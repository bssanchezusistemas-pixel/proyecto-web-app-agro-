"""
Configuración de URLs de agro_config.
Expone el panel administrativo, todos los endpoints REST (/api/...) y sirve el SPA de React (frontend_dist).
"""

import mimetypes
from pathlib import Path

from django.contrib import admin
from django.http import FileResponse, HttpResponse, JsonResponse
from django.urls import path, re_path

from cultivos import views

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BASE_DIR / "frontend_dist"


def serve_spa_asset(_request, asset_path: str):
    target = (FRONTEND_DIST / asset_path).resolve()
    if not str(target).startswith(str(FRONTEND_DIST.resolve())) or not target.is_file():
        return HttpResponse(status=404)
    content_type, _ = mimetypes.guess_type(str(target))
    return FileResponse(open(target, "rb"), content_type=content_type or "application/octet-stream")


def serve_spa_index(_request):
    index_file = FRONTEND_DIST / "index.html"
    if index_file.is_file():
        return HttpResponse(index_file.read_text(encoding="utf-8"), content_type="text/html; charset=utf-8")
    return JsonResponse({
        "status": "ok",
        "servicio": "API Sistema de Gestión de Cultivos (Django + Supabase)",
        "frontend_url": "https://proyecto-web-app-agro-frontend.vercel.app",
    })


urlpatterns = [
    path("admin/", admin.site.urls),

    # Autenticación
    re_path(r"^api/auth/login/?$", views.auth_login, name="api_auth_login"),
    re_path(r"^api/auth/yo/?$", views.auth_yo, name="api_auth_yo"),

    # Empleados
    re_path(r"^api/empleados/?$", views.empleados_collection, name="api_empleados"),
    re_path(r"^api/empleados/(?P<empleado_id>[^/]+)/?$", views.empleado_detail, name="api_empleado_detail"),

    # Cultivos y Lotes
    re_path(r"^api/cultivos/?$", views.cultivos_collection, name="api_cultivos"),
    re_path(r"^api/cultivos/(?P<cultivo_id>[^/]+)/?$", views.cultivo_detail, name="api_cultivo_detail"),
    re_path(r"^api/lotes/?$", views.lotes_collection, name="api_lotes"),
    re_path(r"^api/lotes/(?P<lote_id>[^/]+)/?$", views.lote_detail, name="api_lote_detail"),

    # Ciclos Productivos
    re_path(r"^api/ciclos/estado/?$", views.ciclos_estado, name="api_ciclos_estado"),
    re_path(r"^api/ciclos/(?P<ciclo_id>[^/]+)/cerrar/?$", views.ciclo_cerrar, name="api_ciclo_cerrar"),
    re_path(r"^api/ciclos/?$", views.ciclos_collection, name="api_ciclos"),

    # Labores de Campo
    re_path(r"^api/labores/proximas/?$", views.labores_proximas, name="api_labores_proximas"),
    re_path(r"^api/labores/(?P<labor_id>[^/]+)/ejecutar/?$", views.labor_ejecutar, name="api_labor_ejecutar"),
    re_path(r"^api/labores/(?P<labor_id>[^/]+)/?$", views.labor_detail, name="api_labor_detail"),
    re_path(r"^api/labores/?$", views.labores_collection, name="api_labores"),

    # Cosechas
    re_path(r"^api/cosechas/(?P<cosecha_id>[^/]+)/?$", views.cosecha_detail, name="api_cosecha_detail"),
    re_path(r"^api/cosechas/?$", views.cosechas_collection, name="api_cosechas"),

    # Reportes y Exportación
    re_path(r"^api/reportes/resumen/?$", views.reportes_resumen, name="api_reportes_resumen"),
    re_path(r"^api/reportes/ciclos/?$", views.reportes_ciclos, name="api_reportes_ciclos"),
    re_path(r"^api/reportes/costos/?$", views.reportes_costos, name="api_reportes_costos"),
    re_path(r"^api/reportes/historial/?$", views.reportes_historial, name="api_reportes_historial"),
    re_path(r"^api/reportes/exportar/csv/?$", views.reportes_exportar_csv, name="api_reportes_exportar_csv"),
    re_path(r"^api/reportes/exportar/excel/?$", views.reportes_exportar_excel, name="api_reportes_exportar_excel"),

    # Archivos estáticos del Frontend compilado (React + Vite)
    re_path(r"^(?P<asset_path>assets/.+|favicon\.svg|icons\.svg)$", serve_spa_asset, name="spa_assets"),

    # Rutas del Frontend SPA (React Router)
    re_path(r"^(?:login|empleados|cultivos|ciclos|labores|cosechas|reportes)?/?$", serve_spa_index, name="spa_index"),
]
