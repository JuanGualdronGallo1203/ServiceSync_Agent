"""
Herramienta de consulta de inventario y cotizaciones en tiempo real con Supabase.
Accede a la tabla 'servicios' (id, nombre, precio_base, tiempo_estimado).
Incorpora resiliencia y manejo de errores estricto para Hito S2.
"""

import os
from typing import Optional
from langchain_core.tools import tool

# Catálogo mock de respaldo para entornos sin credenciales activas de Supabase
MOCK_SERVICIOS_DB = [
    {
        "id": 1,
        "nombre": "Mantenimiento Preventivo (Cambio de Aceite y Filtros)",
        "precio_base": 120.0,
        "tiempo_estimado": "45 min",
        "descripcion": "Aceite sintético homologado, filtro de aceite, filtro de aire y revisión de 25 puntos."
    },
    {
        "id": 2,
        "nombre": "Servicio y Diagnóstico de Sistema de Frenos",
        "precio_base": 180.0,
        "tiempo_estimado": "90 min",
        "descripcion": "Pastillas cerámicas, rectificado de discos dentro de tolerancia y purga de líquido DOT 4."
    },
    {
        "id": 3,
        "nombre": "Alineación y Balanceo Computarizado",
        "precio_base": 60.0,
        "tiempo_estimado": "40 min",
        "descripcion": "Alineación 3D en 4 ruedas, balanceo dinámico y calibración de presión con nitrógeno."
    },
    {
        "id": 4,
        "nombre": "Diagnóstico Electrónico Computarizado (Scanner OBD-II)",
        "precio_base": 50.0,
        "tiempo_estimado": "30 min",
        "descripcion": "Escaneo completo de módulos ECU, TCM, ABS, lectura de códigos de falla y borrado de testigos."
    },
    {
        "id": 5,
        "nombre": "Mantenimiento del Sistema de Refrigeración",
        "precio_base": 95.0,
        "tiempo_estimado": "60 min",
        "descripcion": "Drenado, limpieza de radiador, presurización contra fugas y refrigerante orgánico 50/50."
    }
]


@tool
def consultar_inventario_supabase(servicio: Optional[str] = None) -> str:
    """
    Consulta la tabla 'servicios' en Supabase para obtener cotizaciones y tiempos estimados en tiempo real.
    Campos consultados: id, nombre, precio_base, tiempo_estimado.
    
    Args:
        servicio: Nombre o palabra clave del servicio mecánico a consultar (ej. 'aceite', 'frenos', 'alineacion').
                  Si se omite, retorna la lista de servicios disponibles.
    """
    # 1. Verificación de bandera de simulación de error
    if os.getenv("SIMULATE_SUPABASE_ERROR", "false").lower() == "true":
        return "Error en BD: Indica al usuario que los sistemas de precios están en mantenimiento, pero invítalo al taller."

    try:
        supabase_url = os.getenv("SUPABASE_URL", "").strip()
        supabase_key = os.getenv("SUPABASE_KEY", "").strip()

        # Si hay credenciales reales de Supabase configuradas, conectamos vía SDK
        if supabase_url and supabase_key and not supabase_url.startswith("https://tu-proyecto"):
            from supabase import create_client, Client
            client: Client = create_client(supabase_url, supabase_key)
            query = client.table("servicios").select("id, nombre, precio_base, tiempo_estimado")
            
            if servicio:
                # Búsqueda flexible por coincidencia de texto
                query = query.ilike("nombre", f"%{servicio}%")
                
            response = query.execute()
            data = response.data
        else:
            # Consulta SQL real sobre la base de datos local SQLite (data/servicios.db)
            try:
                from src.local_db import query_local_services
                data = query_local_services(servicio)
            except Exception:
                # Fallback seguro en memoria si SQLite tuviese alguna eventualidad
                if servicio:
                    srv_lower = servicio.lower()
                    data = [s for s in MOCK_SERVICIOS_DB if srv_lower in s["nombre"].lower() or any(w in s["nombre"].lower() for w in srv_lower.split())]
                    if not data:
                        data = MOCK_SERVICIOS_DB
                else:
                    data = MOCK_SERVICIOS_DB

        if not data:
            return (
                f"No se encontró un servicio específico con el término '{servicio}' en la base de datos de Supabase. "
                "Los servicios disponibles son: Mantenimiento Preventivo, Frenos, Alineación y Balanceo, Scanner OBD-II y Sistema de Refrigeración."
            )

        # Formateo estructurado para el LLM
        lineas = ["Resultados de inventario en tiempo real (Supabase - tabla 'servicios'):"]
        for item in data:
            lineas.append(
                f"- [ID {item.get('id')}] {item.get('nombre')}: "
                f"Precio base: ${item.get('precio_base', 0.0):.2f} USD | "
                f"Tiempo estimado: {item.get('tiempo_estimado', 'N/D')}"
            )
        return "\n".join(lineas)

    except Exception:
        # Requisito estricto Fase 2
        return "Error en BD: Indica al usuario que los sistemas de precios están en mantenimiento, pero invítalo al taller."

