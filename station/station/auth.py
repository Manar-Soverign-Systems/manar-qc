import argon2
from . import store

PH = argon2.PasswordHasher()

def tester_by_badge(payload, code):
    if not payload or "testers" not in payload:
        return None
    for t in payload["testers"]:
        if t["code"] == code or t["badge_id"] == code:
            return t
    return None

def verify_pin(tester, pin):
    try:
        return PH.verify(tester["pin_hash"], pin)
    except Exception:
        return False

def open_shift(c, code):
    cur = c.execute("INSERT INTO shifts(tester_code,started) VALUES(?,?)", (code, store.now()))
    c.commit()
    return cur.lastrowid
