"""
Sistema de Gestión de Cultivos Agrícolas - Semana 5
Módulo: repositorio.py

Implementa la clase RepositorioSQLite según el Diagrama de Clases UML:
- conexion: Connection
- + guardar(entidad)
- + consultar(filtros): list
- + actualizar(entidad)
- + eliminar(id)
"""

import sqlite3
from datetime import date
from typing import Any, Dict, List, Optional


class RepositorioSQLite:
    """
    Capa de persistencia local en SQLite que cumple con la interfaz del diagrama UML.
    """

    def __init__(self, ruta_bd: str = ":memory:") -> None:
        self.conexion: sqlite3.Connection = sqlite3.connect(ruta_bd)
        self.conexion.row_factory = sqlite3.Row
        self._inicializar_tablas()

    def _inicializar_tablas(self) -> None:
        cursor = self.conexion.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS empleados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                documento TEXT NOT NULL UNIQUE,
                telefono TEXT,
                cargo TEXT NOT NULL,
                fecha_ingreso TEXT NOT NULL,
                activo INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS cultivos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                variedad TEXT,
                dias_a_cosecha INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                area_ha REAL NOT NULL,
                ubicacion TEXT
            );
            """
        )
        self.conexion.commit()

    def guardar(self, tabla: str, datos: Dict[str, Any]) -> int:
        """Inserta un registro en la tabla indicada y retorna su ID."""
        columnas = ", ".join(datos.keys())
        placeholders = ", ".join(["?"] * len(datos))
        valores = [str(v) if isinstance(v, date) else v for v in datos.values()]
        cursor = self.conexion.cursor()
        cursor.execute(f"INSERT INTO {tabla} ({columnas}) VALUES ({placeholders})", valores)
        self.conexion.commit()
        return int(cursor.lastrowid or 0)

    def consultar(self, tabla: str, filtros: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Consulta registros de una tabla aplicando filtros opcionales."""
        cursor = self.conexion.cursor()
        if filtros:
            condiciones = " AND ".join([f"{k} = ?" for k in filtros.keys()])
            valores = list(filtros.values())
            cursor.execute(f"SELECT * FROM {tabla} WHERE {condiciones}", valores)
        else:
            cursor.execute(f"SELECT * FROM {tabla}")
        return [dict(fila) for fila in cursor.fetchall()]

    def actualizar(self, tabla: str, id_registro: int, datos: Dict[str, Any]) -> bool:
        """Actualiza los campos de un registro por su ID."""
        asignaciones = ", ".join([f"{k} = ?" for k in datos.keys()])
        valores = [str(v) if isinstance(v, date) else v for v in datos.values()] + [id_registro]
        cursor = self.conexion.cursor()
        cursor.execute(f"UPDATE {tabla} SET {asignaciones} WHERE id = ?", valores)
        self.conexion.commit()
        return cursor.rowcount > 0

    def eliminar(self, tabla: str, id_registro: int) -> bool:
        """Elimina un registro por su ID."""
        cursor = self.conexion.cursor()
        cursor.execute(f"DELETE FROM {tabla} WHERE id = ?", (id_registro,))
        self.conexion.commit()
        return cursor.rowcount > 0

    def cerrar(self) -> None:
        self.conexion.close()
