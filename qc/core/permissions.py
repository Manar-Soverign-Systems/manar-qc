from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from .models import Vendor

def get_vendor(request):
    """Leakage-safe by construction: every lookup goes through this."""
    u = request.user
    if not u.is_authenticated:
        return None
    if u.role == "manar":
        vid = request.GET.get("vendor") or request.session.get("staff_vendor")
        return (Vendor.objects.filter(id=vid, support_consent=True).first() if vid else None)
    return u.vendor

def role_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrap(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.path)
            if request.user.role not in roles and request.user.role != "manar":
                raise PermissionDenied
            if get_vendor(request) is None and request.user.role != "manar":
                raise PermissionDenied
            return fn(request, *args, **kwargs)
        return wrap
    return deco
