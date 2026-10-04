"""
Sistema de Gestión de Cultivos Agrícolas
Módulo: persona_empleado.py

Define el modelo de dominio para personas y empleados de la finca.
Aplica principios de Programación Orientada a Objetos:
- Abstracción: Persona como clase base abstracta (ABC).
- Encapsulamiento: Atributos privados con decoradores @property y setters con validación estricta.
- Herencia: Empleado especializa a Persona reutilizando atributos base.
- Polimorfismo: Sobrescritura del método abstracto describir().
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional


class Persona(ABC):
    """
    Clase base abstracta que representa a cualquier individuo en el sistema.
    No puede ser instanciada directamente (genera TypeError).
    
    Atributos privados:
        _nombre (str): Nombre completo del individuo.
        _documento (str): Documento oficial de identidad (único).
        _telefono (str): Número telefónico o WhatsApp de contacto.
    """

    def __init__(self, nombre: str, documento: str, telefono: Optional[str] = None) -> None:
        self.nombre = nombre          # Pasa por validación del setter
        self.documento = documento    # Pasa por validación del setter
        self.telefono = telefono or ""

    # -------------------------------------------------------------------------
    # Encapsulamiento con Properties y Validaciones
    # -------------------------------------------------------------------------
    @property
    def nombre(self) -> str:
        """Obtiene el nombre completo."""
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        """Valida que el nombre no sea nulo ni consista únicamente de espacios."""
        if not valor or not valor.strip():
            raise ValueError("El nombre no puede estar vacío ni contener solo espacios.")
        self._nombre = valor.strip()

    @property
    def documento(self) -> str:
        """Obtiene el documento de identidad."""
        return self._documento

    @documento.setter
    def documento(self, valor: str) -> None:
        """Valida que el documento no esté vacío."""
        if not valor or not valor.strip():
            raise ValueError("El documento no puede estar vacío ni contener solo espacios.")
        self._documento = valor.strip()

    @property
    def telefono(self) -> str:
        """Obtiene el teléfono de contacto."""
        return self._telefono

    @telefono.setter
    def telefono(self, valor: Optional[str]) -> None:
        """Sanitiza el teléfono eliminando espacios sobrantes."""
        self._telefono = valor.strip() if valor else ""

    # -------------------------------------------------------------------------
    # Método Abstracto
    # -------------------------------------------------------------------------
    @abstractmethod
    def describir(self) -> str:
        """
        Retorna una representación textual descriptiva del individuo.
        Debe ser implementado obligatoriamente por cada subclase.
        """
        pass


class Empleado(Persona):
    """
    Especialización de Persona que representa a un colaborador laboral de la finca
    (agrónomo, fumigador, recolector, etc.).
    
    Atributos adicionales:
        cargo (str): Rol o cargo asignado en la operación agrícola.
        fecha_ingreso (date): Fecha de inicio laboral (no puede ser futura).
        activo (bool): Estado laboral (borrado lógico para preservar histórico).
    """

    def __init__(
        self,
        nombre: str,
        documento: str,
        telefono: Optional[str],
        cargo: str,
        fecha_ingreso: date
    ) -> None:
        super().__init__(nombre=nombre, documento=documento, telefono=telefono)
        self.cargo = cargo
        self.fecha_ingreso = fecha_ingreso
        self._activo: bool = True

    # -------------------------------------------------------------------------
    # Encapsulamiento de Cargo y Fecha de Ingreso
    # -------------------------------------------------------------------------
    @property
    def cargo(self) -> str:
        """Obtiene el cargo del empleado."""
        return self._cargo

    @cargo.setter
    def cargo(self, valor: str) -> None:
        """Valida que el cargo no esté vacío."""
        if not valor or not valor.strip():
            raise ValueError("El cargo no puede estar vacío ni contener solo espacios.")
        self._cargo = valor.strip()

    @property
    def fecha_ingreso(self) -> date:
        """Obtiene la fecha de ingreso."""
        return self._fecha_ingreso

    @fecha_ingreso.setter
    def fecha_ingreso(self, valor: date) -> None:
        """Valida que la fecha de ingreso no sea futura con respecto al día actual."""
        if valor > date.today():
            raise ValueError(f"La fecha de ingreso ({valor}) no puede ser posterior a la fecha actual ({date.today()}).")
        self._fecha_ingreso = valor

    @property
    def activo(self) -> bool:
        """Mapeo 1:1 con la columna 'activo' de la base de datos."""
        return self._activo

    # -------------------------------------------------------------------------
    # Métodos de Negocio y Control de Estado
    # -------------------------------------------------------------------------
    def esta_activo(self) -> bool:
        """Retorna True si el empleado se encuentra activo operativamente."""
        return self._activo

    def desactivar(self) -> None:
        """
        Realiza un borrado lógico del empleado.
        Preserva el registro para trazabilidad histórica de labores y cosechas.
        """
        self._activo = False

    def activar(self) -> None:
        """Reactiva al empleado en la nómina de la finca."""
        self._activo = True

    # -------------------------------------------------------------------------
    # Polimorfismo: Implementación del método abstracto
    # -------------------------------------------------------------------------
    def describir(self) -> str:
        """Sobrescritura polimórfica que detalla el estado laboral del empleado."""
        estado = "Activo" if self._activo else "Inactivo"
        tel = f", Tel: {self._telefono}" if self._telefono else ""
        return (
            f"Empleado: {self._nombre} | Doc: {self._documento}{tel} | "
            f"Cargo: {self._cargo} | Ingreso: {self._fecha_ingreso.strftime('%Y-%m-%d')} | "
            f"Estado: {estado}"
        )


# =============================================================================
# Bloque de Demostración y Pruebas Unitarias Integradas
# =============================================================================
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  DEMOSTRACIÓN Y PRUEBAS: MÓDULO PERSONA Y EMPLEADO")
    print("=" * 70)

    # 1. Prueba de Creación Exitosa
    print("\n--- 1. Instanciación correcta de Empleados ---")
    emp1 = Empleado("Juan Pérez", "1002003", "3001234567", "Fumigador Certificado", date(2023, 3, 1))
    emp2 = Empleado("María Gómez", "1002004", "3007654321", "Recolectora Principal", date(2024, 6, 15))
    print(emp1.describir())
    print(emp2.describir())

    # 2. Prueba de Desactivación Lógica (Borrado lógico)
    print("\n--- 2. Desactivación lógica (preservación histórica) ---")
    print(f"Estado inicial de Juan: {'Activo' if emp1.esta_activo() else 'Inactivo'}")
    emp1.desactivar()
    print(f"Estado tras desactivar: {'Activo' if emp1.esta_activo() else 'Inactivo'}")
    print(emp1.describir())
    assert not emp1.esta_activo(), "El empleado debería estar inactivo"
    print("[PASS] Desactivación lógica validada correctamente.")

    # 3. Validación de Clase Abstracta (No se puede instanciar Persona directamente)
    print("\n--- 3. Intento de instanciar la clase abstracta Persona ---")
    try:
        # Intento ilegal
        Persona("Persona Fantasma", "999999", "3000000000")  # type: ignore
        print("[FAIL] Se permitió instanciar Persona abstracta.")
    except TypeError as error:
        print(f"[PASS] TypeError controlado exitosamente: {error}")

    # 4. Validaciones de Integridad de Datos (Reglas de Negocio)
    print("\n--- 4. Validación: Nombre vacío ---")
    try:
        Empleado("   ", "1002005", "3000000", "Operario", date(2024, 1, 1))
        print("[FAIL] Se permitió nombre en blanco.")
    except ValueError as error:
        print(f"[PASS] ValueError controlado: {error}")

    print("\n--- 5. Validación: Documento vacío ---")
    try:
        Empleado("Carlos Ruiz", "", "3000000", "Operario", date(2024, 1, 1))
        print("[FAIL] Se permitió documento vacío.")
    except ValueError as error:
        print(f"[PASS] ValueError controlado: {error}")

    print("\n--- 6. Validación: Cargo vacío ---")
    try:
        Empleado("Carlos Ruiz", "1002006", "3000000", "   ", date(2024, 1, 1))
        print("[FAIL] Se permitió cargo en blanco.")
    except ValueError as error:
        print(f"[PASS] ValueError controlado: {error}")

    print("\n--- 7. Validación: Fecha de ingreso futura ---")
    from datetime import timedelta
    fecha_futura = date.today() + timedelta(days=30)
    try:
        Empleado("Carlos Ruiz", "1002006", "3000000", "Operario", fecha_futura)
        print("[FAIL] Se permitió fecha de ingreso futura.")
    except ValueError as error:
        print(f"[PASS] ValueError controlado: {error}")

    print("\n" + "=" * 70)
    print("  ¡TODAS LAS PRUEBAS DE PERSONA Y EMPLEADO PASARON CON ÉXITO!")
    print("=" * 70 + "\n")