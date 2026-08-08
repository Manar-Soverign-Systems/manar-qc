import base64
import datetime
import hashlib
import json

from django.conf import settings
from django.utils import timezone

import nacl.signing

from .models import Pack, SpecRow, SpecSet, Style, WorkOrder, Lay, Bundle
from .sheets import PROFILES

CANON = lambda o: json.dumps(o, sort_keys=True, separators=(",", ":"))

def _load_signing_key():
    with open(settings.SIGNING_KEY_PATH, "rb") as f:
        return nacl.signing.SigningKey(f.read())

def build_payload(vendor, unit):
    lic = vendor.license_set.first()
    specs = []
    for ss in SpecSet.objects.for_vendor(vendor).filter(status="active"):
        specs.append({
            "style_code": ss.style.style_code,
            "domain": ss.domain,
            "version": ss.version,
            "rows": [{
                "sz": r.size_label,
                "panel": r.panel_type,
                "code": r.code.code,
                "t": r.target_mm,
                "tp": r.tol_plus_mm,
                "tm": r.tol_minus_mm,
            } for r in SpecRow.objects.filter(specset=ss)]
        })

    workorders = []
    for wo in WorkOrder.objects.for_vendor(vendor).filter(status="open"):
        lays = []
        for lay in Lay.objects.filter(workorder=wo):
            bundles = [{
                "b": b.bundle_code,
                "sz": b.size_label,
                "c": b.color,
                "q": b.qty,
            } for b in Bundle.objects.filter(lay=lay)]
            lays.append({
                "lay": lay.lay_number,
                "bundles": bundles,
            })
        workorders.append({
            "po": wo.po_number,
            "style_code": wo.style.style_code,
            "category": wo.style.category.name,
            "lays": lays,
        })

    allowed_units = ["*"] if (unit and unit.roving) else ([unit.code] if unit else ["*"])

    return {
        "format": "manar.pack",
        "v": 1,
        "vendor": vendor.code,
        "unit": unit.code if unit else "ALL",
        "application": unit.application if unit else "garment",
        "issued_at": timezone.now().date().isoformat(),
        "license": {
            "expires_at": lic.expires_at.isoformat() if lic else "2030-01-01",
            "grace_days": lic.grace_days if lic else 30,
            "allowed_units": allowed_units,
            "stations": [{
                "station_code": s.station_code,
                "hardware_id": s.hardware_id,
            } for s in (unit.station_set.all() if unit else [])],
        },
        "sheet_profiles": PROFILES,
        "testers": [{
            "code": t.code,
            "name": t.name,
            "badge_id": t.badge_id,
            "pin_hash": t.pin_hash,
        } for t in (unit.tester_set.filter(status="active") if unit else [])],
        "workorders": workorders,
        "specs": specs,
    }

def issue_pack(vendor, unit):
    payload = build_payload(vendor, unit)
    body = CANON(payload).encode()
    key = _load_signing_key()
    signed = key.sign(body)
    version = (Pack.objects.for_vendor(vendor).filter(unit=unit).count()) + 1
    pack = Pack.objects.create(
        vendor=vendor,
        unit=unit,
        version=version,
        contents_hash=hashlib.sha256(body).hexdigest(),
        signature=signed.signature.hex(),
        key_id=base64.b64encode(key.verify_key.encode()).hex()[:16],
        body=body
    )
    return pack

def verify_pack(body, signature_hex, pubkey_b64):
    vk = nacl.signing.VerifyKey(base64.b64decode(pubkey_b64))
    try:
        vk.verify(body, bytes.fromhex(signature_hex))
        return True
    except Exception:
        return False

def station_accept(station, payload, current_version, today=None):
    """A2 acceptance rules — all must pass."""
    today = today or datetime.date.today()
    if payload["vendor"] != station.vendor.code:
        return False, "vendor mismatch"
    if not any(s["hardware_id"] == station.hardware_id for s in payload["license"]["stations"]):
        return False, "station not in allowlist"
    if payload["version"] <= current_version:
        return False, "downgrade refused"
    exp = payload["license"]["expires_at"]
    grace = payload["license"]["grace_days"]
    if (today - datetime.date.fromisoformat(exp)).days > grace:
        return False, "license beyond grace"

    allowed_units = payload["license"].get("allowed_units", ["*"])
    station_unit_code = station.unit.code if station.unit else ""
    if "*" not in allowed_units and station_unit_code and station_unit_code not in allowed_units:
        return False, "unit not allowed"

    return True, "ok"
