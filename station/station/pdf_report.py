import datetime
import json

def _esc(s):
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")

def text_pdf(path, lines):
    pages = [lines[i:i + 62] for i in range(0, len(lines), 62)] or [[]]
    n = len(pages)
    contents = []
    for pl in pages:
        parts = ["BT", "/F1 9 Tf", "40 800 Td", "12 TL"]
        for ln in pl:
            parts.append("(%s) Tj" % _esc(ln))
            parts.append("T*")
        parts.append("ET")
        contents.append("\n".join(parts).encode("latin-1", "replace"))
    kids = " ".join("%d 0 R" % (4 + 2 * i) for i in range(n))
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            ("<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, n)).encode(),
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>"]
    for i in range(n):
        objs.append(("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                     "/Resources << /Font << /F1 3 0 R >> >> "
                     "/Contents %d 0 R >>" % (5 + 2 * i)).encode())
        objs.append(contents[i])
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += ("%d 0 obj\n" % i).encode()
        if i >= 5:                      # content streams
            out += b"<< /Length %d >>\nstream\n" % len(o)
            out += o
            out += b"\nendstream\n"
        else:
            out += o + b"\n"
        out += b"endobj\n"
    xref = len(out)
    out += ("xref\n0 %d\n" % (len(objs) + 1)).encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, xref)).encode()
    with open(path, "wb") as f:
        f.write(bytes(out))
    return path

def batch_report(c, path, meta):
    lines = ["MANAR QC BATCH REPORT", "vendor/unit: %s / %s"
             % (meta.get("vendor"), meta.get("unit")),
             "station hw: %s   generated: %s"
             % (meta.get("hardware_id"), datetime.datetime.now().isoformat()), ""]
    for po, size in c.execute("SELECT DISTINCT po,size FROM checks WHERE kind!='ack'"):
        lines.append("PO %s  size %s" % (po, size))
        for verdict, n in c.execute(
                "SELECT verdict,COUNT(*) FROM checks WHERE po=? AND size=?"
                " AND kind!='ack' GROUP BY verdict", (po, size)):
            lines.append("  %-9s %d" % (verdict, n))
        for code, n in c.execute(
                "SELECT json_extract(dims.value,'$.verdict'), COUNT(*) "
                "FROM checks, json_each(checks.dims) AS dims "
                "WHERE po=? AND size=? AND "
                "json_extract(dims.value,'$.verdict')='FAIL' "
                "GROUP BY 1", (po, size)):
            lines.append("  fails: %s x%d" % (code, n))
        lines.append("")
    first = c.execute("SELECT hash FROM checks ORDER BY id LIMIT 1").fetchone()
    last = c.execute("SELECT hash FROM checks ORDER BY id DESC LIMIT 1").fetchone()
    lines += ["hash chain head: %s" % (first[0] if first else "-"),
              "hash chain tail: %s" % (last[0] if last else "-"),
              "opt-in portal upload: yes (aggregates only, no photos)"]
    return text_pdf(path, lines)
