import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import auth
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import AuditLog, User, Vendor

def sso_login(request):
    if not settings.SSO_ENABLED:
        return render(request, "login.html", {"error": "SSO is disabled."})
    state, nonce = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    request.session["sso_state"], request.session["sso_nonce"] = state, nonce
    return redirect(settings.OIDC_AUTH_URL + "?" + urlencode({
        "response_type": "code",
        "client_id": settings.OIDC_CLIENT_ID,
        "redirect_uri": request.build_absolute_uri(reverse("sso_callback")),
        "scope": "openid email profile", "state": state, "nonce": nonce}))

def sso_callback(request):
    if not settings.SSO_ENABLED:
        return render(request, "login.html", {"error": "SSO is disabled."})

    if request.GET.get("state") != request.session.pop("sso_state", None):
        return render(request, "login.html", {"error": "SSO state mismatch."})

    try:
        import jwt
        import requests
        tok = requests.post(settings.OIDC_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "code": request.GET["code"],
            "redirect_uri": request.build_absolute_uri(reverse("sso_callback")),
            "client_id": settings.OIDC_CLIENT_ID,
            "client_secret": settings.OIDC_CLIENT_SECRET}, timeout=10).json()

        jwks = jwt.PyJWKClient(settings.OIDC_JWKS_URL)
        claims = jwt.decode(tok["id_token"],
                            jwks.get_signing_key_from_jwt(tok["id_token"]).key,
                            algorithms=["RS256"],
                            audience=settings.OIDC_CLIENT_ID)
    except Exception as e:
        return render(request, "login.html", {"error": f"SSO authentication failed: {str(e)}"})

    if claims.get("nonce") != request.session.pop("sso_nonce", None):
        return render(request, "login.html", {"error": "SSO nonce mismatch."})

    email = claims.get("email", "").lower()
    vendor = (Vendor.objects.filter(code=settings.SELF_HOST_VENDOR).first()
              if settings.SELF_HOST_VENDOR else
              Vendor.objects.filter(code__iexact=request.GET.get("tenant", "")).first())

    if vendor is None:
        return render(request, "login.html", {"error": "No tenant associated with SSO."})

    user = User.objects.filter(vendor=vendor, email=email).first()
    if not user:
        role_claim_val = (claims.get(settings.OIDC_ROLE_CLAIM) or "").lower()
        role = settings.OIDC_ROLE_MAP.get(role_claim_val, "merch")
        user = User.objects.create_user(
            username=email, email=email,
            password=User.objects.make_random_password(32),
            vendor=vendor, role=role)

    auth.login(request, user)
    AuditLog.append(vendor, email, "sso_login", "user", user.id)
    return redirect("/")
