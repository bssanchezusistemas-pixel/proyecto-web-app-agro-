"""
Módulo de Consultas Agregadas y Reportes Analíticos (B2)
Sistema de Gestión de Cultivos Agrícolas

Proporciona las consultas de agregación con Django ORM para:
1. Kilos cosechados vs. vendidos por cultivo y por periodo.
2. Costo total de abonos/insumos y labores por cultivo (desglosado por tipo).
3. Balance financiero (Ingresos de ventas vs. Costos de labores).
4. Resumen operativo de ciclos productivos activos y cerrados.
"""

from datetime import date
from typing import Optional, List, Dict, Any
from django.db.models import Sum, Q

from .models import (
    Cultivo,
    CicloProductivo,
    Cosecha,
    Labor,
    Venta,
)


def reporte_cosechado_vs_vendido(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None
) -> List[Dict[str, Any]]:
    """
    Calcula y compara los kilos cosechados contra los kilos vendidos por cada cultivo,
    opcionalmente filtrado por un rango de fechas.
    """
    resultados: List[Dict[str, Any]] = []

    for cultivo in Cultivo.objects.all():
        # Filtro de cosechas
        cosechas_qs = Cosecha.objects.filter(ciclo__cultivo=cultivo)
        if fecha_inicio:
            cosechas_qs = cosechas_qs.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            cosechas_qs = cosechas_qs.filter(fecha__lte=fecha_fin)

        kilos_cosechados = float(cosechas_qs.aggregate(total=Sum("kilos"))["total"] or 0.0)

        # Filtro de ventas
        ventas_qs = Venta.objects.filter(cultivo=cultivo)
        if fecha_inicio:
            ventas_qs = ventas_qs.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            ventas_qs = ventas_qs.filter(fecha__lte=fecha_fin)

        agregados_venta = ventas_qs.aggregate(
            kilos=Sum("kilos_vendidos"),
            ingresos=Sum("total")
        )
        kilos_vendidos = float(agregados_venta["kilos"] or 0.0)
        ingresos_ventas = float(agregados_venta["ingresos"] or 0.0)

        porcentaje_vendido = (
            round((kilos_vendidos / kilos_cosechados) * 100, 2)
            if kilos_cosechados > 0 else 0.0
        )

        resultados.append({
            "cultivo_id": str(cultivo.id),
            "cultivo": cultivo.nombre,
            "variedad": cultivo.variedad,
            "kilos_cosechados": round(kilos_cosechados, 2),
            "kilos_vendidos": round(kilos_vendidos, 2),
            "stock_en_periodo": round(kilos_cosechados - kilos_vendidos, 2),
            "inventario_total_actual": cultivo.inventario_disponible(),
            "porcentaje_comercializado": porcentaje_vendido,
            "ingresos_ventas": round(ingresos_ventas, 2),
        })

    return resultados


def reporte_costos_por_cultivo(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None
) -> List[Dict[str, Any]]:
    """
    Calcula el costo total de abonos/insumos y labores aplicadas por cada cultivo,
    desglosando entre Fertilización, Fumigación y Otras Labores, además del margen neto.
    """
    resultados: List[Dict[str, Any]] = []

    for cultivo in Cultivo.objects.all():
        labores_qs = Labor.objects.filter(ciclo__cultivo=cultivo).exclude(estado="cancelada")
        if fecha_inicio:
            labores_qs = labores_qs.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            labores_qs = labores_qs.filter(fecha__lte=fecha_fin)

        agregados = labores_qs.aggregate(
            costo_fumigacion=Sum("costo", filter=Q(tipo_labor="FUMIGACION")),
            costo_fertilizacion=Sum("costo", filter=Q(tipo_labor="FERTILIZACION")),
            costo_otras=Sum("costo", filter=Q(tipo_labor="OTRA")),
            costo_total=Sum("costo"),
        )

        costo_fum = float(agregados["costo_fumigacion"] or 0.0)
        costo_fert = float(agregados["costo_fertilizacion"] or 0.0)
        costo_otras = float(agregados["costo_otras"] or 0.0)
        costo_total = float(agregados["costo_total"] or 0.0)

        # Ingresos en el mismo periodo para calcular rentabilidad
        ventas_qs = Venta.objects.filter(cultivo=cultivo)
        if fecha_inicio:
            ventas_qs = ventas_qs.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            ventas_qs = ventas_qs.filter(fecha__lte=fecha_fin)

        ingresos = float(ventas_qs.aggregate(total=Sum("total"))["total"] or 0.0)

        resultados.append({
            "cultivo_id": str(cultivo.id),
            "cultivo": cultivo.nombre,
            "variedad": cultivo.variedad,
            "costo_fumigacion": round(costo_fum, 2),
            "costo_fertilizacion": round(costo_fert, 2),
            "costo_otras_labores": round(costo_otras, 2),
            "costo_total_insumos_labores": round(costo_total, 2),
            "ingresos_totales": round(ingresos, 2),
            "utilidad_neta": round(ingresos - costo_total, 2),
        })

    return resultados


def reporte_resumen_ciclos() -> List[Dict[str, Any]]:
    """
    Entrega el estado operativo y financiero de cada Ciclo Productivo.
    """
    resumen: List[Dict[str, Any]] = []
    ciclos = CicloProductivo.objects.select_related("lote", "cultivo", "responsable").all()

    for ciclo in ciclos:
        resumen.append({
            "ciclo_id": str(ciclo.id),
            "lote": ciclo.lote.nombre,
            "cultivo": f"{ciclo.cultivo.nombre} ({ciclo.cultivo.variedad})",
            "responsable": ciclo.responsable.nombre if ciclo.responsable else "Sin asignar",
            "fecha_siembra": ciclo.fecha_siembra,
            "fecha_estimada_cosecha": ciclo.fecha_estimada_cosecha(),
            "dias_transcurridos": ciclo.dias_transcurridos(),
            "dias_restantes": ciclo.dias_restantes(),
            "etapa": ciclo.etapa,
            "estado": ciclo.estado,
            "kilaje_total_cosechado": round(ciclo.kilaje_total(), 2),
            "costo_total_labores": round(ciclo.costo_total_labores(), 2),
        })

    return resumen
