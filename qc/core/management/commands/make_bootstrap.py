import json
import secrets
from pathlib import Path
import nacl.signing
from django.conf import settings
from django.core.management.base import BaseCommand

CANON = lambda o: json.dumps(o, sort_keys=True, separators=(",", ":"))

class Command(BaseCommand):
    help = "Make signed bootstrap payload for self-hosted enterprise tenant onboarding"

    def add_arguments(self, p):
        p.add_argument("vendor", help="Vendor code (e.g. INTERLOOP)")
        p.add_argument("--stations", type=int, default=4)
        p.add_argument("--expires", default="2027-12-31")

    def handle(self, *a, **o):
        payload = {
            "vendor": o["vendor"],
            "stations": o["stations"],
            "expires": o["expires"],
            "activation": secrets.token_urlsafe(12)
        }
        key_path = Path(settings.SIGNING_KEY_PATH)
        if not key_path.exists():
            self.stderr.write("SIGNING_KEY_PATH file not found")
            return
        key = nacl.signing.SigningKey(key_path.read_bytes())
        sig = key.sign(CANON(payload).encode()).signature.hex()
        out_file = f"bootstrap_{o['vendor']}.json"
        with open(out_file, "w") as f:
            json.dump({"payload": payload, "sig": sig}, f, indent=2)
        self.stdout.write(self.style.SUCCESS(f"bootstrap written to {out_file} — ship with self-host kit"))
