from django.core.management.base import BaseCommand
from core.models import Category, MeasurementCode, SizeSetTemplate

TOPS = ["tee", "polo", "shirt", "sweatshirt", "hoodie", "jacket"]
BOTTOMS = ["trouser", "shorts"]
SHOES = ["shoe-vamp", "shoe-quarter", "shoe-tongue", "shoe-insole"]

PANELS_TOP = ["FRONT", "BACK", "SLEEVE_L", "SLEEVE_R"]
PANELS_BOT = ["LEG_FRONT", "LEG_BACK", "WAISTBAND"]
PANELS_SHOE = ["L", "R"]

FIN_TOP = [("overall_length", 300, 1000), ("overall_width", 200, 900),
           ("chest_width", 200, 800), ("shoulder_width", 200, 700),
           ("sleeve_length", 100, 800), ("hem_width", 200, 800)]
FIN_BOT = [("overall_length", 300, 1300), ("overall_width", 150, 700),
           ("waist_width", 150, 700), ("inseam", 300, 1000),
           ("outseam", 300, 1300), ("leg_opening", 100, 400)]
CUT = [("cut_length", 100, 1400), ("cut_width", 50, 900)]

SIZES = [{"label": l, "eu": e, "us": u} for l, e, u in [
    ("XS", 44, 34), ("S", 46, 36), ("M", 48, 38),
    ("L", 50, 40), ("XL", 52, 42), ("XXL", 54, 44)]]

class Command(BaseCommand):
    help = "Seed global categories, measurement codes, and size templates"

    def handle(self, *a, **o):
        for name in TOPS:
            cat, _ = Category.objects.get_or_create(
                name=name, defaults={"sheet_id": "T-1100" if name in ("tee", "polo", "shirt") else "U-1400",
                                     "panel_types": PANELS_TOP})
            for code, lo, hi in FIN_TOP:
                MeasurementCode.objects.get_or_create(
                    code=code, domain="FIN", category=cat,
                    defaults={"name": code.replace("_", " "),
                              "definition": f"flat garment, {code}",
                              "sane_min_mm": lo, "sane_max_mm": hi})
            for code, lo, hi in CUT:
                MeasurementCode.objects.get_or_create(
                    code=code, domain="CUT", category=cat,
                    defaults={"name": code.replace("_", " "),
                              "definition": "cut panel dimension",
                              "sane_min_mm": lo, "sane_max_mm": hi})

        for name in BOTTOMS:
            cat, _ = Category.objects.get_or_create(
                name=name, defaults={"sheet_id": "U-1400",
                                     "panel_types": PANELS_BOT})
            for code, lo, hi in FIN_BOT:
                MeasurementCode.objects.get_or_create(
                    code=code, domain="FIN", category=cat,
                    defaults={"name": code.replace("_", " "),
                              "definition": f"flat garment, {code}",
                              "sane_min_mm": lo, "sane_max_mm": hi})
            for code, lo, hi in CUT:
                MeasurementCode.objects.get_or_create(
                    code=code, domain="CUT", category=cat,
                    defaults={"name": code.replace("_", " "),
                              "definition": "cut panel dimension",
                              "sane_min_mm": lo, "sane_max_mm": hi})

        for name in SHOES:
            cat, _ = Category.objects.get_or_create(
                name=name, defaults={"sheet_id": "SHOE-600",
                                     "panel_types": PANELS_SHOE})
            for code, lo, hi in (("cut_length", 40, 400), ("cut_width", 20, 250)):
                MeasurementCode.objects.get_or_create(
                    code=code, domain="CUT", category=cat,
                    defaults={"name": code.replace("_", " "),
                              "definition": "die-cut piece dimension",
                              "sane_min_mm": lo, "sane_max_mm": hi})

        SizeSetTemplate.objects.get_or_create(
            name="EU_ALPHA", defaults={"sizes": SIZES})

        self.stdout.write(self.style.SUCCESS(
            f"library: {Category.objects.count()} categories, {MeasurementCode.objects.count()} codes"
        ))
