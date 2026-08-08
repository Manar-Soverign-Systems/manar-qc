import csv
from django.db import transaction
from .models import (CUT, FIN, MeasurementCode, SpecRow, SpecSet, Style)

REQUIRED = ["style_code", "buyer", "category", "domain", "size_label",
            "measurement_code", "target_mm", "tol_plus_mm", "tol_minus_mm"]

def validate_and_import(vendor, file_obj):
    errors = []
    if hasattr(file_obj, "read") and isinstance(file_obj.read(0), bytes):
        lines = [line.decode("utf-8-sig") for line in file_obj.readlines()]
        rows = list(csv.DictReader(lines))
    else:
        rows = list(csv.DictReader(file_obj))

    for n, row in enumerate(rows, start=2):
        missing = [c for c in REQUIRED if not (row.get(c) or "").strip()]
        if missing:
            errors.append((n, "error", f"missing: {','.join(missing)}"))
            continue
        if row["domain"] not in (CUT, FIN):
            errors.append((n, "error", "bad domain"))
        try:
            t, tp, tm = (int(float(row[k])) for k in ("target_mm", "tol_plus_mm", "tol_minus_mm"))
        except ValueError:
            errors.append((n, "error", "non-numeric mm values"))
            continue
        if t < 50:
            errors.append((n, "error", "target < 50 mm — looks like cm"))
        if not (1 <= tp <= 25 and 1 <= tm <= 25):
            errors.append((n, "error", "tolerance outside 1-25 mm"))

    if errors:
        return errors, None

    with transaction.atomic():
        drafts = {}
        for row in rows:
            style = Style.objects.for_vendor(vendor).get(style_code=row["style_code"].strip())
            domain = row["domain"].strip()
            key = (style.id, domain)
            if key not in drafts:
                ver = (SpecSet.objects.for_vendor(vendor).filter(style=style, domain=domain).count()) + 1
                drafts[key] = SpecSet.objects.create(
                    vendor=vendor, style=style, domain=domain,
                    version=ver, status="draft"
                )
            code = MeasurementCode.objects.get(
                domain=domain,
                category=style.category,
                code=row["measurement_code"].strip()
            )
            SpecRow.objects.create(
                specset=drafts[key],
                size_label=row["size_label"].strip(),
                panel_type=(row.get("panel_type") or "").strip(),
                code=code,
                target_mm=int(float(row["target_mm"])),
                tol_plus_mm=int(float(row["tol_plus_mm"])),
                tol_minus_mm=int(float(row["tol_minus_mm"]))
            )
    return [], list(drafts.values())
