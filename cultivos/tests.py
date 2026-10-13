"""
Suite de Pruebas Unitarias e Integración en Django (B1 y B2)
Sistema de Gestión de Cultivos Agrícolas

Valida:
- B1: Persona (abstracta), Empleado, Cultivo, Lote, CicloProductivo y Regla RN-01.
- B2: Polimorfismo de Labor (Fumigacion, Fertilizacion, OtraLabor), Cosecha (RN-05, RN-06, RN-07),
      Cliente, Venta (control de inventario disponible) y Consultas Agregadas de Reportes.
"""

from datetime import date, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import (
    Empleado,
    Cultivo,
    Lote,
    CicloProductivo,
    Labor,
    Fumigacion,
    Fertilizacion,
    OtraLabor,
    Cosecha,
    Cliente,
    Venta,
)
from .reportes import (
    reporte_cosechado_vs_vendido,
    reporte_costos_por_cultivo,
    reporte_resumen_ciclos,
)


class BackendB1Tests(TestCase):
    """Pruebas del Bloque B1: Empleados, Cultivos, Lotes y Ciclos Productivos (RN-01)."""

    def test_empleado_herencia_y_validaciones(self):
        emp = Empleado.objects.create(
            nombre="Juan Pérez",
            documento="100200300",
            telefono="3001234567",
            cargo="Agrónomo",
            fecha_ingreso=date(2024, 1, 15),
        )
        self.assertTrue(emp.esta_activo())
        self.assertIn("Juan Pérez", emp.describir())
        self.assertIn("activo", emp.describir())

        # Desactivación lógica
        emp.desactivar()
        self.assertFalse(emp.esta_activo())
        self.assertIn("inactivo", emp.describir())

        # Validación de fecha de ingreso futura
        with self.assertRaises(ValidationError):
            Empleado.objects.create(
                nombre="Futuro",
                documento="999888",
                cargo="Operario",
                fecha_ingreso=date.today() + timedelta(days=10),
            )

    def test_cultivo_y_lote_validaciones(self):
        mango = Cultivo.objects.create(nombre="Mango", variedad="Tommy", dias_a_cosecha=120)
        lote = Lote.objects.create(nombre="Lote Norte", area_ha=Decimal("3.50"), ubicacion="Vereda El Sol")
        self.assertEqual(mango.dias_a_cosecha, 120)
        self.assertFalse(lote.tiene_ciclo_activo())

        # Área negativa debe fallar
        with self.assertRaises(ValidationError):
            Lote.objects.create(nombre="Lote Inválido", area_ha=Decimal("-1.0"))

    def test_ciclo_productivo_y_regla_rn01(self):
        mango = Cultivo.objects.create(nombre="Mango", variedad="Tommy", dias_a_cosecha=120)
        lote = Lote.objects.create(nombre="Lote A", area_ha=Decimal("2.50"))
        siembra = date.today() - timedelta(days=50)

        ciclo1 = CicloProductivo.iniciar(lote=lote, cultivo=mango, fecha=siembra)
        self.assertTrue(lote.tiene_ciclo_activo())
        self.assertEqual(ciclo1.dias_transcurridos(), 50)
        self.assertEqual(ciclo1.dias_restantes(), 70)

        # RN-01: No permitir un segundo ciclo activo en el mismo lote
        with self.assertRaises(ValidationError):
            CicloProductivo.iniciar(lote=lote, cultivo=mango, fecha=date.today())

        # Al cerrar el ciclo, el lote queda libre para iniciar otro
        ciclo1.cerrar_ciclo()
        self.assertFalse(lote.tiene_ciclo_activo())

        ciclo2 = CicloProductivo.iniciar(lote=lote, cultivo=mango, fecha=date.today())
        self.assertEqual(ciclo2.estado, "activo")


class BackendB2Tests(TestCase):
    """Pruebas del Bloque B2: Polimorfismo de Labores, Cosecha (RN-05/06/07), Ventas y Reportes."""

    def setUp(self):
        self.empleado = Empleado.objects.create(
            nombre="María Gómez",
            documento="200300400",
            telefono="3109876543",
            cargo="Técnica de Campo",
            fecha_ingreso=date(2023, 5, 1),
        )
        self.cultivo = Cultivo.objects.create(nombre="Fresa", variedad="Albión", dias_a_cosecha=90)
        self.lote = Lote.objects.create(nombre="Lote B", area_ha=Decimal("1.80"), ubicacion="Zona Alta")
        self.fecha_siembra = date.today() - timedelta(days=60)
        self.ciclo = CicloProductivo.iniciar(
            lote=self.lote,
            cultivo=self.cultivo,
            fecha=self.fecha_siembra,
            responsable=self.empleado,
        )

    def test_polimorfismo_labores_y_costo_acumulado(self):
        fum = Fumigacion.objects.create(
            ciclo=self.ciclo,
            responsable=self.empleado,
            fecha=self.fecha_siembra + timedelta(days=10),
            costo=Decimal("150000.00"),
            producto="Abamectina",
            dosis=Decimal("0.50"),
            plaga_objetivo="Ácaro rojo",
            periodo_carencia=15,
        )
        fert = Fertilizacion.objects.create(
            ciclo=self.ciclo,
            responsable=self.empleado,
            fecha=self.fecha_siembra + timedelta(days=20),
            costo=Decimal("220000.00"),
            tipo_abono="Triple 15",
            cantidad=Decimal("100.00"),
            unidad="kg",
        )
        otra = OtraLabor.objects.create(
            ciclo=self.ciclo,
            responsable=self.empleado,
            fecha=self.fecha_siembra + timedelta(days=25),
            costo=Decimal("80000.00"),
            tipo="Desyerbe",
            descripcion="Limpieza manual de surcos",
        )

        # Verificar polimorfismo desde la consulta padre Labor
        labores = list(Labor.objects.filter(ciclo=self.ciclo))
        self.assertEqual(len(labores), 3)
        descripciones = " | ".join(l.describir() for l in labores)
        self.assertIn("Abamectina", descripciones)
        self.assertIn("Triple 15", descripciones)
        self.assertIn("Desyerbe", descripciones)

        # Costo total acumulado en el ciclo
        self.assertEqual(self.ciclo.costo_total_labores(), 450000.0)

    def test_cosecha_regla_carencia_rn05_rn06_rn07(self):
        fecha_fum = date.today() - timedelta(days=5)
        Fumigacion.objects.create(
            ciclo=self.ciclo,
            responsable=self.empleado,
            fecha=fecha_fum,
            costo=Decimal("120000.00"),
            producto="Fungicida Cobre",
            dosis=Decimal("1.00"),
            plaga_objetivo="Botrytis",
            periodo_carencia=10,  # Requiere esperar 10 días (hasta dentro de 5 días)
        )

        # RN-05: Intentar cosechar hoy (solo han pasado 5 de los 10 días de carencia) debe fallar
        with self.assertRaises(ValidationError) as ctx:
            Cosecha.objects.create(
                ciclo=self.ciclo,
                empleado=self.empleado,
                fecha=date.today(),
                kilos=Decimal("300.00"),
            )
        self.assertIn("RN-05", str(ctx.exception))

        # RN-06: Kilos <= 0 debe fallar
        with self.assertRaises(ValidationError):
            Cosecha.objects.create(
                ciclo=self.ciclo,
                empleado=self.empleado,
                fecha=date.today() + timedelta(days=10),
                kilos=Decimal("0.00"),
            )

        # RN-07: Fecha antes de la siembra debe fallar
        with self.assertRaises(ValidationError):
            Cosecha.objects.create(
                ciclo=self.ciclo,
                empleado=self.empleado,
                fecha=self.fecha_siembra - timedelta(days=5),
                kilos=Decimal("100.00"),
            )

        # Cosecha válida una vez cumplido el periodo de carencia (fecha_fum + 10 días)
        fecha_segura = fecha_fum + timedelta(days=10)
        cosecha_ok = Cosecha.objects.create(
            ciclo=self.ciclo,
            empleado=self.empleado,
            fecha=fecha_segura,
            kilos=Decimal("500.00"),
        )
        self.assertEqual(self.ciclo.kilaje_total(), 500.0)

    def test_ventas_control_inventario_y_reportes_agregados(self):
        # 1. Registrar labor y cosecha
        Fertilizacion.objects.create(
            ciclo=self.ciclo,
            responsable=self.empleado,
            fecha=self.fecha_siembra + timedelta(days=10),
            costo=Decimal("100000.00"),
            tipo_abono="Urea",
            cantidad=Decimal("50.00"),
            unidad="kg",
        )
        Cosecha.objects.create(
            ciclo=self.ciclo,
            empleado=self.empleado,
            fecha=date.today(),
            kilos=Decimal("400.00"),
        )

        cliente = Cliente.objects.create(
            nombre="Frutas del Valle S.A.S",
            documento="900123456-1",
            telefono="3150001122",
            tipo_cliente="Mayorista",
        )

        # 2. Registrar venta válida de 250 kg (quedan 150 kg disponibles)
        venta1 = Venta.objects.create(
            cliente=cliente,
            cultivo=self.cultivo,
            fecha=date.today(),
            kilos_vendidos=Decimal("250.00"),
            precio_kilo=Decimal("4000.00"),
        )
        self.assertEqual(float(venta1.total), 1000000.0)
        self.assertEqual(self.cultivo.inventario_disponible(), 150.0)

        # 3. Intentar vender 200 kg cuando solo quedan 150 kg debe lanzar ValidationError
        with self.assertRaises(ValidationError):
            Venta.objects.create(
                cliente=cliente,
                cultivo=self.cultivo,
                fecha=date.today(),
                kilos_vendidos=Decimal("200.00"),
                precio_kilo=Decimal("4000.00"),
            )

        # 4. Probar consultas agregadas de reportes
        rep_cv = reporte_cosechado_vs_vendido()
        self.assertEqual(len(rep_cv), 1)
        self.assertEqual(rep_cv[0]["kilos_cosechados"], 400.0)
        self.assertEqual(rep_cv[0]["kilos_vendidos"], 250.0)
        self.assertEqual(rep_cv[0]["inventario_total_actual"], 150.0)
        self.assertEqual(rep_cv[0]["ingresos_ventas"], 1000000.0)

        rep_costos = reporte_costos_por_cultivo()
        self.assertEqual(rep_costos[0]["costo_fertilizacion"], 100000.0)
        self.assertEqual(rep_costos[0]["utilidad_neta"], 900000.0)

        rep_ciclos = reporte_resumen_ciclos()
        self.assertEqual(len(rep_ciclos), 1)
        self.assertEqual(rep_ciclos[0]["kilaje_total_cosechado"], 400.0)


class FrontendApiIntegrationTests(TestCase):
    """Pruebas de integración de los endpoints REST (/api/...) consumidos por el frontend React."""

    def test_auth_login_y_perfil_yo(self):
        # Login inválido
        res_fail = self.client.post(
            "/api/auth/login",
            data={"username": "admin@cultivos.com", "password": "wrong"},
        )
        self.assertEqual(res_fail.status_code, 401)

        # Login exitoso con form-urlencoded como hace iniciarSesion() en api.js
        res_ok = self.client.post(
            "/api/auth/login",
            data={"username": "admin@cultivos.com", "password": "admin123"},
        )
        self.assertEqual(res_ok.status_code, 200)
        token = res_ok.json()["access_token"]
        self.assertTrue(token)

        # Consultar /api/auth/yo con Bearer token
        res_yo = self.client.get("/api/auth/yo", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(res_yo.status_code, 200)
        datos_yo = res_yo.json()
        self.assertEqual(datos_yo["email"], "admin@cultivos.com")
        self.assertEqual(datos_yo["rol"], "administrador")

    def test_flujo_completo_api_frontend(self):
        import json
        import zipfile
        import io

        # 1. Crear empleado
        res_emp = self.client.post(
            "/api/empleados",
            data=json.dumps({
                "nombre": "Carlos Ruiz",
                "documento": "8090100",
                "cargo": "Fumigador",
                "telefono": "3005556677",
                "activo": True,
            }),
            content_type="application/json",
        )
        self.assertEqual(res_emp.status_code, 201)
        emp_id = res_emp.json()["id"]

        # 2. Crear cultivo con dias_ciclo y periodo_carencia_dias
        res_cult = self.client.post(
            "/api/cultivos",
            data=json.dumps({
                "nombre": "Aguacate",
                "variedad": "Hass",
                "dias_ciclo": 150,
                "periodo_carencia_dias": 12,
                "activo": True,
            }),
            content_type="application/json",
        )
        self.assertEqual(res_cult.status_code, 201)
        cult_data = res_cult.json()
        self.assertEqual(cult_data["dias_ciclo"], 150)
        self.assertEqual(cult_data["periodo_carencia_dias"], 12)
        cult_id = cult_data["id"]

        # 3. Crear lote vinculado al cultivo
        res_lote = self.client.post(
            "/api/lotes",
            data=json.dumps({
                "nombre": "Lote El Mirador",
                "ubicacion": "Sector Oriental",
                "area_hectareas": 4.5,
                "cultivo_id": cult_id,
                "activo": True,
            }),
            content_type="application/json",
        )
        self.assertEqual(res_lote.status_code, 201)
        lote_data = res_lote.json()
        self.assertEqual(lote_data["cultivo"]["nombre"], "Aguacate")
        lote_id = lote_data["id"]

        # 4. Iniciar ciclo productivo desde lote_id y fecha_inicio
        inicio_str = (date.today() - timedelta(days=30)).isoformat()
        res_ciclo = self.client.post(
            "/api/ciclos",
            data=json.dumps({
                "lote_id": lote_id,
                "fecha_inicio": inicio_str,
                "observaciones": "Siembra inicial",
            }),
            content_type="application/json",
        )
        self.assertEqual(res_ciclo.status_code, 201)
        ciclo_id = res_ciclo.json()["id"]
        self.assertEqual(res_ciclo.json()["lote"]["cultivo"]["nombre"], "Aguacate")

        # RN-01 vía API: segundo ciclo activo en el mismo lote debe dar 400
        res_dup = self.client.post(
            "/api/ciclos",
            data=json.dumps({"lote_id": lote_id, "fecha_inicio": date.today().isoformat()}),
            content_type="application/json",
        )
        self.assertEqual(res_dup.status_code, 400)
        self.assertIn("RN-01", res_dup.json()["detail"])

        # 5. Programar y ejecutar una labor de riego, y registrar fumigación ejecutada
        res_lab_prog = self.client.post(
            "/api/labores",
            data=json.dumps({
                "ciclo_id": ciclo_id,
                "empleado_id": emp_id,
                "tipo": "riego",
                "fecha_programada": date.today().isoformat(),
                "fecha_ejecucion": None,
                "producto": None,
                "dosis": None,
                "costo": 60000,
                "observaciones": "Riego por goteo",
            }),
            content_type="application/json",
        )
        self.assertEqual(res_lab_prog.status_code, 201)
        labor_prog_id = res_lab_prog.json()["id"]
        self.assertEqual(res_lab_prog.json()["estado"], "programada")

        # Verificar en /api/labores/proximas
        res_prox = self.client.get("/api/labores/proximas")
        self.assertEqual(len(res_prox.json()), 1)

        # Ejecutar labor programada
        res_ejec = self.client.post(
            f"/api/labores/{labor_prog_id}/ejecutar",
            data=json.dumps({"fecha_ejecucion": date.today().isoformat()}),
            content_type="application/json",
        )
        self.assertEqual(res_ejec.status_code, 200)
        self.assertEqual(res_ejec.json()["estado"], "ejecutada")

        # Registrar fumigación hace 5 días (carencia del cultivo = 12 días)
        fecha_fum = (date.today() - timedelta(days=5)).isoformat()
        res_fum = self.client.post(
            "/api/labores",
            data=json.dumps({
                "ciclo_id": ciclo_id,
                "empleado_id": emp_id,
                "tipo": "fumigacion",
                "fecha_programada": fecha_fum,
                "fecha_ejecucion": fecha_fum,
                "producto": "Mancozeb",
                "dosis": "2.5 g/L",
                "costo": 140000,
                "observaciones": "Control preventivo",
            }),
            content_type="application/json",
        )
        self.assertEqual(res_fum.status_code, 201)

        # 6. Intentar cosechar hoy (viola RN-05 de 12 días de carencia)
        res_cos_bloqueada = self.client.post(
            "/api/cosechas",
            data=json.dumps({
                "ciclo_id": ciclo_id,
                "empleado_id": emp_id,
                "fecha": date.today().isoformat(),
                "kilos": 180,
                "calidad": "Primera",
                "observaciones": "Intento antes de carencia",
            }),
            content_type="application/json",
        )
        self.assertEqual(res_cos_bloqueada.status_code, 400)
        self.assertIn("RN-05", res_cos_bloqueada.json()["detail"])

        # Cosechar cumplida la carencia
        fecha_cosecha_ok = (date.today() + timedelta(days=8)).isoformat()
        res_cos_ok = self.client.post(
            "/api/cosechas",
            data=json.dumps({
                "ciclo_id": ciclo_id,
                "empleado_id": emp_id,
                "fecha": fecha_cosecha_ok,
                "kilos": 320.5,
                "calidad": "Primera",
                "observaciones": "Lote limpio",
            }),
            content_type="application/json",
        )
        self.assertEqual(res_cos_ok.status_code, 201)
        self.assertEqual(res_cos_ok.json()["kilos"], 320.5)

        # 7. Verificar reportes y exportación CSV / Excel
        res_resumen = self.client.get("/api/reportes/resumen").json()
        self.assertEqual(res_resumen["ciclos_activos"], 1)
        self.assertEqual(res_resumen["kilos_totales"], 320.5)
        self.assertEqual(res_resumen["costo_total"], 200000.0)

        res_csv = self.client.get("/api/reportes/exportar/csv")
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn("Mancozeb", res_csv.content.decode("utf-8"))

        res_xlsx = self.client.get("/api/reportes/exportar/excel")
        self.assertEqual(res_xlsx.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(res_xlsx.content), "r") as zf:
            self.assertIn("xl/worksheets/sheet1.xml", zf.namelist())

        # 8. Verificar endpoints de reportes detallados y estado de ciclos
        res_estado = self.client.get("/api/ciclos/estado")
        self.assertEqual(res_estado.status_code, 200)
        self.assertEqual(len(res_estado.json()), 1)
        self.assertEqual(res_estado.json()[0]["lote"], "Lote El Mirador")
        self.assertEqual(res_estado.json()[0]["cultivo"], "Aguacate")

        res_rep_ciclos = self.client.get("/api/reportes/ciclos")
        self.assertEqual(res_rep_ciclos.status_code, 200)
        self.assertEqual(res_rep_ciclos.json()[0]["kilos_cosechados"], 320.5)
        self.assertEqual(res_rep_ciclos.json()[0]["total_labores"], 2)

        res_rep_costos = self.client.get("/api/reportes/costos")
        self.assertEqual(res_rep_costos.status_code, 200)
        self.assertEqual(len(res_rep_costos.json()), 2)

        res_rep_hist = self.client.get("/api/reportes/historial")
        self.assertEqual(res_rep_hist.status_code, 200)
        self.assertEqual(len(res_rep_hist.json()), 2)

        # 9. Probar PUT y DELETE en empleados, cultivos, lotes, labores, cosechas y cierre de ciclo
        res_emp_put = self.client.put(
            f"/api/empleados/{emp_id}",
            data=json.dumps({"nombre": "Carlos Ruiz Editado", "cargo": "Supervisor"}),
            content_type="application/json",
        )
        self.assertEqual(res_emp_put.status_code, 200)
        self.assertEqual(res_emp_put.json()["nombre"], "Carlos Ruiz Editado")

        res_cult_put = self.client.put(
            f"/api/cultivos/{cult_id}",
            data=json.dumps({"dias_ciclo": 160, "periodo_carencia_dias": 10}),
            content_type="application/json",
        )
        self.assertEqual(res_cult_put.status_code, 200)
        self.assertEqual(res_cult_put.json()["dias_ciclo"], 160)

        res_lote_put = self.client.put(
            f"/api/lotes/{lote_id}",
            data=json.dumps({"area_hectareas": 5.0}),
            content_type="application/json",
        )
        self.assertEqual(res_lote_put.status_code, 200)
        self.assertEqual(res_lote_put.json()["area_hectareas"], 5.0)

        # Cerrar ciclo
        res_cerrar = self.client.post(f"/api/ciclos/{ciclo_id}/cerrar", data="{}", content_type="application/json")
        self.assertEqual(res_cerrar.status_code, 200)
        self.assertEqual(res_cerrar.json()["estado"], "cerrado")

        # Eliminar cosecha y desactivar empleado/cultivo/lote
        cosecha_id = res_cos_ok.json()["id"]
        res_cos_del = self.client.delete(f"/api/cosechas/{cosecha_id}")
        self.assertEqual(res_cos_del.status_code, 204)

        res_emp_del = self.client.delete(f"/api/empleados/{emp_id}")
        self.assertEqual(res_emp_del.status_code, 200)
        self.assertFalse(res_emp_del.json()["activo"])

        # CORS preflight OPTIONS
        res_opt = self.client.options("/api/empleados", HTTP_ORIGIN="http://localhost:5173")
        self.assertEqual(res_opt.status_code, 204)
        self.assertEqual(res_opt["Access-Control-Allow-Origin"], "http://localhost:5173")


