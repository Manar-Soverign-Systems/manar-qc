from django.contrib import admin
from . import models

@admin.register(models.Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("code", "legal_name", "status", "hosting", "support_consent", "created_at")
    search_fields = ("code", "legal_name")
    list_filter = ("status", "hosting", "support_consent")

@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "vendor", "role", "is_active")
    search_fields = ("username", "email")
    list_filter = ("role", "vendor")

@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "sheet_id", "active")
    list_filter = ("active", "sheet_id")

@admin.register(models.MeasurementCode)
class MeasurementCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "domain", "category", "name", "sane_min_mm", "sane_max_mm")
    list_filter = ("domain", "category")
    search_fields = ("code", "name")

@admin.register(models.Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "vendor", "city", "application", "roving")
    list_filter = ("vendor", "application", "roving")

@admin.register(models.Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ("station_code", "vendor", "unit", "hardware_id", "status")
    list_filter = ("vendor", "status")

@admin.register(models.Tester)
class TesterAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "vendor", "unit", "badge_id", "status")
    list_filter = ("vendor", "unit", "status")

@admin.register(models.Buyer)
class BuyerAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "vendor")
    list_filter = ("vendor",)

@admin.register(models.Style)
class StyleAdmin(admin.ModelAdmin):
    list_display = ("style_code", "name", "buyer", "vendor", "category", "status")
    list_filter = ("vendor", "status", "category")
    search_fields = ("style_code", "name")

@admin.register(models.SpecSet)
class SpecSetAdmin(admin.ModelAdmin):
    list_display = ("style", "domain", "version", "vendor", "status", "effective_from")
    list_filter = ("domain", "status", "vendor")

@admin.register(models.SpecRow)
class SpecRowAdmin(admin.ModelAdmin):
    list_display = ("specset", "size_label", "panel_type", "code", "target_mm", "tol_plus_mm", "tol_minus_mm")

@admin.register(models.WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ("po_number", "buyer", "style", "vendor", "status")
    list_filter = ("vendor", "status")

@admin.register(models.Lay)
class LayAdmin(admin.ModelAdmin):
    list_display = ("workorder", "lay_number", "fabric_batch", "shade", "plies")

@admin.register(models.Bundle)
class BundleAdmin(admin.ModelAdmin):
    list_display = ("bundle_code", "lay", "size_label", "color", "qty", "status")
    list_filter = ("status",)

@admin.register(models.Pack)
class PackAdmin(admin.ModelAdmin):
    list_display = ("vendor", "unit", "version", "contents_hash", "status", "created_at")
    list_filter = ("vendor", "status")

@admin.register(models.AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "object_type", "object_id", "vendor", "created_at")
    list_filter = ("action", "object_type", "vendor")

admin.site.register(models.SizeSetTemplate)
admin.site.register(models.License)
admin.site.register(models.ActivationCode)
admin.site.register(models.SyncUpload)
