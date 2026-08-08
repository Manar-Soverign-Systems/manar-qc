import csv
import io
import json
import zipfile

def export(path, c):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for table, name in (("checks", "records.csv"),):
            rows = c.execute("SELECT * FROM %s" % table).fetchall()
            cols = [d[0] for d in c.description]
            s = io.StringIO()
            w = csv.writer(s)
            w.writerow(cols)
            w.writerows(rows)
            z.writestr(name, s.getvalue())
        z.writestr("chain.json", json.dumps(
            [r[0] for r in c.execute("SELECT hash FROM checks ORDER BY id")]))
        z.writestr("summary.json", json.dumps(summary(c)))
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    return path

def summary(c):
    out = []
    for po, size, verdict, n in c.execute(
            "SELECT po,size,verdict,COUNT(*) FROM checks WHERE kind!='ack'"
            " GROUP BY po,size,verdict"):
        out.append({"po": po, "size": size, "verdict": verdict, "n": n})
    testers = []
    for tc, n, nf in c.execute(
            "SELECT s.tester_code, COUNT(*), SUM(verdict!='OKAY')"
            " FROM checks k JOIN shifts s ON s.id=k.shift_id"
            " WHERE k.kind!='ack' GROUP BY s.tester_code"):
        testers.append({"code": tc, "n": n, "not_okay": nf})
    drift = c.execute("SELECT COUNT(*) FROM checks WHERE flags LIKE '%DRIFT%'").fetchone()[0]
    return {"opt_in_upload": True, "batches": out, "testers": testers, "drift_stops": drift}
