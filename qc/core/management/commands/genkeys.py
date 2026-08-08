import base64
from pathlib import Path

from django.core.management.base import BaseCommand
import nacl.signing

class Command(BaseCommand):
    help = "Generate Ed25519 keypair for station pack signing"

    def add_arguments(self, parser):
        parser.add_argument("dir", help="Directory path to save keypair files")

    def handle(self, *a, **o):
        d = Path(o["dir"])
        d.mkdir(parents=True, exist_ok=True)
        key = nacl.signing.SigningKey.generate()
        (d / "manar_sign.key").write_bytes(bytes(key))
        (d / "manar_sign.pub").write_bytes(base64.b64encode(key.verify_key.encode()))
        self.stdout.write(self.style.SUCCESS("keys written — set SIGNING_KEY_PATH and TRUSTED_PUBKEY_B64 from these files"))
