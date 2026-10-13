"""
Vistas y Endpoints REST API (/api/...) para el Sistema de Gestión de Cultivos.
Conecta el frontend en React (Vite) con los modelos de dominio en Django (B1 y B2).
"""

import csv
import io
import json
import re
import zipfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape as xml_escape

from django.contrib.auth.models import User
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Q, Sum
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import (
    CicloProductivo,
    Cosecha,
    Cultivo,
    Empleado,
    Fertilizacion,
    Fumigacion,
    Labor,
    Lote,
    OtraLabor,
)

TOKEN_SALT = "agro-auth-token-v1"
TOKEN_MAX_AGE = 60 * 60 * 24 * 7  # 7 días


# ==============================================================================
# UTILIDADES DE AUTENTICACIÓN, PARSEO Y MANEJO DE ERRORES
# ==============================================================================

def asegurar_usuarios_por_defecto() -> None:
    """Crea los usuarios por defecto (administrador y operario) si no existen."""
    cuentas = ("admin@cultivos.com", "operario@cultivos.com", "empleado@cultivos.com")
    existentes = set(
        User.objects.filter(username__in=cuentas).values_list("username", flat=True)
    )
    if len(existentes) == len(cuentas):
        return

    if "admin@cultivos.com" not in existentes:
        admin_user = User(
            username="admin@cultivos.com",
            email="admin@cultivos.com",
            first_name="Administrador",
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )
        admin_user.set_password("admin123")
        admin_user.save()

    if "operario@cultivos.com" not in existentes:
        op_user = User(
            username="operario@cultivos.com",
            email="operario@cultivos.com",
            first_name="Operario de Campo",
            is_staff=False,
            is_superuser=False,
            is_active=True,
        )
        op_user.set_password("operario123")
        op_user.save()

    if "empleado@cultivos.com" not in existentes:
        emp_user = User(
            username="empleado@cultivos.com",
            email="empleado@cultivos.com",
            first_name="Empleado de Campo",
            is_staff=False,
            is_superuser=False,
            is_active=True,
        )
        emp_user.set_password("empleado123")
        emp_user.save()



def generar_token(usuario: User) -> str:
    payload = {
        "uid": usuario.id,
        "username": usuario.username,
        "rol": "administrador" if (usuario.is_staff or usuario.is_superuser) else "operario",
    }
    return signing.dumps(payload, salt=TOKEN_SALT)


def obtener_usuario_autenticado(request: HttpRequest) -> Optional[User]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        datos = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)
        return User.objects.filter(pk=datos.get("uid"), is_active=True).first()
    except Exception:
        return None


def parsear_json(request: HttpRequest) -> Dict[str, Any]:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except Exception:
        raise ValueError("El cuerpo de la petición no es un JSON válido.")


def parsear_fecha(valor: Any, nombre_campo: str = "fecha") -> Optional[date]:
    if valor in (None, ""):
        return None
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor
    try:
        return date.fromisoformat(str(valor).strip()[:10])
    except Exception:
        raise ValidationError({nombre_campo: f"Formato de fecha inválido en '{nombre_campo}': {valor}"})


def parsear_decimal_positivo(valor: Any, por_defecto: str = "1.00") -> Decimal:
    if valor in (None, ""):
        return Decimal(por_defecto)
    if isinstance(valor, (int, float, Decimal)):
        try:
            dec = Decimal(str(valor))
            return dec if dec > 0 else Decimal(por_defecto)
        except InvalidOperation:
            return Decimal(por_defecto)
    coincidencia = re.search(r"(\d+(?:[.,]\d+)?)", str(valor))
    if coincidencia:
        numero_str = coincidencia.group(1).replace(",", ".")
        try:
            dec = Decimal(numero_str)
            return dec if dec > 0 else Decimal(por_defecto)
        except InvalidOperation:
            pass
    return Decimal(por_defecto)


def formatear_error_validacion(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        if hasattr(exc, "message_dict"):
            mensajes = []
            for campo, lista in exc.message_dict.items():
                for msg in lista:
                    mensajes.append(str(msg))
            if mensajes:
                return " ".join(mensajes)
        if hasattr(exc, "messages") and exc.messages:
            return " ".join(str(m) for m in exc.messages)
    return str(exc)


def respuesta_error(mensaje: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"detail": mensaje}, status=status)


# ==============================================================================
# SERIALIZADORES A DICCIONARIOS JSON
# ==============================================================================

def serializar_empleado(e: Empleado) -> Dict[str, Any]:
    return {
        "id": str(e.id),
        "nombre": e.nombre,
        "documento": e.documento,
        "cargo": e.cargo,
        "telefono": e.telefono or "",
        "fecha_ingreso": e.fecha_ingreso.isoformat() if e.fecha_ingreso else None,
        "activo": bool(e.activo),
    }


def serializar_cultivo(c: Cultivo) -> Dict[str, Any]:
    return {
        "id": str(c.id),
        "nombre": c.nombre,
        "variedad": c.variedad or "",
        "dias_ciclo": int(c.dias_a_cosecha),
        "dias_a_cosecha": int(c.dias_a_cosecha),
        "periodo_carencia_dias": int(c.periodo_carencia_dias or 0),
        "activo": bool(c.activo),
    }


def serializar_lote(l: Lote, cultivo_override: Optional[Cultivo] = None) -> Dict[str, Any]:
    cultivo_obj = cultivo_override or l.cultivo
    if not cultivo_obj:
        ciclo_act = l.obtener_ciclo_activo()
        if ciclo_act:
            cultivo_obj = ciclo_act.cultivo
    return {
        "id": str(l.id),
        "nombre": l.nombre,
        "ubicacion": l.ubicacion or "",
        "area_hectareas": float(l.area_ha),
        "area_ha": float(l.area_ha),
        "cultivo_id": str(cultivo_obj.id) if cultivo_obj else None,
        "cultivo": serializar_cultivo(cultivo_obj) if cultivo_obj else None,
        "activo": bool(l.activo),
    }


def serializar_ciclo(c: CicloProductivo) -> Dict[str, Any]:
    fecha_est = c.fecha_estimada_cosecha()
    return {
        "id": str(c.id),
        "lote_id": str(c.lote_id),
        "cultivo_id": str(c.cultivo_id),
        "lote": serializar_lote(c.lote, cultivo_override=c.cultivo),
        "cultivo": serializar_cultivo(c.cultivo),
        "responsable": serializar_empleado(c.responsable) if c.responsable else None,
        "fecha_inicio": c.fecha_siembra.isoformat(),
        "fecha_siembra": c.fecha_siembra.isoformat(),
        "fecha_fin_estimada": fecha_est.isoformat(),
        "dias_transcurridos": c.dias_transcurridos(),
        "dias_restantes": (fecha_est - date.today()).days,
        "etapa": c.etapa,
        "estado": c.estado,
        "observaciones": c.observaciones or "",
    }


def obtener_metadatos_labor(labor: Labor) -> Dict[str, str]:
    especifica = labor.obtener_instancia_especifica()
    tipo = "otra"
    producto = labor.producto_insumo or ""
    dosis = labor.dosis_cantidad or ""

    if isinstance(especifica, Fumigacion):
        tipo = "fumigacion"
        if not producto:
            producto = especifica.producto
        if not dosis:
            dosis = str(especifica.dosis)
    elif isinstance(especifica, Fertilizacion):
        tipo = "fertilizacion"
        if not producto:
            producto = especifica.tipo_abono
        if not dosis:
            dosis = f"{especifica.cantidad} {especifica.unidad}".strip()
    elif isinstance(especifica, OtraLabor):
        tipo = (especifica.tipo or "otra").strip().lower()

    estado_ui = "ejecutada" if labor.estado == "realizada" else labor.estado
    fecha_prog = labor.fecha_programada or labor.fecha
    fecha_ejec = labor.fecha_ejecucion
    if estado_ui == "ejecutada" and not fecha_ejec:
        fecha_ejec = labor.fecha

    return {
        "tipo": tipo,
        "producto": producto,
        "dosis": dosis,
        "estado": estado_ui,
        "fecha_programada": fecha_prog.isoformat() if fecha_prog else labor.fecha.isoformat(),
        "fecha_ejecucion": fecha_ejec.isoformat() if fecha_ejec else None,
    }


def serializar_labor(labor: Labor) -> Dict[str, Any]:
    meta = obtener_metadatos_labor(labor)
    return {
        "id": str(labor.id),
        "ciclo_id": str(labor.ciclo_id),
        "empleado_id": str(labor.responsable_id),
        "empleado": serializar_empleado(labor.responsable) if labor.responsable else None,
        "tipo": meta["tipo"],
        "fecha_programada": meta["fecha_programada"],
        "fecha_ejecucion": meta["fecha_ejecucion"],
        "producto": meta["producto"] or None,
        "dosis": meta["dosis"] or None,
        "costo": float(labor.costo),
        "estado": meta["estado"],
        "observaciones": labor.observaciones or "",
    }


def serializar_cosecha(c: Cosecha) -> Dict[str, Any]:
    return {
        "id": str(c.id),
        "ciclo_id": str(c.ciclo_id),
        "empleado_id": str(c.empleado_id),
        "empleado": serializar_empleado(c.empleado) if c.empleado else None,
        "fecha": c.fecha.isoformat(),
        "kilos": float(c.kilos),
        "calidad": c.calidad or None,
        "observaciones": c.observaciones or None,
    }


# ==============================================================================
# 1. ENDPOINTS DE AUTENTICACIÓN
# ==============================================================================

@csrf_exempt
def auth_login(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return respuesta_error("Método no permitido.", status=405)

    asegurar_usuarios_por_defecto()

    username = ""
    password = ""
    content_type = request.headers.get("Content-Type", "")
    if "application/json" in content_type:
        try:
            datos = parsear_json(request)
            username = str(datos.get("username") or datos.get("email") or "").strip()
            password = str(datos.get("password") or "")
        except ValueError as e:
            return respuesta_error(str(e), status=400)
    else:
        username = (request.POST.get("username") or request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""

    if not username or not password:
        return respuesta_error("Debe ingresar correo y contraseña.", status=400)

    usuario = User.objects.filter(
        Q(username__iexact=username) | Q(email__iexact=username)
    ).first()
    if not usuario or not usuario.is_active or not usuario.check_password(password):
        return respuesta_error("Correo o contraseña incorrectos.", status=401)

    token = generar_token(usuario)
    rol = "administrador" if (usuario.is_staff or usuario.is_superuser) else "operario"
    nombre = usuario.get_full_name().strip() or usuario.first_name or usuario.username
    return JsonResponse({
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario.id,
            "nombre": nombre,
            "email": usuario.email or usuario.username,
            "rol": rol,
        },
    })


@csrf_exempt
def auth_yo(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return respuesta_error("Método no permitido.", status=405)

    usuario = obtener_usuario_autenticado(request)
    if not usuario:
        return respuesta_error("Sesión inválida o expirada.", status=401)

    rol = "administrador" if (usuario.is_staff or usuario.is_superuser) else "operario"
    nombre = usuario.get_full_name().strip() or usuario.first_name or usuario.username
    return JsonResponse({
        "id": usuario.id,
        "nombre": nombre,
        "email": usuario.email or usuario.username,
        "rol": rol,
    })


# ==============================================================================
# 2. ENDPOINTS DE EMPLEADOS
# ==============================================================================

@csrf_exempt
def empleados_collection(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        qs = Empleado.objects.all()
        if request.GET.get("solo_activos", "").lower() in ("true", "1", "yes"):
            qs = qs.filter(activo=True)
        return JsonResponse([serializar_empleado(e) for e in qs], safe=False)

    if request.method == "POST":
        try:
            datos = parsear_json(request)
            fecha_ing = parsear_fecha(datos.get("fecha_ingreso"), "fecha_ingreso") or date.today()
            emp = Empleado(
                nombre=datos.get("nombre") or "",
                documento=datos.get("documento") or "",
                cargo=datos.get("cargo") or "",
                telefono=datos.get("telefono") or "",
                fecha_ingreso=fecha_ing,
                activo=datos.get("activo", True),
            )
            emp.save()
            return JsonResponse(serializar_empleado(emp), status=201)
        except (ValidationError, ValueError, IntegrityError) as e:
            return respuesta_error(formatear_error_validacion(e), status=400)

    return respuesta_error("Método no permitido.", status=405)


@csrf_exempt
def empleado_detail(request: HttpRequest, empleado_id: str) -> JsonResponse:
    try:
        emp = Empleado.objects.filter(pk=empleado_id).first()
    except (ValidationError, ValueError):
        emp = None

    if not emp:
        return respuesta_error("Empleado no encontrado.", status=404)

    if request.method == "GET":
        return JsonResponse(serializar_empleado(emp))

    if request.method == "PUT":
        try:
            datos = parsear_json(request)
            if "nombre" in datos:
                emp.nombre = datos.get("nombre") or ""
            if "documento" in datos:
                emp.documento = datos.get("documento") or ""
            if "cargo" in datos:
                emp.cargo = datos.get("cargo") or ""
            if "telefono" in datos:
                emp.telefono = datos.get("telefono") or ""
            if "activo" in datos and datos["activo"] is not None:
                emp.activo = bool(datos["activo"])
            if "fecha_ingreso" in datos and datos["fecha_ingreso"]:
                emp.fecha_ingreso = parsear_fecha(datos["fecha_ingreso"], "fecha_ingreso")
            emp.save()
            return JsonResponse(serializar_empleado(emp))
        except (ValidationError, ValueError, IntegrityError) as e:
            return respuesta_error(formatear_error_validacion(e), status=400)

    if request.method == "DELETE":
        emp.desactivar()
        return JsonResponse(serializar_empleado(emp))

    return respuesta_error("Método no permitido.", status=405)


# ==============================================================================
# 3. ENDPOINTS DE CULTIVOS Y LOTES
# ==============================================================================

@csrf_exempt
def cultivos_collection(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        qs = Cultivo.objects.all()
        if request.GET.get("solo_activos", "").lower() in ("true", "1", "yes"):
            qs = qs.filter(activo=True)
        return JsonResponse([serializar_cultivo(c) for c in qs], safe=False)

    if request.method == "POST":
        try:
            datos = parsear_json(request)
            dias = datos.get("dias_ciclo", datos.get("dias_a_cosecha", 0))
            carencia = datos.get("periodo_carencia_dias", 0)
            cultivo = Cultivo(
                nombre=datos.get("nombre") or "",
                variedad=datos.get("variedad") or "",
                dias_a_cosecha=int(dias or 0),
                periodo_carencia_dias=max(0, int(carencia or 0)),
                activo=bool(datos.get("activo", True)),
            )
            cultivo.save()
            return JsonResponse(serializar_cultivo(cultivo), status=201)
        except (ValidationError, ValueError, TypeError, IntegrityError) as e:
            return respuesta_error(formatear_error_validacion(e), status=400)

    return respuesta_error("Método no permitido.", status=405)


@csrf_exempt
def cultivo_detail(request: HttpRequest, cultivo_id: str) -> JsonResponse:
    try:
        cultivo = Cultivo.objects.filter(pk=cultivo_id).first()
    except (ValidationError, ValueError):
        cultivo = None

    if not cultivo:
        return respuesta_error("Cultivo no encontrado.", status=404)

    if request.method == "GET":
        return JsonResponse(serializar_cultivo(cultivo))

    if request.method == "PUT":
        try:
            datos = parsear_json(request)
            if "nombre" in datos:
                cultivo.nombre = datos.get("nombre") or ""
            if "variedad" in datos:
                cultivo.variedad = datos.get("variedad") or ""
            if "dias_ciclo" in datos or "dias_a_cosecha" in datos:
                dias = datos.get("dias_ciclo", datos.get("dias_a_cosecha"))
                cultivo.dias_a_cosecha = int(dias or 0)
            if "periodo_carencia_dias" in datos:
                cultivo.periodo_carencia_dias = max(0, int(datos.get("periodo_carencia_dias") or 0))
            if "activo" in datos and datos["activo"] is not None:
                cultivo.activo = bool(datos["activo"])
            cultivo.save()
            return JsonResponse(serializar_cultivo(cultivo))
        except (ValidationError, ValueError, TypeError, IntegrityError) as e:
            return respuesta_error(formatear_error_validacion(e), status=400)

    if request.method == "DELETE":
        cultivo.activo = False
        cultivo.save(update_fields=["activo"])
        return JsonResponse(serializar_cultivo(cultivo))

    return respuesta_error("Método no permitido.", status=405)


def _resolver_cultivo(cultivo_id: Any) -> Optional[Cultivo]:
    if not cultivo_id:
        return None
    try:
        return Cultivo.objects.filter(pk=str(cultivo_id)).first()
    except (ValidationError, ValueError):
        return None


@csrf_exempt
def lotes_collection(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        lotes = Lote.objects.select_related("cultivo").all()
        return JsonResponse([serializar_lote(l) for l in lotes], safe=False)

    if request.method == "POST":
        try:
            datos = parsear_json(request)
            area = datos.get("area_hectareas", datos.get("area_ha", 0))
            cultivo_obj = _resolver_cultivo(datos.get("cultivo_id"))
            lote = Lote(
                nombre=datos.get("nombre") or "",
                ubicacion=datos.get("ubicacion") or "",
                area_ha=Decimal(str(area or 0)),
                cultivo=cultivo_obj,
                activo=bool(datos.get("activo", True)),
            )
            lote.save()
            return JsonResponse(serializar_lote(lote), status=201)
        except (ValidationError, ValueError, InvalidOperation, IntegrityError) as e:
            return respuesta_error(formatear_error_validacion(e), status=400)

    return respuesta_error("Método no permitido.", status=405)


@csrf_exempt
def lote_detail(request: HttpRequest, lote_id: str) -> JsonResponse:
    try:
        lote = Lote.objects.select_related("cultivo").filter(pk=lote_id).first()
    except (ValidationError, ValueError):
        lote = None

    if not lote:
        return respuesta_error("Lote no encontrado.", status=404)

    if request.method == "GET":
        return JsonResponse(serializar_lote(lote))

    if request.method == "PUT":
        try:
            datos = parsear_json(request)
            if "nombre" in datos:
                lote.nombre = datos.get("nombre") or ""
            if "ubicacion" in datos:
                lote.ubicacion = datos.get("ubicacion") or ""
            if "area_hectareas" in datos or "area_ha" in datos:
                area = datos.get("area_hectareas", datos.get("area_ha", 0))
                lote.area_ha = Decimal(str(area or 0))
            if "cultivo_id" in datos:
                lote.cultivo = _resolver_cultivo(datos.get("cultivo_id"))
            if "activo" in datos and datos["activo"] is not None:
                lote.activo = bool(datos["activo"])
            lote.save()
            return JsonResponse(serializar_lote(lote))
        except (ValidationError, ValueError, InvalidOperation, IntegrityError) as e:
            return respuesta_error(formatear_error_validacion(e), status=400)

    if request.method == "DELETE":
        lote.activo = False
        lote.save(update_fields=["activo"])
        return JsonResponse(serializar_lote(lote))

    return respuesta_error("Método no permitido.", status=405)


# ==============================================================================
# 4. ENDPOINTS DE CICLOS PRODUCTIVOS
# ==============================================================================

@csrf_exempt
def ciclos_collection(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        qs = CicloProductivo.objects.select_related("lote", "lote__cultivo", "cultivo", "responsable").all()
        estado = request.GET.get("estado", "").strip().lower()
        if estado:
            qs = qs.filter(estado=estado)
        return JsonResponse([serializar_ciclo(c) for c in qs], safe=False)

    if request.method == "POST":
        try:
            datos = parsear_json(request)
            lote_id = datos.get("lote_id")
            if not lote_id:
                return respuesta_error("Debe seleccionar un lote válido.", status=400)

            try:
                lote = Lote.objects.select_related("cultivo").filter(pk=str(lote_id)).first()
            except (ValidationError, ValueError):
                lote = None

            if not lote:
                return respuesta_error("El lote seleccionado no existe.", status=404)

            cultivo_obj = _resolver_cultivo(datos.get("cultivo_id")) or lote.cultivo
            if not cultivo_obj:
                cultivo_obj = Cultivo.objects.filter(activo=True).first()
            if not cultivo_obj:
                return respuesta_error(
                    "El lote no tiene un cultivo asignado. Asigna un cultivo al lote antes de iniciar el ciclo.",
                    status=400,
                )

            # Si el lote no tenía cultivo guardado, vincularlo
            if not lote.cultivo_id:
                lote.cultivo = cultivo_obj
                lote.save(update_fields=["cultivo"])

            fecha_str = datos.get("fecha_inicio") or datos.get("fecha_siembra")
            fecha_siembra = parsear_fecha(fecha_str, "fecha_siembra") or date.today()

            responsable = None
            if datos.get("responsable_id"):
                try:
                    responsable = Empleado.objects.filter(pk=str(datos["responsable_id"])).first()
                except (ValidationError, ValueError):
                    responsable = None

            ciclo = CicloProductivo.iniciar(
                lote=lote,
                cultivo=cultivo_obj,
                fecha=fecha_siembra,
                responsable=responsable,
                observaciones=datos.get("observaciones") or "",
            )
            return JsonResponse(serializar_ciclo(ciclo), status=201)
        except (ValidationError, ValueError, IntegrityError) as e:
            return respuesta_error(formatear_error_validacion(e), status=400)

    return respuesta_error("Método no permitido.", status=405)


@csrf_exempt
def ciclos_estado(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return respuesta_error("Método no permitido.", status=405)

    activos = CicloProductivo.objects.select_related("lote", "cultivo").filter(estado="activo")
    resultado = []
    for c in activos:
        dias_trans = max(0, c.dias_transcurridos())
        dias_ciclo_total = max(1, int(c.cultivo.dias_a_cosecha))
        fecha_fin = c.fecha_estimada_cosecha()
        dias_rest = (fecha_fin - date.today()).days
        porcentaje = min(100, max(0, round((dias_trans / dias_ciclo_total) * 100)))
        resultado.append({
            "id": str(c.id),
            "lote": c.lote.nombre,
            "cultivo": c.cultivo.nombre,
            "dias_transcurridos": dias_trans,
            "dias_restantes": dias_rest,
            "porcentaje_avance": porcentaje,
            "fecha_inicio": c.fecha_siembra.isoformat(),
            "fecha_fin_estimada": fecha_fin.isoformat(),
            "etapa": c.etapa,
            "estado": c.estado,
        })
    return JsonResponse(resultado, safe=False)


@csrf_exempt
def ciclo_cerrar(request: HttpRequest, ciclo_id: str) -> JsonResponse:
    if request.method != "POST":
        return respuesta_error("Método no permitido.", status=405)

    try:
        ciclo = CicloProductivo.objects.select_related("lote", "cultivo", "responsable").filter(pk=ciclo_id).first()
    except (ValidationError, ValueError):
        ciclo = None

    if not ciclo:
        return respuesta_error("Ciclo productivo no encontrado.", status=404)

    ciclo.cerrar_ciclo()
    return JsonResponse(serializar_ciclo(ciclo))


# ==============================================================================
# 5. ENDPOINTS DE LABORES DE CAMPO
# ==============================================================================

@csrf_exempt
def labores_collection(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        qs = Labor.objects.select_related(
            "ciclo", "ciclo__lote", "ciclo__cultivo", "responsable",
            "fumigacion", "fertilizacion", "otralabor"
        ).all()
        tipo_filtro = request.GET.get("tipo", "").strip().lower()
        items = [serializar_labor(l) for l in qs]
        if tipo_filtro and tipo_filtro != "todas":
            items = [item for item in items if item["tipo"].lower() == tipo_filtro]
        return JsonResponse(items, safe=False)

    if request.method == "POST":
        try:
            datos = parsear_json(request)
            ciclo_id = datos.get("ciclo_id")
            empleado_id = datos.get("empleado_id") or datos.get("responsable_id")

            if not ciclo_id:
                return respuesta_error("Debe seleccionar un ciclo productivo.", status=400)
            if not empleado_id:
                return respuesta_error("Debe seleccionar un empleado responsable.", status=400)

            try:
                ciclo = CicloProductivo.objects.select_related("cultivo", "lote").filter(pk=str(ciclo_id)).first()
            except (ValidationError, ValueError):
                ciclo = None
            if not ciclo:
                return respuesta_error("Ciclo productivo no encontrado.", status=404)

            try:
                empleado = Empleado.objects.filter(pk=str(empleado_id)).first()
            except (ValidationError, ValueError):
                empleado = None
            if not empleado:
                return respuesta_error("Empleado responsable no encontrado.", status=404)

            tipo_req = str(datos.get("tipo") or "otra").strip().lower()
            fecha_prog = parsear_fecha(datos.get("fecha_programada") or datos.get("fecha"), "fecha_programada") or date.today()
            fecha_ejec = parsear_fecha(datos.get("fecha_ejecucion"), "fecha_ejecucion")

            estado = "ejecutada" if fecha_ejec else "programada"
            fecha_efectiva = fecha_ejec or fecha_prog

            costo = Decimal(str(datos.get("costo") or 0))
            producto_txt = (datos.get("producto") or "").strip()
            dosis_txt = (datos.get("dosis") or "").strip()
            observaciones = (datos.get("observaciones") or "").strip()

            if tipo_req == "fumigacion":
                carencia = datos.get("periodo_carencia")
                if carencia is None:
                    carencia = ciclo.cultivo.periodo_carencia_dias or 0
                labor = Fumigacion(
                    ciclo=ciclo,
                    responsable=empleado,
                    fecha=fecha_efectiva,
                    fecha_programada=fecha_prog,
                    fecha_ejecucion=fecha_ejec,
                    estado=estado,
                    costo=costo,
                    producto_insumo=producto_txt,
                    dosis_cantidad=dosis_txt,
                    observaciones=observaciones,
                    producto=producto_txt or "Agroquímico general",
                    dosis=parsear_decimal_positivo(dosis_txt, "1.00"),
                    plaga_objetivo=datos.get("plaga_objetivo") or "Control fitosanitario",
                    periodo_carencia=max(0, int(carencia)),
                )
                labor.save()
            elif tipo_req == "fertilizacion":
                labor = Fertilizacion(
                    ciclo=ciclo,
                    responsable=empleado,
                    fecha=fecha_efectiva,
                    fecha_programada=fecha_prog,
                    fecha_ejecucion=fecha_ejec,
                    estado=estado,
                    costo=costo,
                    producto_insumo=producto_txt,
                    dosis_cantidad=dosis_txt,
                    observaciones=observaciones,
                    tipo_abono=producto_txt or "Fertilizante general",
                    cantidad=parsear_decimal_positivo(dosis_txt, "1.00"),
                    unidad="kg",
                )
                labor.save()
            else:
                labor = OtraLabor(
                    ciclo=ciclo,
                    responsable=empleado,
                    fecha=fecha_efectiva,
                    fecha_programada=fecha_prog,
                    fecha_ejecucion=fecha_ejec,
                    estado=estado,
                    costo=costo,
                    producto_insumo=producto_txt,
                    dosis_cantidad=dosis_txt,
                    observaciones=observaciones,
                    tipo=tipo_req,
                    descripcion=observaciones or producto_txt or f"Labor de {tipo_req}",
                )
                labor.save()

            return JsonResponse(serializar_labor(labor), status=201)
        except (ValidationError, ValueError, InvalidOperation, IntegrityError) as e:
            return respuesta_error(formatear_error_validacion(e), status=400)

    return respuesta_error("Método no permitido.", status=405)


@csrf_exempt
def labores_proximas(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return respuesta_error("Método no permitido.", status=405)

    qs = (
        Labor.objects.select_related(
            "ciclo", "ciclo__lote", "ciclo__cultivo", "responsable",
            "fumigacion", "fertilizacion", "otralabor"
        )
        .filter(estado="programada")
        .order_by("fecha_programada", "fecha")
    )
    return JsonResponse([serializar_labor(l) for l in qs], safe=False)


@csrf_exempt
def labor_ejecutar(request: HttpRequest, labor_id: str) -> JsonResponse:
    if request.method != "POST":
        return respuesta_error("Método no permitido.", status=405)

    try:
        labor = Labor.objects.select_related(
            "ciclo", "responsable", "fumigacion", "fertilizacion", "otralabor"
        ).filter(pk=labor_id).first()
    except (ValidationError, ValueError):
        labor = None

    if not labor:
        return respuesta_error("Labor no encontrada.", status=404)

    try:
        datos = parsear_json(request)
        fecha_ejec = parsear_fecha(datos.get("fecha_ejecucion"), "fecha_ejecucion") or date.today()
        labor.marcar_realizada(fecha_ejec=fecha_ejec)
        return JsonResponse(serializar_labor(labor))
    except (ValidationError, ValueError) as e:
        return respuesta_error(formatear_error_validacion(e), status=400)


@csrf_exempt
def labor_detail(request: HttpRequest, labor_id: str) -> JsonResponse:
    try:
        labor = Labor.objects.select_related(
            "ciclo", "responsable", "fumigacion", "fertilizacion", "otralabor"
        ).filter(pk=labor_id).first()
    except (ValidationError, ValueError):
        labor = None

    if not labor:
        return respuesta_error("Labor no encontrada.", status=404)

    if request.method == "DELETE":
        labor.estado = "cancelada"
        labor.save(update_fields=["estado"])
        return JsonResponse(serializar_labor(labor))

    if request.method == "GET":
        return JsonResponse(serializar_labor(labor))

    return respuesta_error("Método no permitido.", status=405)


# ==============================================================================
# 6. ENDPOINTS DE COSECHAS
# ==============================================================================

@csrf_exempt
def cosechas_collection(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        qs = Cosecha.objects.select_related("ciclo", "ciclo__lote", "ciclo__cultivo", "empleado").all()
        return JsonResponse([serializar_cosecha(c) for c in qs], safe=False)

    if request.method == "POST":
        try:
            datos = parsear_json(request)
            ciclo_id = datos.get("ciclo_id")
            empleado_id = datos.get("empleado_id")
            if not ciclo_id:
                return respuesta_error("Debe seleccionar un ciclo productivo.", status=400)
            if not empleado_id:
                return respuesta_error("Debe seleccionar un recolector responsable.", status=400)

            try:
                ciclo = CicloProductivo.objects.select_related("cultivo", "lote").filter(pk=str(ciclo_id)).first()
            except (ValidationError, ValueError):
                ciclo = None
            if not ciclo:
                return respuesta_error("Ciclo productivo no encontrado.", status=404)

            try:
                empleado = Empleado.objects.filter(pk=str(empleado_id)).first()
            except (ValidationError, ValueError):
                empleado = None
            if not empleado:
                return respuesta_error("Empleado no encontrado.", status=404)

            fecha_cosecha = parsear_fecha(datos.get("fecha"), "fecha") or date.today()
            kilos = Decimal(str(datos.get("kilos") or 0))

            cosecha = Cosecha(
                ciclo=ciclo,
                empleado=empleado,
                fecha=fecha_cosecha,
                kilos=kilos,
                calidad=datos.get("calidad") or "",
                observaciones=datos.get("observaciones") or "",
            )
            cosecha.save()
            return JsonResponse(serializar_cosecha(cosecha), status=201)
        except (ValidationError, ValueError, InvalidOperation, IntegrityError) as e:
            return respuesta_error(formatear_error_validacion(e), status=400)

    return respuesta_error("Método no permitido.", status=405)


@csrf_exempt
def cosecha_detail(request: HttpRequest, cosecha_id: str) -> HttpResponse:
    try:
        cosecha = Cosecha.objects.filter(pk=cosecha_id).first()
    except (ValidationError, ValueError):
        cosecha = None

    if not cosecha:
        return respuesta_error("Cosecha no encontrada.", status=404)

    if request.method == "DELETE":
        cosecha.delete()
        return HttpResponse(status=204)

    return respuesta_error("Método no permitido.", status=405)


# ==============================================================================
# 7. ENDPOINTS DE REPORTES Y EXPORTACIÓN (CSV / EXCEL)
# ==============================================================================

@csrf_exempt
def reportes_resumen(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return respuesta_error("Método no permitido.", status=405)

    ciclos_activos = CicloProductivo.objects.filter(estado="activo").count()
    lotes_activos = Lote.objects.filter(activo=True).count()
    empleados_activos = Empleado.objects.filter(activo=True).count()
    labores_pendientes = Labor.objects.filter(estado="programada").count()
    kilos_totales = float(Cosecha.objects.aggregate(total=Sum("kilos"))["total"] or 0.0)
    costo_total = float(
        Labor.objects.exclude(estado="cancelada").aggregate(total=Sum("costo"))["total"] or 0.0
    )

    return JsonResponse({
        "ciclos_activos": ciclos_activos,
        "lotes": lotes_activos,
        "empleados": empleados_activos,
        "labores_pendientes": labores_pendientes,
        "kilos_totales": round(kilos_totales, 2),
        "costo_total": round(costo_total, 2),
    })


@csrf_exempt
def reportes_ciclos(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return respuesta_error("Método no permitido.", status=405)

    ciclos = (
        CicloProductivo.objects.select_related("lote", "cultivo", "responsable")
        .prefetch_related("labores", "cosechas")
        .all()
    )
    resultado = []
    for c in ciclos:
        labores_validas = [l for l in c.labores.all() if l.estado != "cancelada"]
        total_labores = len(labores_validas)
        costo_total = round(sum(float(l.costo) for l in labores_validas), 2)
        kilos = round(sum(float(cos.kilos) for cos in c.cosechas.all()), 2)
        resultado.append({
            "ciclo_id": str(c.id),
            "lote": c.lote.nombre,
            "cultivo": c.cultivo.nombre,
            "estado": c.estado,
            "total_labores": total_labores,
            "costo_total": costo_total,
            "kilos_cosechados": kilos,
        })
    return JsonResponse(resultado, safe=False)


@csrf_exempt
def reportes_costos(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return respuesta_error("Método no permitido.", status=405)

    labores = Labor.objects.select_related(
        "fumigacion", "fertilizacion", "otralabor"
    ).exclude(estado="cancelada")

    agrupado: Dict[str, Dict[str, Any]] = {}
    for l in labores:
        meta = obtener_metadatos_labor(l)
        tipo = meta["tipo"]
        if tipo not in agrupado:
            agrupado[tipo] = {"tipo": tipo, "costo_total": 0.0, "cantidad": 0}
        agrupado[tipo]["costo_total"] = round(agrupado[tipo]["costo_total"] + float(l.costo), 2)
        agrupado[tipo]["cantidad"] += 1

    return JsonResponse(list(agrupado.values()), safe=False)


def _construir_filas_historial() -> List[Dict[str, Any]]:
    labores = Labor.objects.select_related(
        "ciclo", "ciclo__lote", "ciclo__cultivo", "responsable",
        "fumigacion", "fertilizacion", "otralabor"
    ).all()
    filas = []
    for l in labores:
        meta = obtener_metadatos_labor(l)
        filas.append({
            "Fecha": meta["fecha_ejecucion"] or meta["fecha_programada"],
            "Lote": l.ciclo.lote.nombre,
            "Cultivo": l.ciclo.cultivo.nombre,
            "Tipo": meta["tipo"],
            "Estado": meta["estado"],
            "Empleado": l.responsable.nombre if l.responsable else "",
            "Producto": meta["producto"] or "",
            "Dosis": meta["dosis"] or "",
            "Costo": float(l.costo),
            "Observaciones": l.observaciones or "",
        })
    return filas


@csrf_exempt
def reportes_historial(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return respuesta_error("Método no permitido.", status=405)
    return JsonResponse(_construir_filas_historial(), safe=False)


@csrf_exempt
def reportes_exportar_csv(request: HttpRequest) -> HttpResponse:
    if request.method != "GET":
        return respuesta_error("Método no permitido.", status=405)

    filas = _construir_filas_historial()
    columnas = ["Fecha", "Lote", "Cultivo", "Tipo", "Estado", "Empleado", "Producto", "Dosis", "Costo", "Observaciones"]

    buffer = io.StringIO()
    buffer.write("\ufeff")  # BOM UTF-8 para compatibilidad directa con Excel en español
    escritor = csv.DictWriter(buffer, fieldnames=columnas)
    escritor.writeheader()
    for fila in filas:
        escritor.writerow(fila)

    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="historial_labores.csv"'
    return response


def _generar_xlsx_nativo(columnas: List[str], filas: List[Dict[str, Any]]) -> bytes:
    """
    Genera un archivo .xlsx OpenXML estándar en memoria.
    Usa openpyxl si está disponible; de lo contrario construye el paquete ZIP/XML nativo.
    """
    try:
        import openpyxl  # type: ignore

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Historial de Labores"
        ws.append(columnas)
        for fila in filas:
            ws.append([fila.get(col, "") for col in columnas])
        salida = io.BytesIO()
        wb.save(salida)
        return salida.getvalue()
    except ImportError:
        pass

    # Fallback nativo OpenXML (.xlsx) con biblioteca estándar (zipfile)
    todas_las_filas = [columnas] + [[fila.get(col, "") for col in columnas] for fila in filas]
    filas_xml = []
    for r_idx, valores in enumerate(todas_las_filas, start=1):
        celdas_xml = []
        for c_idx, val in enumerate(valores, start=1):
            col_letra = chr(64 + c_idx)
            ref = f"{col_letra}{r_idx}"
            if isinstance(val, (int, float)) and r_idx > 1:
                celdas_xml.append(f'<c r="{ref}"><v>{val}</v></c>')
            else:
                texto = xml_escape(str(val if val is not None else ""))
                celdas_xml.append(f'<c r="{ref}" t="inlineStr"><is><t>{texto}</t></is></c>')
        filas_xml.append(f'<row r="{r_idx}">{"".join(celdas_xml)}</row>')

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(filas_xml)}</sheetData>'
        '</worksheet>'
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Historial de Labores" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )

    salida = io.BytesIO()
    with zipfile.ZipFile(salida, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return salida.getvalue()


@csrf_exempt
def reportes_exportar_excel(request: HttpRequest) -> HttpResponse:
    if request.method != "GET":
        return respuesta_error("Método no permitido.", status=405)

    filas = _construir_filas_historial()
    columnas = ["Fecha", "Lote", "Cultivo", "Tipo", "Estado", "Empleado", "Producto", "Dosis", "Costo", "Observaciones"]
    contenido_xlsx = _generar_xlsx_nativo(columnas, filas)

    response = HttpResponse(
        contenido_xlsx,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="historial_labores.xlsx"'
    return response
