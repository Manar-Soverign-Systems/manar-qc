import hashlib
import json
import sqlite3
from datetime import datetime, timezone

DB = "manar_station.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS packs(id INTEGER PRIMARY KEY, version INT,
  vendor TEXT, unit TEXT, body BLOB, sig TEXT, imported_at TEXT, active INT);
CREATE TABLE IF NOT EXISTS shifts(id INTEGER PRIMARY KEY AUTOINCREMENT,
  tester_code TEXT, started TEXT, ended TEXT);
CREATE TABLE IF NOT EXISTS checks(id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT, ts TEXT, shift_id INT, po TEXT, lay INT, bundle TEXT,
  panel TEXT, size TEXT, spec_version INT, dims TEXT, verdict TEXT,
  flags TEXT, photo TEXT, hash TEXT, prev_hash TEXT);
"""

def conn(db_path=None):
    c = sqlite3.connect(db_path or DB)
    c.executescript(SCHEMA)
    return c

def now():
    return datetime.now(timezone.utc).isoformat()

def meta_get(c, key, default=None):
    r = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return r[0] if r else default

def meta_set(c, key, value):
    c.execute("REPLACE INTO meta(key,value) VALUES(?,?)", (key, str(value)))
    c.commit()

def hardware_id():
    try:
        mid = open("/etc/machine-id").read().strip()
    except OSError:
        mid = "no-machine-id"
    import socket
    return hashlib.sha256((mid + socket.gethostname()).encode()).hexdigest()[:16]

def last_hash(c):
    r = c.execute("SELECT hash FROM checks ORDER BY id DESC LIMIT 1").fetchone()
    return r[0] if r else "0" * 64

def append_check(c, kind, shift_id, po, lay, bundle, panel, size,
                 spec_version, dims, verdict, flags="", photo=""):
    prev = last_hash(c)
    body = json.dumps({"k": kind, "t": now(), "s": shift_id, "po": po,
                       "l": lay, "b": bundle, "p": panel, "z": size,
                       "v": spec_version, "d": dims, "vd": verdict,
                       "f": flags}, sort_keys=True, separators=(",", ":"))
    h = hashlib.sha256((prev + body).encode()).hexdigest()
    c.execute("INSERT INTO checks(kind,ts,shift_id,po,lay,bundle,panel,"
              "size,spec_version,dims,verdict,flags,photo,hash,prev_hash)"
              " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (kind, now(), shift_id, po, lay, bundle, panel, size,
               spec_version, json.dumps(dims), verdict, flags, photo,
               h, prev))
    c.commit()
    return h
