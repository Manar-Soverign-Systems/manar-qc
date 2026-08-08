import io
import json
import unittest

from . import drift, packs, store, validate

class StationTests(unittest.TestCase):
    def test_store_hash_chain(self):
        c = store.conn(":memory:")
        h1 = store.append_check(c, "final", 1, "PO1", 1, "B1", "", "M", 1, {"overall_length": {"mm": 700, "verdict": "PASS"}}, "OKAY")
        h2 = store.append_check(c, "final", 1, "PO1", 1, "B2", "", "M", 1, {"overall_length": {"mm": 705, "verdict": "PASS"}}, "OKAY")
        self.assertNotEqual(h1, h2)
        chain = [r[0] for r in c.execute("SELECT hash FROM checks ORDER BY id").fetchall()]
        self.assertEqual(len(chain), 2)
        self.assertEqual(chain[0], h1)
        self.assertEqual(chain[1], h2)

    def test_drift_tracker(self):
        dt = drift.DriftTracker()
        key = (1, "M", "FRONT", "cut_length")

        for _ in range(4):
            res = dt.add(key, 4.0, 5.0)
            self.assertEqual(res, "")

        res_stop = dt.add(key, 4.0, 5.0)  # n=5, mu=4.0 > tol/2 (2.5) -> STOP
        self.assertEqual(res_stop, "STOP")

    def test_validate_gate_math(self):
        st = io.StringIO(
            "kind,po,size,dims,verdict\n"
            'final,PO1,M,"{""overall_length"": {""mm"": 702, ""verdict"": ""PASS""}}",OKAY\n')
        tp = io.StringIO("po,size,code,tape_mm\nPO1,M,overall_length,700\n")
        s = validate.load_station(st)
        t = validate.load_tape(tp)
        self.assertEqual(s[(("PO1", "M", "overall_length"), 0)][0], 702)
        self.assertEqual(t[(("PO1", "M", "overall_length"), 0)], 700.0)

    def test_roving_unit_allowlist(self):
        c = store.conn(":memory:")
        store.meta_set(c, "unit", "U1")
        p = {
            "vendor": "X",
            "version": 1,
            "license": {
                "allowed_units": ["U2"],
                "stations": [],
                "expires_at": "2030-01-01",
                "grace_days": 30
            }
        }
        ok, why = packs.accept(p, c)
        self.assertFalse(ok)
        self.assertEqual(why, "unit not allowed")

if __name__ == "__main__":
    unittest.main()
