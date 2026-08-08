import base64
import datetime
import io
import json
import nacl.signing
from django.core.management import call_command
from django.test import Client, TestCase

from .models import Buyer, Category, MeasurementCode, Style, SyncUpload, User, Vendor
from .packs import CANON, station_accept, verify_pack
from .imports import validate_and_import

class ScopingTests(TestCase):
    def test_for_vendor_isolation(self):
        a = Vendor.objects.create(code="AA", legal_name="A")
        b = Vendor.objects.create(code="BB", legal_name="B")
        Buyer.objects.create(vendor=a, name="ZARA", code="Z")
        Buyer.objects.create(vendor=b, name="ZARA", code="Z")
        self.assertEqual(Buyer.objects.for_vendor(a).count(), 1)

class PackTests(TestCase):
    def test_verify_and_downgrade(self):
        key = nacl.signing.SigningKey.generate()
        pub = base64.b64encode(key.verify_key.encode()).decode()
        body = CANON({"vendor": "AA", "version": 2}).encode()
        sig = key.sign(body).signature.hex()
        self.assertTrue(verify_pack(body, sig, pub))
        self.assertFalse(verify_pack(body + b" ", sig, pub))

class ImportTests(TestCase):
    def test_cm_guard(self):
        call_command("load_library")
        v = Vendor.objects.create(code="CC", legal_name="C")
        buy = Buyer.objects.create(vendor=v, name="ZARA", code="Z")
        cat = Category.objects.get(name="tee")
        Style.objects.create(vendor=v, buyer=buy, category=cat, style_code="S1", name="s")

        errs, _ = validate_and_import(v, io.StringIO(
            "style_code,buyer,category,domain,size_label,measurement_code,"
            "target_mm,tol_plus_mm,tol_minus_mm\n"
            "S1,Z,tee,FIN,M,overall_length,45,5,5\n"))
        self.assertTrue(any("cm" in e[2] for e in errs))

class LeakageTests(TestCase):
    def setUp(self):
        call_command("load_library")
        self.a = Vendor.objects.create(code="AA", legal_name="A", status="active")
        self.b = Vendor.objects.create(code="BB", legal_name="B", status="active")
        cat = Category.objects.get(name="tee")
        for v in (self.a, self.b):
            buy = Buyer.objects.create(vendor=v, name="ZARA", code="Z")
            Style.objects.create(vendor=v, buyer=buy, category=cat, style_code="S1", name="s")
            User.objects.create_user(username="u@" + v.code, email="u@" + v.code,
                                     password="x" * 12, vendor=v, role="merch")

    def test_cross_tenant_access(self):
        c = Client()
        c.login(username="u@AA", password="x" * 12)
        other_style = Style.objects.get(vendor=self.b)
        res = c.get(f"/style/{other_style.id}/")
        self.assertEqual(res.status_code, 403)
        mine_style = Style.objects.get(vendor=self.a)
        res_mine = c.get(f"/style/{mine_style.id}/")
        self.assertEqual(res_mine.status_code, 200)

class LibraryTests(TestCase):
    def test_idempotent(self):
        call_command("load_library")
        n = MeasurementCode.objects.count()
        call_command("load_library")
        self.assertEqual(MeasurementCode.objects.count(), n)

class VerifyTests(TestCase):
    def test_verify_lookup(self):
        v = Vendor.objects.create(code="VV", legal_name="V", status="active")
        target_hash = "a" * 64
        SyncUpload.objects.create(vendor=v, uploaded_by="q@v", filename="e.zip", summary={}, chain=[target_hash])
        u = User.objects.create_user(username="a@v", email="a@v", password="x" * 12, vendor=v, role="auditor")
        c = Client()
        c.force_login(u)
        r = c.get("/verify/?hash=" + target_hash)
        self.assertContains(r, "VERIFIED")
        r_fail = c.get("/verify/?hash=" + ("b" * 64))
        self.assertNotContains(r_fail, "VERIFIED")

class BootstrapTests(TestCase):
    def test_seed_idempotent(self):
        call_command("seed_demo")
        n = Vendor.objects.filter(code="DEMO").count()
        call_command("seed_demo")
        self.assertEqual(Vendor.objects.filter(code="DEMO").count(), n)
