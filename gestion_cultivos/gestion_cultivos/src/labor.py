"""
Sistema de Gestión de Cultivos Agrícolas
Módulo: labor.py (B2)

Define las clases polimórficas para las labores de campo:
- Labor (ABC): Clase base abstracta con métodos describir() y calcular_costo().
- Fumigacion: Control fitosanitario con cálculo de periodo de carencia (RN-05).
- Fertilizacion: Aplicación de abonos y nutrientes.
- OtraLabor: Poda, riego, desyerbe u otras labores generales.
- Cliente (hereda de Persona) y Venta: Comercialización y control de inventario.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Optional

try:
    from persona_empleado import Persona, Empleado
    from cultivo_lote_ciclo import CicloProductivo, Cultivo
except ImportError:
    from .persona_empleado import Persona, Empleado
    from .cultivo_lote_ciclo import CicloProductivo, Cultivo


class Labor(ABC):
    """
    Clase base abstracta que representa cualquier actividad operativa en el campo.
    Aplica polimorfismo en describir() y calcular_costo().
    """

    ESTADOS_VALIDOS = ["programada", "realizada", "cancelada"]

    def __init__(
        self,
        fecha: date,
        costo: float,
        empleado: Empleado,
        ciclo: Optional[CicloProductivo] = None,
        estado: str = "realizada",
        observaciones: Optional[str] = None
    ) -> None:
        self.fecha = fecha
        self.costo = costo
        self.empleado = empleado
        self.estado = estado
        self.observaciones = (observaciones or "").strip()
        self.ciclo = ciclo

        if ciclo is not None:
            ciclo.labores.append(self)

    @property
    def costo(self) -> float:
        return self._costo

    @costo.setter
    def costo(self, valor: float) -> None:
        if valor is None or float(valor) < 0:
            raise ValueError("El costo de la labor no puede ser negativo.")
        self._costo = float(valor)

    @property
    def estado(self) -> str:
        return self._estado

    @estado.setter
    def estado(self, valor: str) -> None:
        val_limpio = valor.strip().lower() if valor else ""
        if val_limpio not in self.ESTADOS_VALIDOS:
            raise ValueError(f"Estado inválido '{valor}'. Valores permitidos: {self.ESTADOS_VALIDOS}")
        self._estado = val_limpio

    def marcar_realizada(self) -> None:
        """Marca la labor como ejecutada."""
        self._estado = "realizada"

    def esta_vencida(self) -> bool:
        """Retorna True si la labor sigue programada y su fecha ya pasó."""
        return self._estado == "programada" and self.fecha < date.today()

    @abstractmethod
    def describir(self) -> str:
        """Descripción polimórfica de la labor."""
        pass

    @abstractmethod
    def calcular_costo(self) -> float:
        """Cálculo polimórfico del costo total de la labor."""
        pass


class Fumigacion(Labor):
    """
    Subclase de Labor para control de plagas y enfermedades.
    Incluye periodo_carencia en días para garantizar la inocuidad de la cosecha (RN-05).
    """

    def __init__(
        self,
        fecha: date,
        costo: float,
        empleado: Empleado,
        producto: str,
        dosis: float,
        plaga_objetivo: str,
        periodo_carencia: int,
        ciclo: Optional[CicloProductivo] = None,
        estado: str = "realizada",
        observaciones: Optional[str] = None
    ) -> None:
        if not producto or not producto.strip():
            raise ValueError("El producto de fumigación no puede estar vacío.")
        if dosis <= 0:
            raise ValueError("La dosis aplicada debe ser mayor que 0.")
        if periodo_carencia < 0:
            raise ValueError("El periodo de carencia no puede ser negativo.")

        self.producto = producto.strip()
        self.dosis = float(dosis)
        self.plaga_objetivo = (plaga_objetivo or "").strip()
        self.periodo_carencia = int(periodo_carencia)

        super().__init__(
            fecha=fecha,
            costo=costo,
            empleado=empleado,
            ciclo=ciclo,
            estado=estado,
            observaciones=observaciones
        )

    def fecha_minima_cosecha(self) -> date:
        """Calcula la fecha a partir de la cual es seguro cosechar tras esta fumigación."""
        return self.fecha + timedelta(days=self.periodo_carencia)

    def calcular_costo(self) -> float:
        return self.costo

    def describir(self) -> str:
        return (
            f"[Fumigación] {self.fecha} | Producto: {self.producto} ({self.dosis} L/ha) | "
            f"Plaga: {self.plaga_objetivo} | Carencia: {self.periodo_carencia} días "
            f"(Cosechar desde: {self.fecha_minima_cosecha()}) | Costo: ${self.calcular_costo():,.2f}"
        )


class Fertilizacion(Labor):
    """Subclase de Labor para nutrición y abonado del cultivo."""

    def __init__(
        self,
        fecha: date,
        costo: float,
        empleado: Empleado,
        tipo_abono: str,
        cantidad: float,
        unidad: str = "kg",
        ciclo: Optional[CicloProductivo] = None,
        estado: str = "realizada",
        observaciones: Optional[str] = None
    ) -> None:
        if not tipo_abono or not tipo_abono.strip():
            raise ValueError("El tipo de abono no puede estar vacío.")
        if cantidad <= 0:
            raise ValueError("La cantidad de abono debe ser mayor que 0.")

        self.tipo_abono = tipo_abono.strip()
        self.cantidad = float(cantidad)
        self.unidad = (unidad or "kg").strip()

        super().__init__(
            fecha=fecha,
            costo=costo,
            empleado=empleado,
            ciclo=ciclo,
            estado=estado,
            observaciones=observaciones
        )

    def calcular_costo(self) -> float:
        return self.costo

    def describir(self) -> str:
        return (
            f"[Fertilización] {self.fecha} | Abono: {self.tipo_abono} "
            f"({self.cantidad} {self.unidad}) | Costo: ${self.calcular_costo():,.2f}"
        )


class OtraLabor(Labor):
    """Subclase de Labor para actividades generales (poda, desyerbe, riego, mantenimiento)."""

    def __init__(
        self,
        fecha: date,
        costo: float,
        empleado: Empleado,
        tipo: str,
        descripcion: str,
        ciclo: Optional[CicloProductivo] = None,
        estado: str = "realizada",
        observaciones: Optional[str] = None
    ) -> None:
        if not tipo or not tipo.strip():
            raise ValueError("El tipo de labor no puede estar vacío.")

        self.tipo = tipo.strip()
        self.descripcion = (descripcion or "").strip()

        super().__init__(
            fecha=fecha,
            costo=costo,
            empleado=empleado,
            ciclo=ciclo,
            estado=estado,
            observaciones=observaciones
        )

    def calcular_costo(self) -> float:
        return self.costo

    def describir(self) -> str:
        return (
            f"[Otra Labor: {self.tipo}] {self.fecha} | {self.descripcion} | "
            f"Costo: ${self.calcular_costo():,.2f}"
        )


class Cliente(Persona):
    """Especialización de Persona para compradores de fruta cosechada."""

    def __init__(
        self,
        nombre: str,
        documento: str,
        telefono: Optional[str] = None,
        direccion: Optional[str] = None,
        tipo_cliente: str = "Mayorista"
    ) -> None:
        super().__init__(nombre=nombre, documento=documento, telefono=telefono)
        self.direccion = (direccion or "").strip()
        self.tipo_cliente = (tipo_cliente or "Mayorista").strip()

    def describir(self) -> str:
        return (
            f"Cliente: {self.nombre} (Doc/NIT: {self.documento}) | "
            f"Tipo: {self.tipo_cliente} | Tel: {self.telefono}"
        )


class Venta:
    """
    Registro de comercialización de fruta cosechada.
    Valida que no se vendan más kilos de los disponibles en inventario.
    """

    def __init__(
        self,
        cliente: Cliente,
        cultivo: Cultivo,
        kilos_vendidos: float,
        precio_por_kilo: float,
        fecha: date,
        kilos_disponibles: Optional[float] = None
    ) -> None:
        if kilos_vendidos <= 0:
            raise ValueError("Los kilos vendidos deben ser mayores que 0.")
        if precio_por_kilo <= 0:
            raise ValueError("El precio por kilo debe ser mayor que 0.")
        if kilos_disponibles is not None and kilos_vendidos > kilos_disponibles:
            raise ValueError(
                f"Stock insuficiente para {cultivo.nombre}: intentando vender {kilos_vendidos} kg, "
                f"pero solo hay {kilos_disponibles} kg disponibles."
            )

        self.cliente = cliente
        self.cultivo = cultivo
        self.kilos_vendidos = float(kilos_vendidos)
        self.precio_por_kilo = float(precio_por_kilo)
        self.fecha = fecha

    def total_venta(self) -> float:
        return self.kilos_vendidos * self.precio_por_kilo

    def __str__(self) -> str:
        return (
            f"Venta ({self.fecha}) - Cliente: {self.cliente.nombre} | "
            f"Producto: {self.cultivo.nombre} | {self.kilos_vendidos} kg x ${self.precio_por_kilo:,.2f} "
            f"= Total: ${self.total_venta():,.2f}"
        )
