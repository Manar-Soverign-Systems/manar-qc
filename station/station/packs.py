import base64
import json
import zipfile
from datetime import date, timedelta

import nacl.signing

from . import store

CANON = lambda o: json.dumps(o, sort_keys=True, separators=(",", ":"))

def verify(body, sig_hex, pub_b64):
    vk = nacl.signing.VerifyKey(base64.b64decode(pub_b64))
    try:
        vk.verify(body, bytes.fromhex(sig_hex))
        return True
    except Exception:
        return False

def accept(payload, c, today=None):
    today = today or date.today()
    hw = store.hardware_id()
    stations = payload["license"]["stations"]
    if stations and not any(s["hardware_id"] == hw for s in stations):
        return False, "station not in allowlist"
    cur = c.execute("SELECT MAX(version) FROM packs WHERE vendor=?",
                    (payload["vendor"],)).fetchone()[0] or 0
    if payload["version"] <= cur:
        return False, "downgrade refused"
    exp = date.fromisoformat(payload["license"]["expires_at"])
    if today > exp + timedelta(days=payload["license"]["grace_days"]):
        return False, "license beyond grace"

    allowed_units = payload["license"].get("allowed_units", ["*"])
    current_unit = store.meta_get(c, "unit")
    if "*" not in allowed_units and current_unit and current_unit not in allowed_units:
        return False, "unit not allowed"

    return True, "ok"

def import_pack(path, pub_b64, c):
    with zipfile.ZipFile(path) as z:
        body = z.read("pack.json")
        sig = z.read("pack.sig").decode().strip()
    if not verify(body, sig, pub_b64):
        return False, "signature invalid"
    payload = json.loads(body)
    ok, why = accept(payload, c)
    if not ok:
        return False, why
    c.execute("UPDATE packs SET active=0")
    c.execute("INSERT INTO packs(version,vendor,unit,body,sig,"
              "imported_at,active) VALUES(?,?,?,?,?,?,1)",
              (payload["version"], payload["vendor"], payload["unit"],
               body, sig, store.now()))
    store.meta_set(c, "vendor", payload["vendor"])
    store.meta_set(c, "unit", payload["unit"])
    c.commit()
    return True, f"pack v{payload['version']} active"

def active_payload(c):
    r = c.execute("SELECT body FROM packs WHERE active=1").fetchone()
    return json.loads(r[0]) if r else None
