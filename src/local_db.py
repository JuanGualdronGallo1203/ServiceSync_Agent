"""
Módulo de base de datos local SQLite para ServiceSync Agent.
Permite persistencia y consultas SQL reales en local (tabla 'servicios')
cuando no se dispone de un contenedor activo o credenciales remotas de Supabase.
"""

import sqlite3
from pathlib import Path
from typing import Optional

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_FILE = DB_DIR / "servicios.db"

INITIAL_SERVICES = [
    (1, "Mantenimiento Preventivo (Cambio de Aceite y Filtros)", 120.0, "45 min", "Aceite sintético homologado, filtro de aceite, filtro de aire y revisión de 25 puntos."),
    (2, "Servicio y Diagnóstico de Sistema de Frenos", 180.0, "90 min", "Pastillas cerámicas, rectificado de discos dentro de tolerancia y purga de líquido DOT 4."),
    (3, "Alineación y Balanceo Computarizado", 60.0, "40 min", "Alineación 3D en 4 ruedas, balanceo dinámico y calibración de presión con nitrógeno."),
    (4, "Diagnóstico Electrónico Computarizado (Scanner OBD-II)", 50.0, "30 min", "Escaneo completo de módulos ECU, TCM, ABS, lectura de códigos de falla y borrado de testigos."),
    (5, "Mantenimiento del Sistema de Refrigeración", 95.0, "60 min", "Drenado, limpieza de radiador, presurización contra fugas y refrigerante orgánico 50/50."),
]


def init_local_database() -> Path:
    """Crea el directorio de datos, la tabla 'servicios' y siembra los registros iniciales."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS servicios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                precio_base REAL NOT NULL,
                tiempo_estimado TEXT NOT NULL,
                descripcion TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("SELECT COUNT(*) FROM servicios")
        count = cursor.fetchone()[0]
        
        if count == 0:
            cursor.executemany("""
                INSERT INTO servicios (id, nombre, precio_base, tiempo_estimado, descripcion)
                VALUES (?, ?, ?, ?, ?)
            """, INITIAL_SERVICES)
            conn.commit()
    finally:
        conn.close()
            
    return DB_FILE


def query_local_services(servicio: Optional[str] = None) -> list[dict]:
    """
    Ejecuta una consulta SQL real sobre la base de datos local 'servicios.db'.
    Retorna registros con estructura compatible con Supabase:
    id, nombre, precio_base, tiempo_estimado, descripcion.
    """
    init_local_database()
    
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if servicio and servicio.strip():
            term = f"%{servicio.strip().lower()}%"
            cursor.execute("""
                SELECT id, nombre, precio_base, tiempo_estimado, descripcion
                FROM servicios
                WHERE LOWER(nombre) LIKE ?
                ORDER BY id ASC
            """, (term,))
            rows = cursor.fetchall()
            
            if not rows:
                words = [w.strip().lower() for w in servicio.split() if len(w.strip()) > 2]
                if words:
                    clauses = " OR ".join(["LOWER(nombre) LIKE ?"] * len(words))
                    params = [f"%{w}%" for w in words]
                    cursor.execute(f"""
                        SELECT id, nombre, precio_base, tiempo_estimado, descripcion
                        FROM servicios
                        WHERE {clauses}
                        ORDER BY id ASC
                    """, params)
                    rows = cursor.fetchall()
        else:
            cursor.execute("""
                SELECT id, nombre, precio_base, tiempo_estimado, descripcion
                FROM servicios
                ORDER BY id ASC
            """)
            rows = cursor.fetchall()
            
        return [
            {
                "id": r["id"],
                "nombre": r["nombre"],
                "precio_base": float(r["precio_base"]),
                "tiempo_estimado": r["tiempo_estimado"],
                "descripcion": r["descripcion"]
            }
            for r in rows
        ]
    finally:
        conn.close()
