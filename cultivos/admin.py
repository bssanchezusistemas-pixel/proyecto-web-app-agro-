"""
Configuración del Panel Administrativo de Django para Gestión Agrícola (B1 y B2).
"""

from django.contrib import admin
from .models import (
    Empleado,
    Cultivo,
    Lote,
    CicloProductivo,
    Fumigacion,
    Fertilizacion,
    OtraLabor,
    Cosecha,
    Cliente,
    Venta,
)


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "documento", "cargo", "fecha_ingreso", "activo")
    list_filter = ("activo", "cargo")
    search_fields = ("nombre", "documento", "cargo")


@admin.register(Cultivo)
class CultivoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "variedad", "dias_a_cosecha", "inventario_disponible")
    search_fields = ("nombre", "variedad")


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "area_ha", "ubicacion", "tiene_ciclo_activo")
    search_fields = ("nombre", "ubicacion")


@admin.register(CicloProductivo)
class CicloProductivoAdmin(admin.ModelAdmin):
    list_display = (
        "cultivo",
        "lote",
        "fecha_siembra",
        "etapa",
        "estado",
        "kilaje_total",
        "costo_total_labores",
    )
    list_filter = ("estado", "etapa", "cultivo")
    search_fields = ("lote__nombre", "cultivo__nombre")


@admin.register(Fumigacion)
class FumigacionAdmin(admin.ModelAdmin):
    list_display = (
        "fecha",
        "ciclo",
        "producto",
        "dosis",
        "plaga_objetivo",
        "periodo_carencia",
        "fecha_minima_cosecha",
        "costo",
        "estado",
    )
    list_filter = ("estado", "fecha")
    search_fields = ("producto", "plaga_objetivo")


@admin.register(Fertilizacion)
class FertilizacionAdmin(admin.ModelAdmin):
    list_display = ("fecha", "ciclo", "tipo_abono", "cantidad", "unidad", "costo", "estado")
    list_filter = ("estado", "fecha")
    search_fields = ("tipo_abono",)


@admin.register(OtraLabor)
class OtraLaborAdmin(admin.ModelAdmin):
    list_display = ("fecha", "ciclo", "tipo", "costo", "estado")
    list_filter = ("estado", "tipo")


@admin.register(Cosecha)
class CosechaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "ciclo", "kilos", "empleado")
    list_filter = ("fecha", "ciclo__cultivo")


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "documento", "telefono", "tipo_cliente", "direccion")
    list_filter = ("tipo_cliente",)
    search_fields = ("nombre", "documento")


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "cliente", "cultivo", "kilos_vendidos", "precio_kilo", "total")
    list_filter = ("fecha", "cultivo")
    search_fields = ("cliente__nombre", "cultivo__nombre")
