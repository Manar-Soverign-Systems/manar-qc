import hashlib
import json
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

CUT, FIN = "CUT", "FIN"
DOMAINS = ((CUT, "CUT"), (FIN, "FIN"))

class Base(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

class TenantQuerySet(models.QuerySet):
    def for_vendor(self, vendor):
        return self.filter(vendor=vendor)

class TenantModel(Base):
    vendor = models.ForeignKey("Vendor", on_delete=models.CASCADE)
    objects = TenantQuerySet.as_manager()

    class Meta:
        abstract = True

# ---- global (Manar-managed) -------------------------------------------------
class Category(Base):
    name = models.CharField(max_length=40, unique=True)
    sheet_id = models.CharField(max_length=10)          # T-1100 / U-1400 / SHOE-600
    panel_types = models.JSONField(default=list)        # CUT panel codes
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class MeasurementCode(Base):
    code = models.CharField(max_length=40)
    domain = models.CharField(max_length=3, choices=DOMAINS)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    name = models.CharField(max_length=80)
    definition = models.TextField()
    synonyms = models.JSONField(default=list)
    sane_min_mm = models.PositiveIntegerField(default=50)
    sane_max_mm = models.PositiveIntegerField(default=1400)

    class Meta:
        unique_together = ("domain", "category", "code")

    def __str__(self):
        return f"{self.domain}:{self.category.name}:{self.code}"

class SizeSetTemplate(Base):
    name = models.CharField(max_length=40)
    sizes = models.JSONField()   # [{label, eu, us, uk}, ...] ordered

    def __str__(self):
        return self.name

# ---- tenant -----------------------------------------------------------------
class Vendor(Base):
    code = models.CharField(max_length=20, unique=True)
    legal_name = models.CharField(max_length=120)
    status = models.CharField(max_length=12, default="active")
    hosting = models.CharField(max_length=10, default="cloud")
    support_consent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.code} ({self.legal_name})"

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin"
        MERCH = "merch"
        QA = "qa"
        AUDITOR = "auditor"
        MANAR = "manar"
    vendor = models.ForeignKey(Vendor, null=True, blank=True, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.AUDITOR)

    def __str__(self):
        return f"{self.email or self.username} [{self.role}]"

class License(TenantModel):
    stations_max = models.PositiveSmallIntegerField()
    seats_max = models.PositiveSmallIntegerField()
    expires_at = models.DateField()
    grace_days = models.PositiveSmallIntegerField(default=30)

    def __str__(self):
        return f"License({self.vendor.code}, expires={self.expires_at})"

class Unit(TenantModel):
    class Application(models.TextChoices):
        GARMENT = "garment"
        SHOE = "shoe"
        LEATHER = "leather"
        HOME = "home_textile"
        FABRIC = "fabric"

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=80)
    city = models.CharField(max_length=60, blank=True)
    application = models.CharField(max_length=12, choices=Application.choices, default=Application.GARMENT)
    roving = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.code} - {self.name}"

class Station(TenantModel):
    unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.CASCADE)
    station_code = models.CharField(max_length=12)
    hardware_id = models.CharField(max_length=64)
    modes = models.JSONField(default=list)      # ["CUT","FINAL"]
    status = models.CharField(max_length=12, default="active")

    class Meta:
        unique_together = ("vendor", "hardware_id")

    def __str__(self):
        return f"Station({self.station_code}, hw={self.hardware_id[:8]})"

class Tester(TenantModel):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    code = models.CharField(max_length=12)        # QC-07
    name = models.CharField(max_length=80)
    badge_id = models.CharField(max_length=40)
    pin_hash = models.CharField(max_length=128)   # argon2, station-side
    status = models.CharField(max_length=10, default="active")

    class Meta:
        unique_together = ("vendor", "unit", "code")

    def __str__(self):
        return f"Tester({self.code} - {self.name})"

class Buyer(TenantModel):
    name = models.CharField(max_length=80)        # ZARA (per-tenant copy)
    code = models.CharField(max_length=20)
    default_sizeset = models.ForeignKey(SizeSetTemplate, null=True, blank=True, on_delete=models.SET_NULL)
    tol_policy = models.JSONField(default=dict)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

class Style(TenantModel):
    class Status(models.TextChoices):
        DRAFT = "draft"
        VALIDATED = "validated"
        ARCHIVED = "archived"
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    style_code = models.CharField(max_length=40)
    name = models.CharField(max_length=120)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    sizeset = models.ForeignKey(SizeSetTemplate, null=True, blank=True, on_delete=models.SET_NULL)
    colorways = models.JSONField(default=list)

    class Meta:
        unique_together = ("vendor", "buyer", "style_code")

    def __str__(self):
        return f"{self.style_code} - {self.name}"

class SpecSet(TenantModel):
    style = models.ForeignKey(Style, on_delete=models.CASCADE)
    domain = models.CharField(max_length=3, choices=DOMAINS)
    version = models.PositiveIntegerField()
    effective_from = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, default="draft")

    class Meta:
        unique_together = ("vendor", "style", "domain", "version")

    def __str__(self):
        return f"SpecSet({self.style.style_code}, {self.domain}, v{self.version})"

class SpecRow(Base):
    specset = models.ForeignKey(SpecSet, on_delete=models.CASCADE)
    size_label = models.CharField(max_length=8)
    panel_type = models.CharField(max_length=20, blank=True, default="")
    code = models.ForeignKey(MeasurementCode, on_delete=models.PROTECT)
    target_mm = models.PositiveIntegerField()
    tol_plus_mm = models.PositiveSmallIntegerField()
    tol_minus_mm = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ("specset", "size_label", "panel_type", "code")

    def __str__(self):
        return f"SpecRow({self.size_label}, {self.code.code}, {self.target_mm}mm)"

class WorkOrder(TenantModel):
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE)
    style = models.ForeignKey(Style, on_delete=models.CASCADE)
    po_number = models.CharField(max_length=40)
    size_ratio = models.JSONField(default=dict)
    delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, default="open")

    def __str__(self):
        return f"WO({self.po_number})"

class Lay(TenantModel):
    workorder = models.ForeignKey(WorkOrder, on_delete=models.CASCADE)
    lay_number = models.PositiveIntegerField()
    fabric_batch = models.CharField(max_length=40, blank=True)
    shade = models.CharField(max_length=20, blank=True)
    plies = models.PositiveSmallIntegerField(default=1)
    shrinkage_band_mm = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=10, default="open")

    class Meta:
        unique_together = ("vendor", "workorder", "lay_number")

    def __str__(self):
        return f"Lay({self.workorder.po_number} - L{self.lay_number})"

class Bundle(TenantModel):
    class Status(models.TextChoices):
        OPEN = "open"
        QUARANTINED = "quarantined"
        CLOSED = "closed"
    lay = models.ForeignKey(Lay, on_delete=models.CASCADE)
    size_label = models.CharField(max_length=8)
    color = models.CharField(max_length=20, blank=True)
    qty = models.PositiveSmallIntegerField()
    bundle_code = models.CharField(max_length=24)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)

    class Meta:
        unique_together = ("vendor", "lay", "bundle_code")

    def __str__(self):
        return f"Bundle({self.bundle_code})"

class Pack(TenantModel):
    unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.CASCADE)
    version = models.PositiveIntegerField()
    contents_hash = models.CharField(max_length=64)
    signature = models.CharField(max_length=160)    # hex Ed25519
    key_id = models.CharField(max_length=16)
    status = models.CharField(max_length=12, default="current")
    body = models.BinaryField(null=True, blank=True)

    class Meta:
        unique_together = ("vendor", "unit", "version")

    def __str__(self):
        return f"Pack({self.vendor.code}, v{self.version})"

class AuditLog(TenantModel):
    vendor = models.ForeignKey(Vendor, null=True, blank=True, on_delete=models.CASCADE)
    actor = models.CharField(max_length=80)
    actor_type = models.CharField(max_length=10, default="user")
    action = models.CharField(max_length=40)
    object_type = models.CharField(max_length=40)
    object_id = models.CharField(max_length=64, blank=True)
    payload = models.JSONField(default=dict)
    hash = models.CharField(max_length=64)
    prev_hash = models.CharField(max_length=64)

    @classmethod
    def append(cls, vendor, actor, action, object_type, object_id="", payload=None, actor_type="user"):
        last = (cls.objects.filter(vendor=vendor).order_by("-created_at", "-id").first()) if vendor else (cls.objects.order_by("-created_at", "-id").first())
        prev = last.hash if last else "0" * 64
        body = json.dumps({"a": actor, "act": action, "ot": object_type,
                           "oi": str(object_id), "p": payload or {}},
                          sort_keys=True, separators=(",", ":"))
        h = hashlib.sha256((prev + body).encode()).hexdigest()
        return cls.objects.create(vendor=vendor, actor=actor,
                                  actor_type=actor_type, action=action,
                                  object_type=object_type,
                                  object_id=str(object_id),
                                  payload=payload or {}, hash=h,
                                  prev_hash=prev)

class ActivationCode(Base):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    code = models.CharField(max_length=40, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"ActivationCode({self.code}, vendor={self.vendor.code})"

class SyncUpload(TenantModel):
    uploaded_by = models.CharField(max_length=120)
    filename = models.CharField(max_length=160)
    summary = models.JSONField(default=dict)
    chain = models.JSONField(default=list)   # record hashes from station

    def __str__(self):
        return f"SyncUpload({self.filename}, vendor={self.vendor.code})"
