import csv
import json
import statistics

def load_station(path_or_file):
    out, seq = {}, {}
    if isinstance(path_or_file, str):
        f = open(path_or_file, "r", encoding="utf-8")
    else:
        f = path_or_file
    for r in csv.DictReader(f):
        if r["kind"] != "final":
            continue
        dims = json.loads(r["dims"])
        for code, v in dims.items():
            if v.get("mm") is None:
                continue
            key = (r["po"], r["size"], code)
            out[(key, seq.get(key, 0))] = (v["mm"], v["verdict"])
            seq[key] = seq.get(key, 0) + 1
    return out

def load_tape(path_or_file):
    out, seq = {}, {}
    if isinstance(path_or_file, str):
        f = open(path_or_file, "r", encoding="utf-8")
    else:
        f = path_or_file
    for r in csv.DictReader(f):
        key = (r["po"], r["size"], r["code"])
        out[(key, seq.get(key, 0))] = float(r["tape_mm"])
        seq[key] = seq.get(key, 0) + 1
    return out

def load_pack(path_or_file):
    if isinstance(path_or_file, str):
        p = json.load(open(path_or_file))
    else:
        p = json.load(path_or_file)
    po_style = {w["po"]: w["style_code"] for w in p.get("workorders", [])}
    spec = {}
    for s in p.get("specs", []):
        if s["domain"] != "FIN":
            continue
        for r in s["rows"]:
            spec[(s["style_code"], r["sz"], r["code"])] = (r["t"], r["tp"], r["tm"])
    return po_style, spec

def run(records_csv, tape_csv, pack_json, out_stem, pdf_writer):
    st, tape = load_station(records_csv), load_tape(tape_csv)
    po_style, spec = load_pack(pack_json)
    groups = {}
    for key, n in st:
        if (key, n) in tape:
            groups.setdefault(key, []).append((st[(key, n)], tape[(key, n)]))
    rows, lines = [], ["MANAR QC VALIDATION REPORT (system vs tape)", ""]
    for key, pairs in sorted(groups.items()):
        po, size, code = key
        tgt = spec.get((po_style.get(po, ""), size, code))
        if not tgt:
            continue
        t, tp, tm = tgt
        devs = [s[0][0] - tpv for (s, tpv) in pairs]
        mae = sum(abs(d) for d in devs) / len(devs)
        within = 100.0 * sum(abs(d) <= (tp if d > 0 else tm) for (s, tpv) in pairs) / len(devs)
        f_ok = sum(s[0][1] == "PASS" and not (t - tm) <= tpv <= (t + tp) for (s, tpv) in pairs)
        f_fail = sum(s[0][1] == "FAIL" and (t - tm) <= tpv <= (t + tp) for (s, tpv) in pairs)
        gate = (mae <= max(2.0, min(tp, tm) / 3) and within >= 95 and f_ok == 0)
        rows.append([po, size, code, len(devs),
                     round(statistics.mean(devs), 2),
                     round(statistics.pstdev(devs) if len(devs) > 1 else 0, 2),
                     round(mae, 2), round(max(devs, key=abs), 2),
                     round(within, 1), f_ok, f_fail,
                     "PASS" if gate else "FAIL"])
        lines.append("%s %s %s: n=%d mean=%+.2f mae=%.2f max=%+.2f "
                     "within=%.1f%% falseOK=%d falseFAIL=%d -> %s"
                     % (po, size, code, len(devs),
                        statistics.mean(devs), mae,
                        max(devs, key=abs), within, f_ok, f_fail,
                        "GATE PASS" if gate else "GATE FAIL"))
    with open(out_stem + ".csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["po", "size", "code", "n", "mean_dev", "sd", "mae",
                    "max_dev", "pct_within_tol", "false_ok", "false_fail",
                    "gate"])
        w.writerows(rows)
    pdf_writer(out_stem + ".pdf", lines)
    return rows
