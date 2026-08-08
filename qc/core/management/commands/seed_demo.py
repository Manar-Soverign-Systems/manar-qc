from django.core.management import call_command
from django.core.management.base import BaseCommand
import argon2

from core.models import (Bundle, Buyer, Category, Lay, MeasurementCode,
                         SpecRow, SpecSet, Style, Tester, Unit, Vendor,
                         WorkOrder, Station)

SIZES = [("XS", 660, 460), ("S", 680, 485), ("M", 700, 510),
         ("L", 720, 540), ("XL", 740, 570), ("XXL", 760, 600)]

class Command(BaseCommand):
    help = "Seed demo data for staging/testing"

    def handle(self, *a, **o):
        call_command("load_library")
        v, made = Vendor.objects.get_or_create(code="DEMO",
                                               defaults={"legal_name": "Demo Mills", "status": "active"})
        if not made:
            self.stdout.write("demo already seeded")
            return

        unit = Unit.objects.create(vendor=v, code="U1", name="Demo Unit", city="Faisalabad")
        Station.objects.create(vendor=v, unit=unit, station_code="ST-01", hardware_id="demo-hw-01", modes=["CUT", "FINAL"])

        ph = argon2.PasswordHasher()
        for code in ("QC-01", "QC-02"):
            Tester.objects.create(vendor=v, unit=unit, code=code,
                                  name="Tester " + code, badge_id=code,
                                  pin_hash=ph.hash("123456"))

        for buyer_name in ("ZARA", "HM"):
            b = Buyer.objects.create(vendor=v, name=buyer_name,
                                     code=buyer_name[:2].upper())
            cat = Category.objects.get(name="tee")
            s = Style.objects.create(vendor=v, buyer=b, category=cat,
                                     style_code="D-%s-01" % b.code,
                                     name="Demo Tee", status="validated")
            ss = SpecSet.objects.create(vendor=v, style=s, domain="FIN",
                                        version=1, status="active")
            for size, ln, wd in SIZES:
                for code, t in (("overall_length", ln),
                                ("overall_width", wd)):
                    SpecRow.objects.create(
                        specset=ss, size_label=size,
                        code=MeasurementCode.objects.get(
                            domain="FIN", category=cat, code=code),
                        target_mm=t, tol_plus_mm=5, tol_minus_mm=5)
            wo = WorkOrder.objects.create(vendor=v, buyer=b, style=s,
                                          po_number="PO-DEMO-%s" % b.code)
            lay = Lay.objects.create(vendor=v, workorder=wo, lay_number=1,
                                     plies=12)
            for size, _l, _w in SIZES:
                Bundle.objects.create(vendor=v, lay=lay, size_label=size,
                                      qty=20,
                                      bundle_code="L1-%s" % size)

        self.stdout.write(self.style.SUCCESS("demo seeded: 2 buyers, 2 styles, 12 bundles"))
