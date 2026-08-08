import argparse
import json
import os
import cv2
import numpy as np

from . import auth, export, packs, pdf_report, store, ui, validate, vision
from .drift import DriftTracker

MEASURABLE = {
    "overall_length": 0, "overall_width": 1,
    "cut_length": 0, "cut_width": 1
}

APP_SHEET = {
    "garment": "T-1100",
    "shoe": "SHOE-600",
    "leather": "U-1400",
    "home_textile": "U-1400",
    "fabric": "U-1400"
}

def spec_rows(payload, style_code, domain):
    if not payload or "specs" not in payload:
        return None
    for s in payload["specs"]:
        if s["style_code"] == style_code and s["domain"] == domain:
            return s
    return None

def judge(dims_mm, specset, size, panel=""):
    out, any_fail = {}, False
    if not specset:
        return {"error": "no spec"}, True
    for r in specset["rows"]:
        if r["sz"] != size or r.get("panel", "") != panel:
            continue
        if r["code"] not in MEASURABLE:
            out[r["code"]] = {"mm": None, "verdict": "MANUAL"}
            continue
        m = dims_mm[MEASURABLE[r["code"]]]
        ok = (r["t"] - r["tm"]) <= m <= (r["t"] + r["tp"])
        out[r["code"]] = {"mm": round(m, 1), "verdict": "PASS" if ok else "FAIL"}
        any_fail = any_fail or not ok
    return out, any_fail

def mislabel(payload, style_code, length_mm, ticket_size):
    ss = spec_rows(payload, style_code, "FIN")
    if not ss:
        return False
    hit = None
    for r in [r for r in ss["rows"] if r["code"] == "overall_length"]:
        if (r["t"] - r["tm"]) <= length_mm <= (r["t"] + r["tp"]):
            hit = r["sz"]
    return hit is not None and hit != ticket_size

def _stable(vals):
    return float(np.std(vals)) < 1.5

def _style_for_po(payload, po):
    if not payload:
        return None
    for wo in payload.get("workorders", []):
        if wo["po"] == po:
            return wo["style_code"]
    return None

def _target(ss, size, code):
    if not ss:
        return 0
    for r in ss["rows"]:
        if r["sz"] == size and r["code"] == code:
            return r["t"]
    return 0

def _tol(ss, size, code):
    if not ss:
        return 5
    for r in ss["rows"]:
        if r["sz"] == size and r["code"] == code:
            return max(r["tp"], r["tm"])
    return 5

def _record(kind, c, payload, args, dims, tracker, shift):
    tk = json.loads(args.ticket) if args.ticket and args.ticket.startswith("{") else {}
    size = tk.get("sz", args.size or "M")
    po = tk.get("wo", args.po or "")
    lay = tk.get("lay", 0)
    bundle = tk.get("b", "")
    style = _style_for_po(payload, po)
    domain = "CUT" if kind == "cut" else "FIN"
    ss = spec_rows(payload, style, domain) if style else None
    dims_d, fail = judge(dims, ss, size, panel=args.panel or "")
    verdict = "FAIL" if fail else "OKAY"
    flags = ""

    if kind == "final" and style and mislabel(payload, style, dims[0], size):
        flags = "MISLABEL"
        verdict = "MISLABEL"

    if kind == "cut":
        for code, v in dims_d.items():
            if v.get("mm") is not None:
                lvl = tracker.add((lay, size, args.panel, code),
                                  v["mm"] - _target(ss, size, code),
                                  _tol(ss, size, code))
                if lvl == "STOP":
                    flags = "DRIFT_STOP"

    store.append_check(c, kind, shift, po, lay, bundle, args.panel or "",
                       size, ss["version"] if ss else 0, dims_d, verdict,
                       flags)
    print(verdict, flags, json.dumps(dims_d))
    return verdict

def _supervisor(c, payload, stopped):
    code = input("supervisor badge: ").strip()
    pin = input("supervisor PIN: ").strip()
    t = auth.tester_by_badge(payload, code)
    if t and auth.verify_pin(t, pin):
        store.append_check(c, "ack", 0, "", 0, "", "", "", 0, {}, "ACK", "drift_ack")
        return ""
    print("supervisor verify failed")
    return stopped

def final_loop(c, payload, args):
    sheet_name = args.sheet or APP_SHEET.get((payload or {}).get("application", "garment"), "T-1100")
    profile = payload["sheet_profiles"][sheet_name]
    cap = cv2.VideoCapture(args.cam)
    tracker = DriftTracker()
    shift = int(store.meta_get(c, "shift_id", 0))
    history, stopped = [], ""
    last_verdict = ""

    while True:
        ok, img = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        msg = ""
        if not args.ticket:
            data, _p, _s = cv2.QRCodeDetector().detectAndDecode(gray)
            if data:
                args.ticket = data
                msg = "ticket loaded"
        corners, ids = vision.detect(gray)
        if ids is not None and len(ids) >= 4:
            H, H_inv, pxmm = vision.homography(profile, corners, ids)
            if H is not None:
                mask = vision.garment_mask(img, H_inv, profile, pxmm)
                cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if cnts and cv2.contourArea(max(cnts, key=cv2.contourArea)) > (100 * pxmm) ** 2:
                    g = max(cnts, key=cv2.contourArea)
                    dims = vision.gross_dims(g, H)
                    history.append(dims)
                    history = history[-10:]
                    if len(history) == 10 and _stable([h[0] for h in history]) and _stable([h[1] for h in history]) and not stopped:
                        last_verdict = _record("final", c, payload, args, dims, tracker, shift)
                        history = []
                    msg = "L %.0f W %.0f" % dims

        cv2.putText(img, msg or ("scan ticket" if not args.ticket else ""), (40, 80), 0, 1.4, (0, 200, 255), 3)
        img = ui.banner(img, last_verdict)
        cv2.imshow("manar-station", img)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("x"):
            stopped = _supervisor(c, payload, stopped)

    cap.release()
    cv2.destroyAllWindows()

def _panels_for(payload, style):
    out = set()
    if not payload or "specs" not in payload:
        return []
    for s in payload["specs"]:
        if s["domain"] == "CUT" and s["style_code"] == style:
            out.update(r.get("panel", "") for r in s["rows"])
    return sorted(x for x in out if x)

def _panel_target(payload, style, size, panel):
    lt = wt = None
    if not payload or "specs" not in payload:
        return lt, wt
    for s in payload["specs"]:
        if s["domain"] == "CUT" and s["style_code"] == style:
            for r in s["rows"]:
                if r["sz"] == size and r.get("panel") == panel:
                    if r["code"] == "cut_length":
                        lt = r["t"]
                    if r["code"] == "cut_width":
                        wt = r["t"]
    return lt, wt

def cut_loop(c, payload, args):
    sheet_name = args.sheet or APP_SHEET.get((payload or {}).get("application", "garment"), "U-1400")
    profile = payload["sheet_profiles"][sheet_name]
    cap = cv2.VideoCapture(args.cam)
    tracker = DriftTracker()
    shift = int(store.meta_get(c, "shift_id", 0))
    panel, history = "", []
    last_verdict = ""

    while True:
        ok, img = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if not args.po:
            data, _p, _s = cv2.QRCodeDetector().detectAndDecode(gray)
            if data and data.startswith("{"):
                args.po = json.loads(data).get("wo", "")

        style = _style_for_po(payload, args.po or "")
        panels = _panels_for(payload, style) if style else ["FRONT", "BACK", "SLEEVE_L", "SLEEVE_R"]

        if not panel:
            cv2.putText(img, "CUT MODE - pick panel (1-%d)" % len(panels), (40, 60), 0, 1.2, (0, 200, 255), 3)
            for i, pn in enumerate(panels):
                cv2.putText(img, "%d  %s" % (i + 1, pn), (40, 120 + i * 55), 0, 1.4, (0, 200, 255), 3)
            key = cv2.waitKey(1) & 0xFF
            if ord("1") <= key <= ord("9"):
                i = key - ord("1")
                if i < len(panels):
                    panel, history = panels[i], []
        else:
            corners, ids = vision.detect(gray)
            if ids is not None and len(ids) >= 4:
                H, H_inv, pxmm = vision.homography(profile, corners, ids)
                if H is not None:
                    lt, wt = _panel_target(payload, style, args.size or "M", panel)
                    if lt and wt:
                        w, h = profile["outer_mm"]
                        cx, cy = w / 2, h / 2
                        tgt = [(cx - lt / 2, cy - wt / 2), (cx + lt / 2, cy - wt / 2),
                               (cx + lt / 2, cy + wt / 2), (cx - lt / 2, cy + wt / 2)]
                        cv2.polylines(img, [vision.to_px(H_inv, tgt).astype(int)], True, (0, 255, 0), 2)
                    mask = vision.garment_mask(img, H_inv, profile, pxmm)
                    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if cnts and cv2.contourArea(max(cnts, key=cv2.contourArea)) > (100 * pxmm) ** 2:
                        g = max(cnts, key=cv2.contourArea)
                        dims = vision.gross_dims(g, H)
                        history.append(dims)
                        history = history[-10:]
                        if len(history) == 10 and _stable([x[0] for x in history]) and _stable([x[1] for x in history]):
                            args.panel = panel  # Errata 7 fix
                            last_verdict = _record("cut", c, payload, args, dims, tracker, shift)
                            history = []
                        cv2.putText(img, "%s L %.0f W %.0f" % (panel, dims[0], dims[1]), (40, 60), 0, 1.4, (0, 200, 255), 3)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("b"):
                panel = ""

        img = ui.banner(img, last_verdict)
        cv2.imshow("manar-station", img)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

def main():
    ap = argparse.ArgumentParser(description="MANAR QC Station CLI")
    ap.add_argument("cmd", choices=["import", "shift", "final", "cut", "export",
                                    "status", "report", "validate", "provision", "kiosk"])
    ap.add_argument("--pack", default="")
    ap.add_argument("--pub", default="manar_sign.pub")
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--sheet", default="")
    ap.add_argument("--ticket", default="")
    ap.add_argument("--po", default="")
    ap.add_argument("--size", default="")
    ap.add_argument("--panel", default="")
    ap.add_argument("--out", default="export.zip")
    ap.add_argument("--records", default="records.csv")
    ap.add_argument("--tape", default="tape.csv")
    args = ap.parse_args()

    c = store.conn()
    store.meta_set(c, "hardware_id", store.hardware_id())
    p = packs.active_payload(c)

    if args.cmd == "import":
        ok, why = packs.import_pack(args.pack, open(args.pub).read().strip(), c)
        print("IMPORT:", ok, why)
    elif args.cmd == "status":
        print("vendor:", store.meta_get(c, "vendor"),
              "unit:", store.meta_get(c, "unit"),
              "pack:", p and p.get("version"),
              "application:", p and p.get("application"),
              "hw:", store.hardware_id())
    elif args.cmd == "shift":
        badge = input("badge/code: ").strip()
        t = auth.tester_by_badge(p, badge)
        if t and auth.verify_pin(t, input("PIN: ").strip()):
            sid = auth.open_shift(c, t["code"])
            store.meta_set(c, "shift_id", str(sid))
            print("shift open:", t["code"])
        else:
            print("tester verify failed")
    elif args.cmd == "final":
        final_loop(c, p, args)
    elif args.cmd == "cut":
        cut_loop(c, p, args)
    elif args.cmd == "export":
        print("exported:", export.export(args.out, c))
    elif args.cmd == "report":
        pdf_path = args.out.replace(".zip", ".pdf") if args.out.endswith(".zip") else args.out
        print("report:", pdf_report.batch_report(
            c, pdf_path,
            {"vendor": store.meta_get(c, "vendor"),
             "unit": store.meta_get(c, "unit"),
             "hardware_id": store.hardware_id()}))
    elif args.cmd == "validate":
        out_stem = args.out.replace(".zip", "").replace(".pdf", "")
        rows = validate.run(args.records, args.tape,
                            args.pack or "pack.json",
                            out_stem,
                            lambda p_path, l_lines: pdf_report.text_pdf(p_path, l_lines))
        print("groups:", len(rows), "gates passed:", sum(r[-1] == "PASS" for r in rows))
    elif args.cmd == "provision":
        rep = {"hardware_id": store.hardware_id()}
        cap = cv2.VideoCapture(args.cam)
        ok, frame = cap.read()
        cap.release()
        rep["camera"] = bool(ok)
        if ok:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rep["light_mean"] = round(float(gray.mean()), 1)
            rep["light_ok"] = 40 < gray.mean() < 210
            corners, ids = vision.detect(gray)
            sheet_name = args.sheet or APP_SHEET.get((p or {}).get("application", "garment"), "T-1100")
            prof = (p or {}).get("sheet_profiles", {}).get(sheet_name)
            rep["sheet_ok"] = bool(prof is not None and ids is not None and len(ids) >= 4 and vision.homography(prof, corners, ids)[0] is not None)
        rep["pack_ok"] = p is not None
        rep["testers"] = len((p or {}).get("testers", []))
        json.dump(rep, open("provision_report.json", "w"), indent=1)
        print(json.dumps(rep, indent=1))
    elif args.cmd == "kiosk":
        while True:
            final_loop(c, p, args)

if __name__ == "__main__":
    main()
