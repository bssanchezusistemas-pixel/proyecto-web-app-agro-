"""
Modelos del Dominio en Django ORM (B1 y B2)
Sistema de Gestión de Cultivos Agrícolas

Implementa:
- B1: Persona (abstracta), Empleado, Cultivo, Lote, CicloProductivo (con RN-01).
- B2: Labor (polimórfica), Fumigacion, Fertilizacion, OtraLabor, Cosecha (RN-05, RN-06, RN-07),
      Cliente y Venta (con control de inventario disponible).
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum, Q


# ==============================================================================
# BLOQUE B1: PERSONAS, EMPLEADOS, CULTIVOS, LOTES Y CICLOS PRODUCTIVOS
# ==============================================================================

class Persona(models.Model):
    """
    Clase base abstracta que representa cualquier persona en el sistema.
    En Django ORM: abstract = True impide instanciación/tabla directa y aplica herencia en subclases.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=150, verbose_name="Nombre completo")
    documento = models.CharField(max_length=50, unique=True, verbose_name="Documento de identidad")
    telefono = models.CharField(max_length=20, blank=True, default="", verbose_name="Teléfono")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def clean_fields(self, exclude=None) -> None:
        if self.telefono is None:
            self.telefono = ""
        super().clean_fields(exclude=exclude)

    def clean(self) -> None:
        super().clean()
        if not self.nombre or not self.nombre.strip():
            raise ValidationError({"nombre": "El nombre no puede estar vacío ni contener solo espacios."})
        if not self.documento or not self.documento.strip():
            raise ValidationError({"documento": "El documento no puede estar vacío ni contener solo espacios."})
        self.nombre = self.nombre.strip()
        self.documento = self.documento.strip()
        self.telefono = self.telefono.strip() if self.telefono else ""

    def describir(self) -> str:
        """Método abstracto que cada subclase debe sobrescribir polimórficamente."""
        raise NotImplementedError("Las subclases de Persona deben implementar describir().")

    def __str__(self) -> str:
        return f"{self.nombre} ({self.documento})"


class Empleado(Persona):
    """
    Especialización de Persona para trabajadores de la finca (Agrónomo, Fumigador, Recolector, etc.).
    """
    cargo = models.CharField(max_length=100, verbose_name="Cargo operativo")
    fecha_ingreso = models.DateField(default=date.today, verbose_name="Fecha de ingreso")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "empleados"
        verbose_name = "Empleado"
        verbose_name_plural = "Empleados"
        ordering = ["nombre"]

    def clean(self) -> None:
        super().clean()
        if not self.cargo or not self.cargo.strip():
            raise ValidationError({"cargo": "El cargo no puede estar vacío."})
        self.cargo = self.cargo.strip()

        if self.fecha_ingreso and self.fecha_ingreso > date.today():
            raise ValidationError({
                "fecha_ingreso": f"La fecha de ingreso ({self.fecha_ingreso}) no puede ser futura."
            })

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def esta_activo(self) -> bool:
        """Retorna True si el empleado se encuentra activo."""
        return bool(self.activo)

    def desactivar(self) -> None:
        """Borrado lógico para conservar el historial de labores y cosechas."""
        self.activo = False
        self.save(update_fields=["activo", "updated_at"])

    def activar(self) -> None:
        """Reactiva un empleado previamente inactivo."""
        self.activo = True
        self.save(update_fields=["activo", "updated_at"])

    def describir(self) -> str:
        estado = "activo" if self.activo else "inactivo"
        return (
            f"{self.nombre} (doc. {self.documento}) - {self.cargo} "
            f"- ingreso: {self.fecha_ingreso} - {estado}"
        )


class Cultivo(models.Model):
    """
    Catálogo de frutas o especies sembradas (ej. Mango Tommy, Aguacate Hass, Fresa Albión).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, verbose_name="Nombre del cultivo")
    variedad = models.CharField(max_length=100, blank=True, default="", verbose_name="Variedad")
    dias_a_cosecha = models.PositiveIntegerField(verbose_name="Días estimados a cosecha")
    periodo_carencia_dias = models.PositiveIntegerField(
        default=0,
        verbose_name="Periodo de carencia (días)"
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cultivos"
        verbose_name = "Cultivo"
        verbose_name_plural = "Cultivos"
        ordering = ["nombre"]

    def __init__(self, *args, **kwargs):
        if "dias_ciclo" in kwargs and "dias_a_cosecha" not in kwargs:
            kwargs["dias_a_cosecha"] = kwargs.pop("dias_ciclo")
        super().__init__(*args, **kwargs)

    @property
    def dias_ciclo(self) -> int:
        return self.dias_a_cosecha

    @dias_ciclo.setter
    def dias_ciclo(self, valor: int) -> None:
        self.dias_a_cosecha = valor

    def clean_fields(self, exclude=None) -> None:
        if self.variedad is None:
            self.variedad = ""
        super().clean_fields(exclude=exclude)

    def clean(self) -> None:
        super().clean()
        if not self.nombre or not self.nombre.strip():
            raise ValidationError({"nombre": "El nombre del cultivo no puede estar vacío."})
        if self.dias_a_cosecha is None or self.dias_a_cosecha <= 0:
            raise ValidationError({"dias_a_cosecha": "Los días a cosecha deben ser mayores que 0."})
        self.nombre = self.nombre.strip()
        self.variedad = self.variedad.strip() if self.variedad else ""

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    # ---------- Consultas de Inventario y Acumulados por Cultivo ----------
    def total_kilos_cosechados(self) -> float:
        total = Cosecha.objects.filter(ciclo__cultivo=self).aggregate(total=Sum("kilos"))["total"]
        return float(total or 0.0)

    def total_kilos_vendidos(self, excluir_venta_id: Optional[uuid.UUID] = None) -> float:
        qs = self.ventas.all()
        if excluir_venta_id:
            qs = qs.exclude(pk=excluir_venta_id)
        total = qs.aggregate(total=Sum("kilos_vendidos"))["total"]
        return float(total or 0.0)

    def inventario_disponible(self, excluir_venta_id: Optional[uuid.UUID] = None) -> float:
        """Calcula los kilos disponibles en bodega (Cosechado - Vendido)."""
        return round(self.total_kilos_cosechados() - self.total_kilos_vendidos(excluir_venta_id), 2)

    def __str__(self) -> str:
        var = f" ({self.variedad})" if self.variedad else ""
        return f"{self.nombre}{var} - {self.dias_a_cosecha} días a cosecha"


class Lote(models.Model):
    """
    Porción de terreno físico donde se establecen los ciclos productivos.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del lote")
    area_ha = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Área (Hectáreas)")
    ubicacion = models.CharField(max_length=200, blank=True, default="", verbose_name="Ubicación")
    cultivo = models.ForeignKey(
        Cultivo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lotes",
        verbose_name="Cultivo asignado"
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lotes"
        verbose_name = "Lote"
        verbose_name_plural = "Lotes"
        ordering = ["nombre"]

    def __init__(self, *args, **kwargs):
        if "area_hectareas" in kwargs and "area_ha" not in kwargs:
            kwargs["area_ha"] = kwargs.pop("area_hectareas")
        super().__init__(*args, **kwargs)

    @property
    def area_hectareas(self) -> Decimal:
        return self.area_ha

    @area_hectareas.setter
    def area_hectareas(self, valor: Decimal) -> None:
        self.area_ha = valor

    def clean_fields(self, exclude=None) -> None:
        if self.ubicacion is None:
            self.ubicacion = ""
        super().clean_fields(exclude=exclude)

    def clean(self) -> None:
        super().clean()
        if not self.nombre or not self.nombre.strip():
            raise ValidationError({"nombre": "El nombre del lote no puede estar vacío."})
        if self.area_ha is None or float(self.area_ha) <= 0:
            raise ValidationError({"area_ha": "El área en hectáreas debe ser mayor que 0."})
        self.nombre = self.nombre.strip()
        self.ubicacion = self.ubicacion.strip() if self.ubicacion else ""

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def tiene_ciclo_activo(self) -> bool:
        """Retorna True si el lote tiene un CicloProductivo con estado 'activo'."""
        return self.ciclos.filter(estado="activo").exists()

    def obtener_ciclo_activo(self) -> Optional["CicloProductivo"]:
        return self.ciclos.filter(estado="activo").first()

    def __str__(self) -> str:
        return f"Lote {self.nombre} ({self.area_ha} ha) - {self.ubicacion}"


class CicloProductivo(models.Model):
    """
    Une un Cultivo con un Lote a partir de una fecha de siembra.
    Regla de Negocio RN-01: Un lote solo puede tener un ciclo activo a la vez.
    """
    ETAPAS = ["siembra", "crecimiento", "floracion", "fructificacion", "cosecha"]
    ETAPA_CHOICES = [(e, e.capitalize()) for e in ETAPAS]

    ESTADO_CHOICES = [
        ("activo", "Activo"),
        ("cerrado", "Cerrado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name="ciclos", verbose_name="Lote")
    cultivo = models.ForeignKey(Cultivo, on_delete=models.CASCADE, related_name="ciclos", verbose_name="Cultivo")
    responsable = models.ForeignKey(
        Empleado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ciclos_responsable",
        verbose_name="Empleado responsable"
    )
    fecha_siembra = models.DateField(verbose_name="Fecha de siembra")
    fecha_cierre = models.DateField(null=True, blank=True, verbose_name="Fecha de cierre")
    etapa = models.CharField(max_length=30, choices=ETAPA_CHOICES, default="siembra", verbose_name="Etapa fenológica")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="activo", verbose_name="Estado")
    observaciones = models.TextField(blank=True, default="", verbose_name="Observaciones")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ciclos_productivos"
        verbose_name = "Ciclo Productivo"
        verbose_name_plural = "Ciclos Productivos"
        ordering = ["-fecha_siembra"]
        constraints = [
            models.UniqueConstraint(
                fields=["lote"],
                condition=Q(estado="activo"),
                name="rn01_un_solo_ciclo_activo_por_lote"
            )
        ]

    @property
    def fecha_inicio(self) -> date:
        return self.fecha_siembra

    @fecha_inicio.setter
    def fecha_inicio(self, valor: date) -> None:
        self.fecha_siembra = valor

    @property
    def fecha_fin_estimada(self) -> date:
        return self.fecha_estimada_cosecha()

    def clean_fields(self, exclude=None) -> None:
        if self.observaciones is None:
            self.observaciones = ""
        super().clean_fields(exclude=exclude)

    def clean(self) -> None:
        super().clean()
        if self.fecha_siembra and self.fecha_siembra > date.today():
            raise ValidationError({"fecha_siembra": "La fecha de siembra no puede ser futura."})

        if self.etapa not in self.ETAPAS:
            raise ValidationError({"etapa": f"Etapa inválida. Debe ser una de: {self.ETAPAS}"})

        # RN-01: Validar que el lote no tenga ya otro ciclo activo
        if self.estado == "activo" and self.lote_id:
            conflicto = (
                CicloProductivo.objects.filter(lote_id=self.lote_id, estado="activo")
                .exclude(pk=self.pk)
                .exists()
            )
            if conflicto:
                raise ValidationError({
                    "lote": f"RN-01: El lote '{self.lote.nombre}' ya tiene un ciclo productivo activo."
                })

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    # ---------- Métodos de Dominio (Diagrama UML) ----------
    @classmethod
    def iniciar(
        cls,
        lote: Lote,
        cultivo: Cultivo,
        fecha: date,
        responsable: Optional[Empleado] = None,
        observaciones: str = ""
    ) -> "CicloProductivo":
        """Método de fábrica según el diagrama UML: + iniciar(lote, cultivo, fecha)."""
        ciclo = cls(
            lote=lote,
            cultivo=cultivo,
            fecha_siembra=fecha,
            responsable=responsable,
            observaciones=observaciones or "",
        )
        ciclo.save()
        return ciclo

    def dias_transcurridos(self) -> int:
        return (date.today() - self.fecha_siembra).days

    def dias_restantes(self) -> int:
        restantes = self.cultivo.dias_a_cosecha - self.dias_transcurridos()
        return max(restantes, 0)

    def fecha_estimada_cosecha(self) -> date:
        return self.fecha_siembra + timedelta(days=self.cultivo.dias_a_cosecha)

    def actualizar_etapa(self, nueva_etapa: str) -> None:
        if nueva_etapa not in self.ETAPAS:
            raise ValidationError(f"Etapa inválida. Debe ser una de: {self.ETAPAS}")
        self.etapa = nueva_etapa
        self.save(update_fields=["etapa"])

    def cerrar_ciclo(self) -> None:
        self.estado = "cerrado"
        self.fecha_cierre = date.today()
        self.save(update_fields=["estado", "fecha_cierre"])

    def kilaje_total(self) -> float:
        total = self.cosechas.aggregate(total=Sum("kilos"))["total"]
        return float(total or 0.0)

    def costo_total_labores(self) -> float:
        total = self.labores.exclude(estado="cancelada").aggregate(total=Sum("costo"))["total"]
        return float(total or 0.0)

    def __str__(self) -> str:
        return (
            f"Ciclo {self.cultivo.nombre} en {self.lote.nombre} - "
            f"etapa: {self.etapa} - estado: {self.estado}"
        )


# ==============================================================================
# BLOQUE B2: LABORES DE CAMPO (POLIMORFISMO), COSECHAS, CLIENTES Y VENTAS
# ==============================================================================

class Labor(models.Model):
    """
    Clase base polimórfica para las labores de campo.
    Utiliza Herencia Multi-Tabla de Django para permitir polimorfismo real en describir()
    y calcular_costo(), manteniendo una relación unificada con CicloProductivo.
    """
    ESTADO_CHOICES = [
        ("programada", "Programada"),
        ("realizada", "Realizada"),
        ("ejecutada", "Ejecutada"),
        ("cancelada", "Cancelada"),
    ]
    TIPO_CHOICES = [
        ("FUMIGACION", "Fumigación"),
        ("FERTILIZACION", "Fertilización"),
        ("OTRA", "Otra Labor"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ciclo = models.ForeignKey(
        CicloProductivo,
        on_delete=models.CASCADE,
        related_name="labores",
        verbose_name="Ciclo productivo"
    )
    responsable = models.ForeignKey(
        Empleado,
        on_delete=models.PROTECT,
        related_name="labores_realizadas",
        verbose_name="Empleado responsable"
    )
    fecha = models.DateField(verbose_name="Fecha de la labor")
    fecha_programada = models.DateField(null=True, blank=True, verbose_name="Fecha programada")
    fecha_ejecucion = models.DateField(null=True, blank=True, verbose_name="Fecha de ejecución")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="realizada")
    costo = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Costo ($)")
    producto_insumo = models.CharField(max_length=120, blank=True, default="", verbose_name="Producto / Insumo")
    dosis_cantidad = models.CharField(max_length=100, blank=True, default="", verbose_name="Dosis / Cantidad")
    observaciones = models.TextField(blank=True, default="", verbose_name="Observaciones")
    tipo_labor = models.CharField(max_length=20, choices=TIPO_CHOICES, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "labores"
        verbose_name = "Labor de Campo"
        verbose_name_plural = "Labores de Campo"
        ordering = ["-fecha", "-created_at"]

    def clean_fields(self, exclude=None) -> None:
        if self.observaciones is None:
            self.observaciones = ""
        if self.producto_insumo is None:
            self.producto_insumo = ""
        if self.dosis_cantidad is None:
            self.dosis_cantidad = ""
        if not self.fecha and self.fecha_programada:
            self.fecha = self.fecha_programada
        if not self.fecha_programada and self.fecha:
            self.fecha_programada = self.fecha
        super().clean_fields(exclude=exclude)

    def clean(self) -> None:
        super().clean()
        if self.costo is None or float(self.costo) < 0:
            raise ValidationError({"costo": "El costo de la labor no puede ser negativo."})

    def marcar_realizada(self, fecha_ejec: Optional[date] = None) -> None:
        self.estado = "ejecutada"
        self.fecha_ejecucion = fecha_ejec or date.today()
        self.fecha = self.fecha_ejecucion
        self.save(update_fields=["estado", "fecha_ejecucion", "fecha"])

    def esta_vencida(self) -> bool:
        fecha_ref = self.fecha_programada or self.fecha
        return self.estado == "programada" and fecha_ref < date.today()

    def obtener_instancia_especifica(self) -> "Labor":
        """Resuelve polimórficamente la subclase hija correspondiente."""
        if hasattr(self, "fumigacion"):
            return self.fumigacion
        if hasattr(self, "fertilizacion"):
            return self.fertilizacion
        if hasattr(self, "otralabor"):
            return self.otralabor
        return self

    def describir(self) -> str:
        """Despacho polimórfico hacia la subclase correspondiente."""
        especifica = self.obtener_instancia_especifica()
        if especifica is not self:
            return especifica.describir()
        raise NotImplementedError("Labor es abstracta conceptualmente; utilice Fumigacion, Fertilizacion u OtraLabor.")

    def calcular_costo(self) -> float:
        """Despacho polimórfico hacia la subclase correspondiente."""
        especifica = self.obtener_instancia_especifica()
        if especifica is not self:
            return especifica.calcular_costo()
        return float(self.costo)

    def __str__(self) -> str:
        try:
            return self.describir()
        except NotImplementedError:
            return f"Labor ({self.fecha}) - ${self.costo}"


class Fumigacion(Labor):
    """
    Subclase de Labor para control fitosanitario.
    Define el periodo_carencia en días para la regla RN-05.
    """
    producto = models.CharField(max_length=120, verbose_name="Producto agroquímico")
    dosis = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Dosis aplicada")
    plaga_objetivo = models.CharField(max_length=120, verbose_name="Plaga objetivo")
    periodo_carencia = models.PositiveIntegerField(
        verbose_name="Periodo de carencia (días)",
        help_text="Días mínimos de espera entre la fumigación y la cosecha (RN-05)"
    )

    class Meta:
        db_table = "labores_fumigacion"
        verbose_name = "Fumigación"
        verbose_name_plural = "Fumigaciones"

    def clean(self) -> None:
        self.tipo_labor = "FUMIGACION"
        super().clean()
        if not self.producto or not self.producto.strip():
            raise ValidationError({"producto": "El producto de fumigación es obligatorio."})
        if self.dosis is None or float(self.dosis) <= 0:
            raise ValidationError({"dosis": "La dosis debe ser mayor que 0."})
        if self.periodo_carencia is None or self.periodo_carencia < 0:
            raise ValidationError({"periodo_carencia": "El periodo de carencia no puede ser negativo."})

    def save(self, *args, **kwargs) -> None:
        self.tipo_labor = "FUMIGACION"
        self.full_clean()
        super().save(*args, **kwargs)

    def dias_carencia_efectivos(self) -> int:
        if self.periodo_carencia and self.periodo_carencia > 0:
            return int(self.periodo_carencia)
        if self.ciclo_id and self.ciclo.cultivo_id:
            return int(self.ciclo.cultivo.periodo_carencia_dias or 0)
        return 0

    def fecha_minima_cosecha(self) -> date:
        """Retorna la fecha a partir de la cual se cumple el periodo de carencia."""
        fecha_base = self.fecha_ejecucion or self.fecha
        return fecha_base + timedelta(days=self.dias_carencia_efectivos())

    def calcular_costo(self) -> float:
        return float(self.costo)

    def describir(self) -> str:
        return (
            f"Fumigación ({self.fecha}) - Producto: {self.producto} ({self.dosis} L) - "
            f"Plaga: {self.plaga_objetivo} - Carencia: {self.periodo_carencia} días "
            f"(cosechar desde {self.fecha_minima_cosecha()}) - Costo: ${self.calcular_costo():,.2f}"
        )


class Fertilizacion(Labor):
    """
    Subclase de Labor para aplicación de abonos e insumos nutricionales.
    """
    tipo_abono = models.CharField(max_length=120, verbose_name="Tipo de abono / insumo")
    cantidad = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Cantidad aplicada")
    unidad = models.CharField(max_length=20, default="kg", verbose_name="Unidad de medida")

    class Meta:
        db_table = "labores_fertilizacion"
        verbose_name = "Fertilización"
        verbose_name_plural = "Fertilizaciones"

    def clean(self) -> None:
        self.tipo_labor = "FERTILIZACION"
        super().clean()
        if not self.tipo_abono or not self.tipo_abono.strip():
            raise ValidationError({"tipo_abono": "El tipo de abono no puede estar vacío."})
        if self.cantidad is None or float(self.cantidad) <= 0:
            raise ValidationError({"cantidad": "La cantidad aplicada debe ser mayor que 0."})

    def save(self, *args, **kwargs) -> None:
        self.tipo_labor = "FERTILIZACION"
        self.full_clean()
        super().save(*args, **kwargs)

    def calcular_costo(self) -> float:
        return float(self.costo)

    def describir(self) -> str:
        return (
            f"Fertilización ({self.fecha}) - Abono: {self.tipo_abono} "
            f"({self.cantidad} {self.unidad}) - Costo: ${self.calcular_costo():,.2f}"
        )


class OtraLabor(Labor):
    """
    Subclase de Labor para actividades culturales (poda, riego, desyerbe, plateo).
    """
    tipo = models.CharField(max_length=100, verbose_name="Tipo de labor")
    descripcion = models.TextField(verbose_name="Descripción detallada")

    class Meta:
        db_table = "labores_otra"
        verbose_name = "Otra Labor"
        verbose_name_plural = "Otras Labores"

    def clean(self) -> None:
        self.tipo_labor = "OTRA"
        super().clean()
        if not self.tipo or not self.tipo.strip():
            raise ValidationError({"tipo": "El tipo de labor no puede estar vacío."})

    def save(self, *args, **kwargs) -> None:
        self.tipo_labor = "OTRA"
        self.full_clean()
        super().save(*args, **kwargs)

    def calcular_costo(self) -> float:
        return float(self.costo)

    def describir(self) -> str:
        return (
            f"Labor {self.tipo} ({self.fecha}) - {self.descripcion} - "
            f"Costo: ${self.calcular_costo():,.2f}"
        )


class Cosecha(models.Model):
    """
    Registro de recolección de fruta en un ciclo productivo.
    Aplica las reglas de negocio:
    - RN-05: validar_carencia() revisa la última fumigación antes de guardar.
    - RN-06: kilos > 0.
    - RN-07: fecha >= fecha_siembra del ciclo.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ciclo = models.ForeignKey(
        CicloProductivo,
        on_delete=models.CASCADE,
        related_name="cosechas",
        verbose_name="Ciclo productivo"
    )
    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.PROTECT,
        related_name="cosechas_recolectadas",
        verbose_name="Empleado responsable"
    )
    fecha = models.DateField(verbose_name="Fecha de cosecha")
    kilos = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Kilogramos cosechados")
    calidad = models.CharField(max_length=50, blank=True, default="", verbose_name="Calidad")
    observaciones = models.TextField(blank=True, default="", verbose_name="Observaciones")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cosechas"
        verbose_name = "Cosecha"
        verbose_name_plural = "Cosechas"
        ordering = ["-fecha"]

    def clean_fields(self, exclude=None) -> None:
        if self.calidad is None:
            self.calidad = ""
        if self.observaciones is None:
            self.observaciones = ""
        super().clean_fields(exclude=exclude)

    def validar_carencia(self) -> bool:
        """
        RN-05: Revisa la última fumigación realizada en el ciclo antes o en la fecha de cosecha.
        Retorna True si es seguro cosechar (carencia cumplida) o False si viola el periodo de carencia.
        """
        if not self.ciclo_id or not self.fecha:
            return True

        ultima_fumigacion = (
            Fumigacion.objects.filter(ciclo_id=self.ciclo_id, fecha__lte=self.fecha)
            .exclude(estado__in=["cancelada", "programada"])
            .order_by("-fecha")
            .first()
        )
        if not ultima_fumigacion:
            return True

        return self.fecha >= ultima_fumigacion.fecha_minima_cosecha()

    def obtener_detalle_carencia(self) -> Optional[str]:
        """Retorna el mensaje explicativo si existe violación de carencia, o None si es válida."""
        if not self.ciclo_id or not self.fecha:
            return None

        ultima_fumigacion = (
            Fumigacion.objects.filter(ciclo_id=self.ciclo_id, fecha__lte=self.fecha)
            .exclude(estado__in=["cancelada", "programada"])
            .order_by("-fecha")
            .first()
        )
        if ultima_fumigacion and self.fecha < ultima_fumigacion.fecha_minima_cosecha():
            return (
                f"RN-05: No se puede cosechar el {self.fecha}. El lote tiene una fumigación con "
                f"'{ultima_fumigacion.producto}' del {ultima_fumigacion.fecha} con carencia de "
                f"{ultima_fumigacion.dias_carencia_efectivos()} días. Fecha mínima permitida: "
                f"{ultima_fumigacion.fecha_minima_cosecha()}."
            )
        return None

    def clean(self) -> None:
        super().clean()
        # RN-06: Kilos > 0
        if self.kilos is None or float(self.kilos) <= 0:
            raise ValidationError({"kilos": "RN-06: Los kilos cosechados deben ser mayores que 0."})

        if self.ciclo_id and self.fecha:
            # RN-07: Fecha >= fecha_siembra
            if self.fecha < self.ciclo.fecha_siembra:
                raise ValidationError({
                    "fecha": f"RN-07: La fecha de cosecha ({self.fecha}) no puede ser anterior "
                             f"a la fecha de siembra ({self.ciclo.fecha_siembra})."
                })

            # RN-05: Validar periodo de carencia de fumigación
            if not self.validar_carencia():
                mensaje_error = self.obtener_detalle_carencia()
                raise ValidationError({"fecha": mensaje_error})

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f"Cosecha {self.fecha} - {self.kilos} kg - "
            f"{self.ciclo.cultivo.nombre} ({self.ciclo.lote.nombre})"
        )


class Cliente(Persona):
    """
    Especialización de Persona para los clientes o comercializadores que compran la cosecha.
    """
    direccion = models.CharField(max_length=200, blank=True, default="", verbose_name="Dirección comercial")
    tipo_cliente = models.CharField(
        max_length=50,
        default="Mayorista",
        verbose_name="Tipo de cliente (Mayorista, Minorista, Exportador)"
    )

    class Meta:
        db_table = "clientes"
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nombre"]

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def describir(self) -> str:
        return f"Cliente: {self.nombre} (doc/NIT: {self.documento}) - {self.tipo_cliente}"


class Venta(models.Model):
    """
    Registro de venta de fruta cosechada a un cliente.
    Valida automáticamente que los kilos vendidos no superen el inventario disponible.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="ventas", verbose_name="Cliente")
    cultivo = models.ForeignKey(Cultivo, on_delete=models.PROTECT, related_name="ventas", verbose_name="Producto / Cultivo")
    fecha = models.DateField(default=date.today, verbose_name="Fecha de venta")
    kilos_vendidos = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Kilos vendidos")
    precio_kilo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio por kilo ($)")
    total = models.DecimalField(max_digits=14, decimal_places=2, editable=False, verbose_name="Total venta ($)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ventas"
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ["-fecha", "-created_at"]

    def clean(self) -> None:
        super().clean()
        if self.kilos_vendidos is None or float(self.kilos_vendidos) <= 0:
            raise ValidationError({"kilos_vendidos": "Los kilos vendidos deben ser mayores que 0."})
        if self.precio_kilo is None or float(self.precio_kilo) <= 0:
            raise ValidationError({"precio_kilo": "El precio por kilo debe ser mayor que 0."})

        # Control de inventario disponible (no vender más de lo cosechado disponible)
        if self.cultivo_id and self.kilos_vendidos:
            disponible = self.cultivo.inventario_disponible(excluir_venta_id=self.pk)
            if float(self.kilos_vendidos) > disponible:
                raise ValidationError({
                    "kilos_vendidos": (
                        f"Inventario insuficiente para {self.cultivo.nombre}. "
                        f"Disponible en bodega: {disponible} kg, solicitado: {self.kilos_vendidos} kg."
                    )
                })

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        self.total = Decimal(str(self.kilos_vendidos)) * Decimal(str(self.precio_kilo))
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f"Venta {self.fecha} - {self.cliente.nombre} - "
            f"{self.kilos_vendidos} kg de {self.cultivo.nombre} (${self.total:,.2f})"
        )
