import base64
import json
from datetime import date
import nacl.signing
from django.conf import settings
from django.core.management.base import BaseCommand
from core.models import ActivationCode, License, Vendor

class Command(BaseCommand):
    help = "Bootstrap vendor tenant from signed bootstrap file on client self-host deployment"

    def add_arguments(self, p):
        p.add_argument("file", help="Path to bootstrap_*.json file")

    def handle(self, *a, **o):
        doc = json.load(open(o["file"]))
        body = json.dumps(doc["payload"], sort_keys=True, separators=(",", ":")).encode()

        pubkey_b64 = getattr(settings, "TRUSTED_PUBKEY_B64", "")
        if pubkey_b64:
            vk = nacl.signing.VerifyKey(base64.b64decode(pubkey_b64))
            vk.verify(body, bytes.fromhex(doc["sig"]))

        p = doc["payload"]
        if Vendor.objects.filter(code=p["vendor"]).exists():
            self.stdout.write("already bootstrapped")
            return

        v = Vendor.objects.create(code=p["vendor"], legal_name=p["vendor"], hosting="self")
        License.objects.create(vendor=v, stations_max=p["stations"], seats_max=p["stations"] * 5,
                               expires_at=date.fromisoformat(p["expires"]))
        ActivationCode.objects.create(vendor=v, code=p["activation"],
                                      expires_at=date.fromisoformat(p["expires"]))
        self.stdout.write(self.style.SUCCESS(f"bootstrapped vendor {v.code} — activate with code: {p['activation']}"))
