"""
Script de diagnóstico y prueba rápida para Supabase desde la raíz del proyecto.
"""
import sys
from pathlib import Path

# Agregar la ruta de src al path de Python
ruta_src = Path(__file__).resolve().parent / "gestion_cultivos" / "gestion_cultivos" / "src"
if str(ruta_src) not in sys.path:
    sys.path.insert(0, str(ruta_src))

from supabase_client import verificar_conexion, probar_operaciones_crud

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  VERIFICADOR DE CONEXIÓN - SISTEMA AGROPECUARIO (SUPABASE)")
    print("=" * 60)

    ok = verificar_conexion()
    if ok:
        print("\n[OK] Conectado exitosamente con Supabase.")
        print("Ejecutando pruebas CRUD de validación...")
        crud_ok = probar_operaciones_crud()
        if crud_ok:
            print("\n[ÉXITO] Esquema, credenciales y políticas RLS 100% funcionales.")
        else:
            print("\n[AVISO] Conectó pero ocurrió un error en las operaciones CRUD.")
    else:
        print("\n[ERROR] No se pudo verificar la conexión.")
        print("Asegúrate de haber creado tu archivo .env basado en .env.example")
        print("y de haber ejecutado el archivo schema.sql en el SQL Editor de Supabase.")
    print("=" * 60 + "\n")
