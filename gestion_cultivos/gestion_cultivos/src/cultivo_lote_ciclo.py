"""
Sistema de Gestión de Cultivos Agrícolas
Módulo: cultivo_lote_ciclo.py

Define las entidades centrales del modelo de producción agrícola:
- Cultivo: Catálogo y características del producto (variedad, días a cosecha).
- Lote: Superficie de terreno donde se ejecuta la labor agrícola.
- CicloProductivo: Unión temporal de un Lote con un Cultivo (RN-01).
- Cosecha: Registro de producción recolectada y validación de inocuidad (RN-05, RN-06, RN-07).

Los atributos mapean 1:1 con las columnas del esquema relacional en PostgreSQL / Supabase.
"""

from __future__ import annotations
from datetime import date, timedelta
from typing import Optional, List, Any
import sys
from pathlib import Path

# Garantizar la importación de persona_empleado
try:
    from persona_empleado import Empleado
except ImportError:
    from .persona_empleado import Empleado


class Cultivo:
    """
    Representa una especie o fruta sembrada en la finca.
    Mapeo 1:1 con la tabla 'cultivos' en PostgreSQL / Supabase.
    
    Atributos:
        nombre (str): Nombre común del cultivo (ej: Mango, Aguacate).
        variedad (str): Subtipo genético o variedad comercial (ej: Tommy, Hass).
        dias_a_cosecha (int): Ciclo biológico estimado en días (> 0).
    """

    def __init__(self, nombre: str, variedad: Optional[str], dias_a_cosecha: int) -> None:
        self.nombre = nombre
        self.variedad = variedad or ""
        self.dias_a_cosecha = dias_a_cosecha

    # -------------------------------------------------------------------------
    # Encapsulamiento y Validaciones
    # -------------------------------------------------------------------------
    @property
    def nombre(self) -> str:
        """Obtiene el nombre del cultivo."""
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        """Valida que el nombre no sea nulo ni vacío."""
        if not valor or not valor.strip():
            raise ValueError("El nombre del cultivo no puede estar vacío ni contener solo espacios.")
        self._nombre = valor.strip()

    @property
    def variedad(self) -> str:
        """Obtiene la variedad del cultivo."""
        return self._variedad

    @variedad.setter
    def variedad(self, valor: Optional[str]) -> None:
        """Sanitiza el texto de variedad."""
        self._variedad = valor.strip() if valor else ""

    @property
    def dias_a_cosecha(self) -> int:
        """Obtiene los días a cosecha."""
        return self._dias_a_cosecha

    @dias_a_cosecha.setter
    def dias_a_cosecha(self, valor: int) -> None:
        """Valida que los días a cosecha sean un entero estrictamente positivo (> 0)."""
        if not isinstance(valor, int) or valor <= 0:
            raise ValueError(f"Los días a cosecha deben ser un número entero mayor que 0. Recibido: {valor}")
        self._dias_a_cosecha = valor

    def __str__(self) -> str:
        detalles_variedad = f" ({self._variedad})" if self._variedad else ""
        return f"Cultivo: {self._nombre}{detalles_variedad} - {self._dias_a_cosecha} días hasta cosecha"


class Lote:
    """
    Representa una parcela o unidad territorial física de la propiedad agrícola.
    Mapeo 1:1 con la tabla 'lotes' en PostgreSQL / Supabase.
    
    Atributos:
        nombre (str): Identificador o nombre del lote (ej: Lote Norte, Parcela A).
        area_ha (float): Extensión superficial en hectáreas (> 0).
        ubicacion (str): Descripción o coordenadas del lote.
    """

    def __init__(self, nombre: str, area_ha: float, ubicacion: Optional[str] = None) -> None:
        self.nombre = nombre
        self.area_ha = area_ha
        self.ubicacion = ubicacion or ""
        self._ciclo_activo: Optional[CicloProductivo] = None

    # -------------------------------------------------------------------------
    # Encapsulamiento y Validaciones
    # -------------------------------------------------------------------------
    @property
    def nombre(self) -> str:
        """Obtiene el nombre del lote."""
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        """Valida que el nombre no sea vacío."""
        if not valor or not valor.strip():
            raise ValueError("El nombre del lote no puede estar vacío ni contener solo espacios.")
        self._nombre = valor.strip()

    @property
    def area_ha(self) -> float:
        """Obtiene el área del lote en hectáreas."""
        return self._area_ha

    @area_ha.setter
    def area_ha(self, valor: float) -> None:
        """Valida que el área sea estrictamente positiva (> 0)."""
        if valor is None or float(valor) <= 0:
            raise ValueError(f"El área del lote debe ser un número positivo mayor que 0 ha. Recibido: {valor}")
        self._area_ha = float(valor)

    @property
    def ubicacion(self) -> str:
        """Obtiene la ubicación del lote."""
        return self._ubicacion

    @ubicacion.setter
    def ubicacion(self, valor: Optional[str]) -> None:
        """Sanitiza la ubicación."""
        self._ubicacion = valor.strip() if valor else ""

    # -------------------------------------------------------------------------
    # Regla de Negocio: Estado de Ciclos
    # -------------------------------------------------------------------------
    def tiene_ciclo_activo(self) -> bool:
        """Indica si el lote tiene actualmente una siembra o ciclo en curso."""
        return self._ciclo_activo is not None and self._ciclo_activo.estado == "activo"

    def __str__(self) -> str:
        loc = f" | Ubicación: {self._ubicacion}" if self._ubicacion else ""
        estado_lote = "Ocupado (Ciclo Activo)" if self.tiene_ciclo_activo() else "Disponible"
        return f"Lote: {self._nombre} ({self._area_ha:.2f} ha){loc} [{estado_lote}]"


class CicloProductivo:
    """
    Representa el ciclo agronómico que vincula un Lote con un Cultivo.
    Aplica la regla RN-01: Un lote solo puede tener un ciclo activo a la vez.
    """

    ETAPAS = ["siembra", "crecimiento", "floracion", "fructificacion", "cosecha"]

    def __init__(self, lote: Lote, cultivo: Cultivo, fecha_siembra: date) -> None:
        if lote.tiene_ciclo_activo():
            # RN-01: Exclusividad de ciclo activo por lote
            raise ValueError(f"Violación de RN-01: El lote '{lote.nombre}' ya tiene un ciclo productivo activo.")
        if fecha_siembra > date.today():
            raise ValueError(f"La fecha de siembra ({fecha_siembra}) no puede ser futura.")

        self.lote: Lote = lote
        self.cultivo: Cultivo = cultivo
        self.fecha_siembra: date = fecha_siembra
        self.etapa: str = self.ETAPAS[0]
        self.estado: str = "activo"
        self.cosechas: List[Cosecha] = []
        self.labores: List[Any] = []

        # Registro en el lote
        lote._ciclo_activo = self

    # -------------------------------------------------------------------------
    # Cálculos Biológicos y Temporales
    # -------------------------------------------------------------------------
    def dias_transcurridos(self) -> int:
        """Calcula los días transcurridos desde la fecha de siembra."""
        return (date.today() - self.fecha_siembra).days

    def dias_restantes(self) -> int:
        """Calcula los días estimados restantes para la cosecha."""
        restantes = self.cultivo.dias_a_cosecha - self.dias_transcurridos()
        return max(restantes, 0)

    def fecha_estimada_cosecha(self) -> date:
        """Proyecta la fecha estimada de cosecha con base en los días del cultivo."""
        return self.fecha_siembra + timedelta(days=self.cultivo.dias_a_cosecha)

    # -------------------------------------------------------------------------
    # Gestión del Ciclo
    # -------------------------------------------------------------------------
    def actualizar_etapa(self, nueva_etapa: str) -> None:
        """Actualiza la etapa fenológica del cultivo."""
        if nueva_etapa.lower() not in self.ETAPAS:
            raise ValueError(f"Etapa inválida '{nueva_etapa}'. Etapas válidas: {self.ETAPAS}")
        self.etapa = nueva_etapa.lower()

    def cerrar_ciclo(self) -> None:
        """Finaliza el ciclo y libera el lote para futuros cultivos."""
        self.estado = "cerrado"
        if self.lote._ciclo_activo is self:
            self.lote._ciclo_activo = None

    # -------------------------------------------------------------------------
    # Acumulados y Composición
    # -------------------------------------------------------------------------
    def kilaje_total(self) -> float:
        """Retorna la suma total de kilogramos recolectados en el ciclo."""
        return sum(c.kilos for c in self.cosechas)

    def costo_total_labores(self) -> float:
        """Retorna el costo acumulado de todas las labores de campo aplicadas."""
        return sum(getattr(l, "costo", 0.0) for l in self.labores)

    def registrar_cosecha(self, cosecha: Cosecha) -> None:
        """Agrega una cosecha a la colección interna del ciclo."""
        self.cosechas.append(cosecha)

    def __str__(self) -> str:
        return (
            f"Ciclo {self.cultivo.nombre} en {self.lote.nombre} | Etapa: {self.etapa.capitalize()} | "
            f"Estado: {self.estado.capitalize()} | Día {self.dias_transcurridos()} de {self.cultivo.dias_a_cosecha}"
        )


class Cosecha:
    """
    Registro de pesaje de producto recolectado en un ciclo por un empleado responsable.
    Aplica las reglas de negocio RN-05 (Carencia), RN-06 (Kilos > 0) y RN-07 (Fecha >= Siembra).
    """

    def __init__(self, fecha: date, kilos: float, ciclo: CicloProductivo, empleado: Empleado) -> None:
        # RN-06: Kilos estrictamente positivos
        if kilos <= 0:
            raise ValueError(f"Violación de RN-06: Los kilos cosechados deben ser mayores a 0. Recibido: {kilos}")

        # RN-07: Fecha no anterior a la siembra
        if fecha < ciclo.fecha_siembra:
            raise ValueError(
                f"Violación de RN-07: La fecha de cosecha ({fecha}) no puede ser anterior "
                f"a la fecha de siembra ({ciclo.fecha_siembra})."
            )

        self.fecha: date = fecha
        self.kilos: float = float(kilos)
        self.ciclo: CicloProductivo = ciclo
        self.empleado: Empleado = empleado

        # RN-05: Validación de inocuidad y carencia
        advertencia = self.validar_carencia()
        if advertencia:
            print(f"[ALERTA FITOSANITARIA] {advertencia}")

        # Composición
        ciclo.registrar_cosecha(self)

    def validar_carencia(self) -> Optional[str]:
        """
        RN-05: Revisa si existe una fumigación reciente cuyo periodo de carencia aún no se cumpla.
        """
        fumigaciones = [l for l in self.ciclo.labores if hasattr(l, "periodo_carencia")]
        if not fumigaciones:
            return None

        ultima_fumigacion = max(fumigaciones, key=lambda f: f.fecha)
        fecha_minima = ultima_fumigacion.fecha + timedelta(days=ultima_fumigacion.periodo_carencia)

        if self.fecha < fecha_minima:
            return (
                f"La cosecha del {self.fecha} viola el periodo de carencia de la última fumigación. "
                f"Fecha mínima segura para cosechar: {fecha_minima}."
            )
        return None

    def __str__(self) -> str:
        return (
            f"Cosecha ({self.fecha}): {self.kilos:.2f} kg de {self.ciclo.cultivo.nombre} "
            f"en {self.ciclo.lote.nombre} (Recolector: {self.empleado.nombre})"
        )


# =============================================================================
# Bloque de Demostración y Pruebas Unitarias Integradas
# =============================================================================
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  DEMOSTRACIÓN Y PRUEBAS: MÓDULO CULTIVOS, LOTES Y CICLOS")
    print("=" * 70)

    # 1. Creación correcta de Cultivos y Lotes
    print("\n--- 1. Instanciación correcta de Cultivos y Lotes ---")
    mango = Cultivo(nombre="Mango", variedad="Tommy Atkins", dias_a_cosecha=120)
    aguacate = Cultivo(nombre="Aguacate", variedad="Hass", dias_a_cosecha=180)
    lote_norte = Lote(nombre="Lote Norte 1", area_ha=3.5, ubicacion="Sector A - Ladera Alta")
    print(mango)
    print(aguacate)
    print(lote_norte)
    assert lote_norte.area_ha == 3.5
    assert not lote_norte.tiene_ciclo_activo()
    print("[PASS] Instanciación y propiedades verificadas.")

    # 2. Validaciones de Negocio en Cultivo
    print("\n--- 2. Validación de Cultivo: Nombre vacío ---")
    try:
        Cultivo(nombre="   ", variedad="Test", dias_a_cosecha=90)
        print("[FAIL] Se permitió cultivo con nombre vacío.")
    except ValueError as e:
        print(f"[PASS] Error controlado: {e}")

    print("\n--- 3. Validación de Cultivo: Días a cosecha <= 0 ---")
    try:
        Cultivo(nombre="Fresa", variedad="Albión", dias_a_cosecha=0)
        print("[FAIL] Se permitieron días a cosecha <= 0.")
    except ValueError as e:
        print(f"[PASS] Error controlado: {e}")

    # 3. Validaciones de Negocio en Lote
    print("\n--- 4. Validación de Lote: Nombre vacío ---")
    try:
        Lote(nombre="", area_ha=2.0)
        print("[FAIL] Se permitió lote con nombre vacío.")
    except ValueError as e:
        print(f"[PASS] Error controlado: {e}")

    print("\n--- 5. Validación de Lote: Área <= 0 ---")
    try:
        Lote(nombre="Lote Sur", area_ha=-1.5)
        print("[FAIL] Se permitió área negativa.")
    except ValueError as e:
        print(f"[PASS] Error controlado: {e}")

    # 4. Prueba del Ciclo Productivo y RN-01 (Un solo ciclo activo por lote)
    print("\n--- 6. Inicio de Ciclo Productivo e Integración ---")
    fecha_siembra = date.today() - timedelta(days=60)
    ciclo_1 = CicloProductivo(lote=lote_norte, cultivo=mango, fecha_siembra=fecha_siembra)
    print(ciclo_1)
    print(f"Días transcurridos: {ciclo_1.dias_transcurridos()}")
    print(f"Días restantes para cosecha: {ciclo_1.dias_restantes()}")
    print(f"Fecha estimada de cosecha: {ciclo_1.fecha_estimada_cosecha()}")
    assert lote_norte.tiene_ciclo_activo(), "El lote debería registrar ciclo activo"

    print("\n--- 7. Violación de RN-01: Segundo ciclo en el mismo lote ocupado ---")
    try:
        CicloProductivo(lote=lote_norte, cultivo=aguacate, fecha_siembra=date.today())
        print("[FAIL] Se permitió un segundo ciclo activo en el mismo lote.")
    except ValueError as e:
        print(f"[PASS] RN-01 cumplida y protegida: {e}")

    # 5. Registro de Cosechas y Reglas RN-06 y RN-07
    print("\n--- 8. Registro de Cosechas y Validación de Reglas ---")
    recolector = Empleado("Pedro Morales", "1003001", "3119998877", "Recolector", date(2023, 1, 15))
    cosecha_valida = Cosecha(fecha=date.today(), kilos=450.75, ciclo=ciclo_1, empleado=recolector)
    print(cosecha_valida)
    print(f"Kilaje total acumulado en el ciclo: {ciclo_1.kilaje_total()} kg")
    assert ciclo_1.kilaje_total() == 450.75

    print("\n--- 9. Violación de RN-06: Kilos <= 0 ---")
    try:
        Cosecha(fecha=date.today(), kilos=0, ciclo=ciclo_1, empleado=recolector)
        print("[FAIL] Se permitió cosecha con 0 kilos.")
    except ValueError as e:
        print(f"[PASS] RN-06 controlada: {e}")

    print("\n--- 10. Violación de RN-07: Fecha de cosecha anterior a la siembra ---")
    try:
        fecha_invalida = fecha_siembra - timedelta(days=10)
        Cosecha(fecha=fecha_invalida, kilos=100, ciclo=ciclo_1, empleado=recolector)
        print("[FAIL] Se permitió cosecha antes de la siembra.")
    except ValueError as e:
        print(f"[PASS] RN-07 controlada: {e}")

    # 6. Cierre del ciclo y liberación del lote
    print("\n--- 11. Cierre de Ciclo Productivo ---")
    ciclo_1.cerrar_ciclo()
    print(f"Estado del ciclo: {ciclo_1.estado}")
    print(f"Lote Norte ocupado: {lote_norte.tiene_ciclo_activo()}")
    assert not lote_norte.tiene_ciclo_activo(), "El lote debería estar libre tras cerrar el ciclo."

    # Ahora sí debe permitir iniciar un nuevo ciclo
    ciclo_nuevo = CicloProductivo(lote=lote_norte, cultivo=aguacate, fecha_siembra=date.today())
    print(f"Nuevo ciclo iniciado exitosamente: {ciclo_nuevo}")

    print("\n" + "=" * 70)
    print("  ¡TODAS LAS PRUEBAS DE CULTIVOS, LOTES Y CICLOS PASARON CON ÉXITO!")
    print("=" * 70 + "\n")