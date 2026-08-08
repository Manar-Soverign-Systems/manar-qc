# MANAR QC — Station Pack Specification (.mpk v1)

## File Format
A Manar Station Pack (`.mpk`) is a ZIP archive containing two files:
1. `pack.json` — Canonical JSON payload.
2. `pack.sig` — Hex-encoded Ed25519 digital signature of `pack.json` bytes.

---

## Payload Schema (`pack.json`)
```json
{
  "format": "manar.pack",
  "v": 1,
  "vendor": "MASOOD",
  "unit": "U1",
  "application": "garment",
  "issued_at": "2026-08-08",
  "license": {
    "expires_at": "2027-12-31",
    "grace_days": 30,
    "allowed_units": ["U1"],
    "stations": [
      {
        "station_code": "ST-01",
        "hardware_id": "a1b2c3d4e5f6"
      }
    ]
  },
  "sheet_profiles": { ... },
  "testers": [ ... ],
  "workorders": [ ... ],
  "specs": [ ... ]
}
```

---

## Verification Protocol
1. **Signature Verification:** `VerifyKey(pubkey).verify(pack.json, pack.sig)` must pass.
2. **Vendor Check:** `payload.vendor == station.vendor_id`.
3. **Allowlist Check:** Station `hardware_id` must be listed under `license.stations`.
4. **Monotonic Version Check:** `payload.version > station.current_pack_version`.
5. **License Check:** `current_date <= license.expires_at + license.grace_days`.
6. **Roving Unit Check:** Station `unit_code` must match `allowed_units` (or `allowed_units` contains `*`).
