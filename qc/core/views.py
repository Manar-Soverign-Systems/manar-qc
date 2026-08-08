import base64
import io
import json
import zipfile

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (BundleForm, BuyerForm, LayForm, SpecRowForm,
                    StyleForm, WorkOrderForm)
from .imports import validate_and_import
from .models import (AuditLog, Bundle, Buyer, Lay, MeasurementCode, Pack,
                     SpecRow, SpecSet, Station, Style, SyncUpload, Unit, WorkOrder)
from .packs import CANON, issue_pack
from .permissions import get_vendor, role_required

READ = ("admin", "merch", "qa", "auditor")
WRITE = ("admin", "merch")
QA = ("admin", "qa")

@login_required
def dashboard(request):
    v = get_vendor(request)
    return render(request, "dash.html", {
        "vendor": v,
        "units": Unit.objects.for_vendor(v) if v else [],
        "packs": Pack.objects.for_vendor(v).order_by("-created_at")[:10] if v else [],
        "stations": Station.objects.for_vendor(v) if v else [],
    })

@role_required(*READ)
def buyers(request):
    v = get_vendor(request)
    if request.method == "POST" and request.user.role in WRITE:
        f = BuyerForm(request.POST)
        if f.is_valid():
            b = f.save(commit=False)
            b.vendor = v
            b.save()
            AuditLog.append(v, request.user.email, "create", "buyer", b.id)
            return redirect("buyers")
    return render(request, "buyers.html", {
        "buyers": Buyer.objects.for_vendor(v), "form": BuyerForm()})

@role_required(*READ)
def styles(request):
    v = get_vendor(request)
    if request.method == "POST" and request.user.role in WRITE:
        f = StyleForm(request.POST)
        if f.is_valid():
            s = f.save(commit=False)
            s.vendor = v
            s.save()
            AuditLog.append(v, request.user.email, "create", "style", s.id)
            return redirect("styles")
    return render(request, "styles.html", {
        "styles": Style.objects.for_vendor(v).select_related("buyer", "category"),
        "form": StyleForm(buyer_qs=Buyer.objects.for_vendor(v))})

@role_required(*READ)
def style_detail(request, pk):
    v = get_vendor(request)
    style = get_object_or_404(Style.objects.for_vendor(v), id=pk)
    editable = (request.user.role in WRITE or request.user.role == "manar") and style.status == "draft"
    
    specsets = SpecSet.objects.for_vendor(v).filter(style=style).order_by("domain", "-version")
    categories_codes = MeasurementCode.objects.filter(category=style.category)
    
    return render(request, "style_detail.html", {
        "style": style,
        "editable": editable,
        "specsets": specsets,
        "measurement_codes": categories_codes,
    })

@role_required(*WRITE)
def run_import(request, pk):
    v = get_vendor(request)
    style = get_object_or_404(Style.objects.for_vendor(v), id=pk)
    if "csv" not in request.FILES:
        messages.error(request, "No CSV file uploaded.")
        return redirect("style_detail", pk=pk)
    errs, drafts = validate_and_import(v, request.FILES["csv"])
    if errs:
        for n, lvl, msg in errs[:30]:
            messages.error(request, f"row {n}: {msg}")
    else:
        for d in drafts:
            AuditLog.append(v, request.user.email, "import",
                            "specset", d.id,
                            {"style": style.style_code,
                             "domain": d.domain, "version": d.version})
        messages.success(request, "Draft SpecSet(s) created.")
    return redirect("style_detail", pk=pk)

@role_required(*WRITE)
def spec_row_update(request, pk):
    v = get_vendor(request)
    row = get_object_or_404(SpecRow.objects.filter(specset__vendor=v), id=pk)
    if row.specset.status != "draft":
        raise PermissionDenied
    f = SpecRowForm(request.POST, instance=row)
    if f.is_valid():
        f.save()
    return redirect("style_detail", pk=row.specset.style_id)

@role_required(*WRITE)
def spec_row_add(request, pk):
    v = get_vendor(request)
    ss = get_object_or_404(SpecSet.objects.for_vendor(v), id=pk)
    if ss.status != "draft":
        raise PermissionDenied
    code = MeasurementCode.objects.get(
        domain=ss.domain, category=ss.style.category,
        code=request.POST["code"])
    SpecRow.objects.create(
        specset=ss, size_label=request.POST["size_label"].strip(),
        panel_type=(request.POST.get("panel_type") or "").strip(),
        code=code, target_mm=int(request.POST["target_mm"]),
        tol_plus_mm=int(request.POST["tol_plus_mm"]),
        tol_minus_mm=int(request.POST["tol_minus_mm"]))
    AuditLog.append(v, request.user.email, "row_add", "specrow", "",
                    {"specset": str(ss.id), "code": code.code})
    return redirect("style_detail", pk=ss.style_id)

@role_required(*WRITE)
def spec_row_delete(request, pk):
    v = get_vendor(request)
    row = get_object_or_404(SpecRow.objects.filter(specset__vendor=v), id=pk)
    if row.specset.status != "draft":
        raise PermissionDenied
    style_id = row.specset.style_id
    row.delete()
    return redirect("style_detail", pk=style_id)

@role_required(*QA)
@require_POST
def validate_style(request, pk):
    v = get_vendor(request)
    style = get_object_or_404(Style.objects.for_vendor(v), id=pk)
    for ss in SpecSet.objects.for_vendor(v).filter(style=style, status="draft"):
        SpecSet.objects.for_vendor(v).filter(
            style=style, domain=ss.domain, status="active").update(status="superseded")
        ss.status = "active"
        ss.effective_from = timezone.now().date()
        ss.save()
    style.status = "validated"
    style.save()
    AuditLog.append(v, request.user.email, "validate", "style", style.id)
    messages.success(request, f"Style {style.style_code} validated.")
    return redirect("style_detail", pk=pk)

@role_required(*READ)
def workorders(request):
    v = get_vendor(request)
    if request.method == "POST" and request.user.role in WRITE:
        f = WorkOrderForm(request.POST)
        if f.is_valid():
            wo = f.save(commit=False)
            wo.vendor = v
            wo.save()
            return redirect("workorders")
    return render(request, "workorders.html", {
        "wos": WorkOrder.objects.for_vendor(v).select_related("style", "buyer"),
        "form": WorkOrderForm(style_qs=Style.objects.for_vendor(v))})

@role_required(*WRITE)
def add_lay(request, pk):
    v = get_vendor(request)
    wo = get_object_or_404(WorkOrder.objects.for_vendor(v), id=pk)
    if request.method == "POST":
        f = LayForm(request.POST)
        if f.is_valid():
            lay = f.save(commit=False)
            lay.vendor, lay.workorder = v, wo
            lay.save()
            return redirect("workorders")
    return render(request, "lay_form.html", {"wo": wo, "form": LayForm()})

@role_required(*WRITE)
def add_bundles(request, pk):
    v = get_vendor(request)
    lay = get_object_or_404(Lay.objects.for_vendor(v), id=pk)
    if request.method == "POST":
        f = BundleForm(request.POST)
        if f.is_valid():
            for line in f.cleaned_data["lines"].splitlines():
                if not line.strip() or "," not in line:
                    continue
                size, qty = line.split(",", 1)
                b_count = Bundle.objects.filter(lay=lay).count() + 1
                Bundle.objects.create(
                    vendor=v, lay=lay, size_label=size.strip(),
                    qty=int(qty.strip()),
                    bundle_code=f"L{lay.lay_number}-{size.strip()}-{b_count}")
            return redirect("workorders")
    return render(request, "bundle_form.html", {"lay": lay, "form": BundleForm()})

@role_required(*READ)
def bundle_ticket(request, pk):
    v = get_vendor(request)
    b = get_object_or_404(Bundle.objects.for_vendor(v), id=pk)
    payload = CANON({"v": 1, "vc": v.code,
                     "wo": b.lay.workorder.po_number,
                     "lay": b.lay.lay_number, "b": b.bundle_code,
                     "sz": b.size_label, "c": b.color, "q": b.qty})
    qr = qrcode.make(payload)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    return render(request, "ticket.html", {
        "b": b, "payload": payload,
        "img": base64.b64encode(buf.getvalue()).decode()})

@role_required(*QA)
@require_POST
def pack_build(request, pk):
    v = get_vendor(request)
    unit = get_object_or_404(Unit.objects.for_vendor(v), id=pk)
    pack = issue_pack(v, unit)
    AuditLog.append(v, request.user.email, "pack_build", "pack", pack.id,
                    {"version": pack.version})
    messages.success(request, f"Pack v{pack.version} built for {unit.code}.")
    return redirect("dashboard")

@role_required(*QA)
def pack_download(request, pk):
    v = get_vendor(request)
    pack = get_object_or_404(Pack.objects.for_vendor(v), id=pk)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("pack.json", bytes(pack.body))
        z.writestr("pack.sig", bytes.fromhex(pack.signature))
    buf.seek(0)
    AuditLog.append(v, request.user.email, "pack_download", "pack", pack.id)
    unit_code = pack.unit.code if pack.unit else "ALL"
    resp = FileResponse(buf, as_attachment=True,
                        filename=f"manar_pack_{v.code}_{unit_code}_v{pack.version}.mpk")
    return resp

@role_required("admin", "qa")
def sync_upload(request):
    v = get_vendor(request)
    if request.method == "POST":
        if "zip" not in request.FILES:
            messages.error(request, "No zip file uploaded.")
            return redirect("sync_upload")
        f = request.FILES["zip"]
        with zipfile.ZipFile(f) as z:
            summary = json.loads(z.read("summary.json"))
            chain = json.loads(z.read("chain.json")) if "chain.json" in z.namelist() else []
        up = SyncUpload.objects.create(
            vendor=v, uploaded_by=request.user.email,
            filename=f.name, summary=summary, chain=chain)
        AuditLog.append(v, request.user.email, "sync_upload", "syncupload", up.id)
        messages.success(request, f"Uploaded {f.name}")
        return redirect("dashboard")
    return render(request, "upload.html", {})

@role_required(*READ)
def verify_record(request):
    v = get_vendor(request)
    h = request.GET.get("hash", "").strip().lower()
    hit = None
    if len(h) == 64:
        hit = SyncUpload.objects.for_vendor(v).filter(chain__contains=[h]).first()
    return render(request, "verify.html", {"hash": h, "hit": hit})

@role_required(*READ)
def aggregates(request):
    v = get_vendor(request)
    return render(request, "aggregates.html", {
        "ups": SyncUpload.objects.for_vendor(v).order_by("-created_at")[:20]})

@role_required("admin")
@require_POST
def station_transfer(request, pk):
    v = get_vendor(request)
    st = get_object_or_404(Station.objects.for_vendor(v), id=pk)
    unit = get_object_or_404(Unit.objects.for_vendor(v), id=request.POST["unit"])
    st.unit = unit
    st.save()
    AuditLog.append(v, request.user.email, "station_transfer",
                    "station", st.id, {"to": unit.code})
    messages.success(request, f"Station {st.station_code} transferred to unit {unit.code}.")
    return redirect("dashboard")
