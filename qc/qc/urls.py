from django.contrib import admin
from django.http import JsonResponse
from django.urls import path

from core import auth_views, sso, views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", lambda r: JsonResponse({"ok": True}), name="healthz"),
    path("accounts/activate/", auth_views.activate, name="activate"),
    path("accounts/login/", auth_views.login_view, name="login"),
    path("accounts/logout/", auth_views.logout_view, name="logout"),
    path("sso/login/", sso.sso_login, name="sso_login"),
    path("sso/callback/", sso.sso_callback, name="sso_callback"),
    path("", views.dashboard, name="dashboard"),
    path("buyers/", views.buyers, name="buyers"),
    path("styles/", views.styles, name="styles"),
    path("style/<uuid:pk>/", views.style_detail, name="style_detail"),
    path("style/<uuid:pk>/import/", views.run_import, name="run_import"),
    path("style/<uuid:pk>/validate/", views.validate_style, name="validate_style"),
    path("specrow/<uuid:pk>/", views.spec_row_update, name="spec_row_update"),
    path("specrow/<uuid:pk>/delete/", views.spec_row_delete, name="spec_row_delete"),
    path("specset/<uuid:pk>/row/add/", views.spec_row_add, name="spec_row_add"),
    path("workorders/", views.workorders, name="workorders"),
    path("workorder/<uuid:pk>/lay/", views.add_lay, name="add_lay"),
    path("lay/<uuid:pk>/bundles/", views.add_bundles, name="add_bundles"),
    path("bundle/<uuid:pk>/ticket/", views.bundle_ticket, name="bundle_ticket"),
    path("unit/<uuid:pk>/pack/build/", views.pack_build, name="pack_build"),
    path("pack/<uuid:pk>/download/", views.pack_download, name="pack_download"),
    path("sync/upload/", views.sync_upload, name="sync_upload"),
    path("verify/", views.verify_record, name="verify_record"),
    path("aggregates/", views.aggregates, name="aggregates"),
    path("station/<uuid:pk>/transfer/", views.station_transfer, name="station_transfer"),
]
