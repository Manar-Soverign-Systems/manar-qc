from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import ActivationCode, AuditLog, User, Vendor

def _locked(ip):
    return (cache.get_or_set(f"lock:{ip}", 0, 900) >= 5)

def _bump(ip):
    try:
        cache.incr(f"lock:{ip}")
    except ValueError:
        cache.set(f"lock:{ip}", 1, 900)

def activate(request):
    error, vendor, ac = None, None, None
    if request.method == "POST":
        if request.POST.get("step") == "check":
            ac = ActivationCode.objects.filter(
                code=request.POST.get("code", "").strip(),
                used_at=None, expires_at__gt=timezone.now()).first()
            if not ac:
                error = "Invalid or expired code. Contact Manar."
            else:
                request.session["activation"] = str(ac.id)
                vendor = ac.vendor
        else:
            ac_id = request.session.get("activation")
            ac = ActivationCode.objects.filter(id=ac_id, used_at=None).first()
            if not ac:
                error = "Restart activation."
            else:
                email = request.POST.get("email", "").lower().strip()
                password = request.POST.get("password", "")
                if User.objects.filter(vendor=ac.vendor, email=email).exists():
                    error = "Account exists — use login."
                elif len(password) < 12:
                    error = "Password must be 12+ characters."
                else:
                    u = User.objects.create_user(
                        username=email, email=email,
                        password=password,
                        vendor=ac.vendor, role="admin")
                    ac.used_at = timezone.now()
                    ac.save()
                    AuditLog.append(ac.vendor, email, "activate", "user", u.id)
                    auth.login(request, u)
                    return redirect("/")
    elif request.session.get("activation"):
        ac = ActivationCode.objects.filter(id=request.session["activation"]).first()
        vendor = ac.vendor if ac else None

    return render(request, "activate.html", {"error": error, "vendor": vendor})

def login_view(request):
    error = None
    if request.method == "POST":
        ip = request.META.get("REMOTE_ADDR", "")
        if _locked(ip):
            error = "Too many attempts. Try later."
        else:
            code = request.POST.get("tenant", "").strip()
            email = request.POST.get("email", "").lower().strip()
            password = request.POST.get("password", "")
            vendor = Vendor.objects.filter(code__iexact=code, status="active").first()
            user = auth.authenticate(request, username=email, password=password)
            if user and (user.role == "manar" or (vendor and user.vendor_id == vendor.id)):
                auth.login(request, user)
                return redirect("/")
            _bump(ip)
            error = "Login failed."
    return render(request, "login.html", {"error": error})

@login_required
def logout_view(request):
    auth.logout(request)
    return redirect("/accounts/login/")
