"""
Suite de Pruebas Unitarias Automatizadas (unittest)
Sistema de Gestión de Cultivos Agrícolas
Cubre: Persona, Empleado, Cultivo, Lote, CicloProductivo, Cosecha.
"""

import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

# Añadir ruta src
ruta_src = Path(__file__).resolve().parent.parent / "gestion_cultivos" / "gestion_cultivos" / "src"
if str(ruta_src) not in sys.path:
    sys.path.insert(0, str(ruta_src))

from persona_empleado import Persona, Empleado
from cultivo_lote_ciclo import Cultivo, Lote, CicloProductivo, Cosecha


class TestPersonaEmpleado(unittest.TestCase):
    """Pruebas para herencia, encapsulamiento y polimorfismo de Persona y Empleado."""

    def test_no_instanciar_persona_abstracta(self):
        """Verifica que la clase abstracta Persona no pueda ser instanciada."""
        with self.assertRaises(TypeError):
            Persona("Test", "123", "300")  # type: ignore

    def test_creacion_empleado_valido(self):
        """Verifica la creación correcta de un empleado y acceso a propiedades."""
        emp = Empleado("Ana Gómez", "102030", "3101234567", "Agrónoma", date(2023, 5, 10))
        self.assertEqual(emp.nombre, "Ana Gómez")
        self.assertEqual(emp.documento, "102030")
        self.assertEqual(emp.telefono, "3101234567")
        self.assertEqual(emp.cargo, "Agrónoma")
        self.assertTrue(emp.esta_activo())
        self.assertTrue(emp.activo)

    def test_desactivacion_logica_empleado(self):
        """Verifica el borrado lógico del empleado."""
        emp = Empleado("Luis Soto", "405060", "", "Operario", date(2023, 1, 1))
        self.assertTrue(emp.esta_activo())
        emp.desactivar()
        self.assertFalse(emp.esta_activo())
        self.assertIn("Inactivo", emp.describir())
        emp.activar()
        self.assertTrue(emp.esta_activo())
        self.assertIn("Activo", emp.describir())

    def test_validaciones_empleado_datos_invalidos(self):
        """Verifica que los setters capturen cadenas vacías y fechas futuras."""
        with self.assertRaises(ValueError):
            Empleado("   ", "123", "", "Operario", date(2023, 1, 1))
        with self.assertRaises(ValueError):
            Empleado("Carlos", "   ", "", "Operario", date(2023, 1, 1))
        with self.assertRaises(ValueError):
            Empleado("Carlos", "123", "", "   ", date(2023, 1, 1))
        with self.assertRaises(ValueError):
            fecha_futura = date.today() + timedelta(days=5)
            Empleado("Carlos", "123", "", "Operario", fecha_futura)


class TestCultivoLoteCiclo(unittest.TestCase):
    """Pruebas para Cultivo, Lote, CicloProductivo y Cosecha."""

    def test_creacion_cultivo_valido(self):
        c = Cultivo("Mango", "Tommy", 120)
        self.assertEqual(c.nombre, "Mango")
        self.assertEqual(c.variedad, "Tommy")
        self.assertEqual(c.dias_a_cosecha, 120)

    def test_validaciones_cultivo_invalidas(self):
        with self.assertRaises(ValueError):
            Cultivo("", "Variedad", 90)
        with self.assertRaises(ValueError):
            Cultivo("Fresa", "Albión", 0)
        with self.assertRaises(ValueError):
            Cultivo("Fresa", "Albión", -10)

    def test_creacion_lote_valido(self):
        lote = Lote("Lote 1", 4.25, "Sector Sur")
        self.assertEqual(lote.nombre, "Lote 1")
        self.assertEqual(lote.area_ha, 4.25)
        self.assertEqual(lote.ubicacion, "Sector Sur")
        self.assertFalse(lote.tiene_ciclo_activo())

    def test_validaciones_lote_invalidas(self):
        with self.assertRaises(ValueError):
            Lote("   ", 3.0)
        with self.assertRaises(ValueError):
            Lote("Lote 2", 0)
        with self.assertRaises(ValueError):
            Lote("Lote 3", -2.5)

    def test_regla_rn_01_un_solo_ciclo_activo_por_lote(self):
        """RN-01: Un lote solo puede tener un ciclo activo a la vez."""
        lote = Lote("Lote Experimental", 1.5)
        cultivo = Cultivo("Aguacate", "Hass", 180)
        siembra = date.today() - timedelta(days=30)

        ciclo1 = CicloProductivo(lote, cultivo, siembra)
        self.assertTrue(lote.tiene_ciclo_activo())

        # Intentar iniciar un segundo ciclo debe fallar
        with self.assertRaises(ValueError):
            CicloProductivo(lote, cultivo, date.today())

        # Cerrar ciclo libera el lote
        ciclo1.cerrar_ciclo()
        self.assertFalse(lote.tiene_ciclo_activo())

        # Ahora sí permite iniciar un nuevo ciclo
        ciclo2 = CicloProductivo(lote, cultivo, date.today())
        self.assertTrue(lote.tiene_ciclo_activo())

    def test_reglas_rn_06_y_rn_07_cosecha(self):
        """RN-06: Kilos > 0 y RN-07: Fecha >= Siembra."""
        lote = Lote("Lote Cosecha", 2.0)
        cultivo = Cultivo("Fresa", "Albión", 90)
        siembra = date.today() - timedelta(days=60)
        ciclo = CicloProductivo(lote, cultivo, siembra)
        empleado = Empleado("Pedro", "987", "", "Recolector", date(2023, 1, 1))

        # Kilos <= 0
        with self.assertRaises(ValueError):
            Cosecha(date.today(), 0, ciclo, empleado)
        with self.assertRaises(ValueError):
            Cosecha(date.today(), -50, ciclo, empleado)

        # Fecha anterior a siembra
        with self.assertRaises(ValueError):
            Cosecha(siembra - timedelta(days=1), 100, ciclo, empleado)

        # Cosecha válida
        c = Cosecha(date.today(), 250.5, ciclo, empleado)
        self.assertEqual(ciclo.kilaje_total(), 250.5)


if __name__ == "__main__":
    unittest.main()
