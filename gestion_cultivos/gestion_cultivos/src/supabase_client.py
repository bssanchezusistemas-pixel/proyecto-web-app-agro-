"""
Módulo de conexión y cliente para Supabase (PostgreSQL)
Sistema de Gestión de Cultivos Agrícolas

Proporciona la inicialización centralizada del cliente Supabase,
verificación de conectividad y pruebas de operaciones de datos.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv, find_dotenv
from supabase import create_client, Client

# -----------------------------------------------------------------------------
# 1. Configuración de Logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("supabase_client")

# -----------------------------------------------------------------------------
# 2. Carga flexible de variables de entorno (.env)
# -----------------------------------------------------------------------------
def _cargar_variables_entorno():
    """Busca y carga el archivo .env desde el directorio de trabajo o ancestros."""
    # Primero intentar find_dotenv
    env_path = find_dotenv(usecwd=True)
    if env_path:
        load_dotenv(env_path)
        logger.debug(f"Archivo .env cargado desde: {env_path}")
        return

    # Búsqueda manual en los directorios superiores
    directorio_actual = Path(__file__).resolve().parent
    for nivel in range(5):
        posible_env = directorio_actual / ".env"
        if posible_env.exists():
            load_dotenv(posible_env)
            logger.debug(f"Archivo .env cargado desde: {posible_env}")
            return
        directorio_actual = directorio_actual.parent

    # Si no se encuentra, load_dotenv cargará desde el entorno del sistema
    load_dotenv()

_cargar_variables_entorno()

# Variable global para patrón Singleton
_cliente_supabase: Optional[Client] = None


# -----------------------------------------------------------------------------
# 3. Inicialización del Cliente Supabase (Singleton)
# -----------------------------------------------------------------------------
def get_supabase_client() -> Client:
    """
    Obtiene o crea una instancia única del cliente de Supabase.
    
    Requiere las variables de entorno:
      - SUPABASE_URL: URL del proyecto (ej: https://xyz.supabase.co)
      - SUPABASE_KEY: Clave anon o service_role
      
    Returns:
        Client: Instancia configurada de Supabase Client.
        
    Raises:
        ValueError: Si faltan credenciales o son valores de plantilla.
        RuntimeError: Si ocurre un error de inicialización en el SDK.
    """
    global _cliente_supabase
    if _cliente_supabase is not None:
        return _cliente_supabase

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_KEY", "").strip()

    # Validación de presencia de credenciales
    if not supabase_url or not supabase_key:
        error_msg = (
            "Credenciales de Supabase no encontradas en el entorno.\n"
            "Asegúrate de definir SUPABASE_URL y SUPABASE_KEY en tu archivo .env o en el sistema.\n"
            "Ejemplo de formato en .env:\n"
            "  SUPABASE_URL=https://tu-proyecto.supabase.co\n"
            "  SUPABASE_KEY=tu-clave-anon-o-service-role"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Validación contra valores por defecto de ejemplo
    if "tu-proyecto.supabase.co" in supabase_url or "tu-anon-key" in supabase_key:
        error_msg = (
            "Las variables en .env aún contienen los valores de ejemplo de .env.example.\n"
            "Por favor, actualiza SUPABASE_URL y SUPABASE_KEY con los valores reales de tu panel de Supabase."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        _cliente_supabase = create_client(supabase_url, supabase_key)
        logger.info("Cliente de Supabase inicializado correctamente.")
        return _cliente_supabase
    except Exception as e:
        logger.exception(f"Fallo al inicializar el cliente de Supabase: {e}")
        raise RuntimeError(f"Error al conectar con el SDK de Supabase: {e}") from e


# -----------------------------------------------------------------------------
# 4. Verificación de Conectividad (Health Check)
# -----------------------------------------------------------------------------
def verificar_conexion(client: Optional[Client] = None) -> bool:
    """
    Verifica que la conexión a Supabase y la base de datos PostgreSQL funcione.
    Realiza una consulta ligera a la tabla 'cultivos' o 'personas'.

    Args:
        client: Cliente de Supabase opcional. Si es None, utiliza get_supabase_client().

    Returns:
        bool: True si la conexión y consulta fueron exitosas, False en caso contrario.
    """
    try:
        if client is None:
            client = get_supabase_client()

        # Consulta ligera (limit 1) a la tabla cultivos
        respuesta = client.table("cultivos").select("id").limit(1).execute()
        
        logger.info("Conexión con Supabase verificada exitosamente.")
        return True

    except ValueError as ve:
        logger.warning(f"Verificación abortada por configuración incompleta: {ve}")
        return False
    except Exception as e:
        logger.error(f"Error al verificar la conexión con Supabase: {e}")
        logger.info(
            "Verifica que:\n"
            " 1. El script schema.sql haya sido ejecutado en el SQL Editor de Supabase.\n"
            " 2. Las políticas RLS permitan lectura (SELECT) o estés usando la service_role key.\n"
            " 3. La URL y la KEY sean exactamente las de tu proyecto activo en Supabase."
        )
        return False


# -----------------------------------------------------------------------------
# 5. Prueba de Operaciones CRUD Básicas
# -----------------------------------------------------------------------------
def probar_operaciones_crud(client: Optional[Client] = None) -> bool:
    """
    Ejecuta un ciclo de prueba (Inserción, Consulta y Eliminación)
    para validar que los permisos y constraints funcionan correctamente.
    
    Returns:
        bool: True si todo el ciclo CRUD de prueba se ejecutó con éxito.
    """
    try:
        if client is None:
            client = get_supabase_client()

        logger.info("Iniciando prueba de operaciones CRUD en tabla 'cultivos'...")

        # 1. Inserción de prueba
        datos_prueba = {
            "nombre": "Cultivo Test Temporal",
            "variedad": "Variedad AutoTest",
            "dias_a_cosecha": 120
        }
        res_insert = client.table("cultivos").insert(datos_prueba).execute()
        if not res_insert.data:
            logger.error("No se recibieron datos de confirmación tras la inserción.")
            return False

        registro_id = res_insert.data[0]["id"]
        logger.info(f"Registro de prueba insertado exitosamente con ID: {registro_id}")

        # 2. Consulta de verificación
        res_select = client.table("cultivos").select("*").eq("id", registro_id).execute()
        if not res_select.data:
            logger.error(f"No se encontró el registro con ID {registro_id} al consultar.")
            return False
        logger.info(f"Registro verificado: {res_select.data[0]['nombre']} ({res_select.data[0]['variedad']})")

        # 3. Limpieza (Eliminar registro de prueba)
        client.table("cultivos").delete().eq("id", registro_id).execute()
        logger.info(f"Registro de prueba {registro_id} eliminado exitosamente (limpieza completa).")

        logger.info("¡Todas las operaciones CRUD de prueba finalizaron con éxito!")
        return True

    except Exception as e:
        logger.error(f"Error durante las pruebas CRUD: {e}")
        return False


# -----------------------------------------------------------------------------
# 6. Ejecución directa como script de diagnóstico
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  DIAGNÓSTICO DE CONEXIÓN A SUPABASE (POSTGRESQL)")
    print("=" * 60)

    try:
        conectado = verificar_conexion()
        if conectado:
            print("\n[OK] Conexión establecida correctamente con Supabase.")
            print("\nProbando ciclo de inserción, consulta y eliminación...")
            crud_ok = probar_operaciones_crud()
            if crud_ok:
                print("\n[OK] Base de datos y permisos RLS funcionando al 100%.")
            else:
                print("\n[ADVERTENCIA] Conexión establecida pero falló la prueba CRUD.")
        else:
            print("\n[FALLO] No se pudo verificar la conexión con Supabase.")
            print("Revisa los mensajes de log arriba para más detalles.")
    except Exception as general_err:
        print(f"\n[ERROR CRÍTICO] {general_err}")
    print("=" * 60 + "\n")
