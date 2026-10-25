"""
Pruebas unitarias para las herramientas y el grafo del Hito S2.
Valida las herramientas consultar_inventario_supabase, gestionar_cita_calendar,
notificar_confirmacion_n8n y sus políticas de resiliencia y error handling.
"""

import os
import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.inventory import consultar_inventario_supabase
from src.tools.calendar_tool import gestionar_cita_calendar
from src.tools.notification import notificar_confirmacion_n8n
from src.graph import build_service_sync_graph, should_continue
from langchain_core.messages import AIMessage


class TestHitoS2ToolsAndGraph(unittest.TestCase):

    def test_supabase_inventory_success(self):
        """Verifica que la consulta de inventario retorne campos id, nombre, precio_base y tiempo_estimado."""
        res = consultar_inventario_supabase.invoke({"servicio": "aceite"})
        self.assertIn("Mantenimiento Preventivo", res)
        self.assertIn("Precio base", res)
        self.assertIn("Tiempo estimado", res)

    def test_supabase_error_handling(self):
        """Verifica la respuesta exacta ante caída de Supabase."""
        os.environ["SIMULATE_SUPABASE_ERROR"] = "true"
        try:
            res = consultar_inventario_supabase.invoke({"servicio": "frenos"})
            self.assertEqual(
                res,
                "Error en BD: Indica al usuario que los sistemas de precios están en mantenimiento, pero invítalo al taller."
            )
        finally:
            os.environ.pop("SIMULATE_SUPABASE_ERROR", None)

    def test_calendar_success_and_conflict(self):
        """Verifica agendamiento con duración dinámica, detección de duplicados (idempotencia) y colisiones."""
        # 1. Agendar en horario libre con bloque dinámico de 2 horas (10:00 a 12:00)
        res1 = gestionar_cita_calendar.invoke({
            "fecha_hora_inicio": "2026-11-01 10:00",
            "fecha_hora_fin": "2026-11-01 12:00",
            "cliente": "Pedro Infante",
            "servicio": "Cambio de Aceite"
        })
        self.assertIn("Cita confirmada exitosamente", res1)
        self.assertIn("Enlace de confirmación", res1)
        self.assertIn("hora Bogotá", res1)

        # 2. Re-agendamiento por el mismo cliente (Idempotencia / Evita duplicados sin error)
        res_dup = gestionar_cita_calendar.invoke({
            "fecha_hora_inicio": "2026-11-01 10:30",
            "fecha_hora_fin": "2026-11-01 11:30",
            "cliente": "Pedro Infante",
            "servicio": "Cambio de Aceite"
        })
        self.assertIn("Cita ya registrada previamente", res_dup)
        self.assertIn("No se creó un duplicado", res_dup)

        # 3. Intentar agendar en el mismo horario por otro cliente (Colisión de disponibilidad)
        res2 = gestionar_cita_calendar.invoke({
            "fecha_hora_inicio": "2026-11-01 11:00",
            "fecha_hora_fin": "2026-11-01 13:00",
            "cliente": "Jorge Negrete",
            "servicio": "Frenos"
        })
        self.assertIn("Conflicto de disponibilidad", res2)

    def test_calendar_error_handling(self):
        """Verifica la respuesta exacta ante fallo de Google Calendar."""
        os.environ["SIMULATE_CALENDAR_ERROR"] = "true"
        try:
            res = gestionar_cita_calendar.invoke({
                "fecha_hora_inicio": "2026-11-02 12:00",
                "fecha_hora_fin": "2026-11-02 13:00",
                "cliente": "Test Client",
                "servicio": "Alineacion"
            })
            self.assertEqual(
                res,
                "Error en Calendario: Dile al usuario que no es posible agendar digitalmente en este instante."
            )
        finally:
            os.environ.pop("SIMULATE_CALENDAR_ERROR", None)

    def test_n8n_notification_success(self):
        """Verifica que el webhook de n8n reporte envío exitoso."""
        res = notificar_confirmacion_n8n.invoke({
            "cliente": "Ana Brenda",
            "servicio": "Frenos",
            "fecha": "2026-11-03 15:00",
            "telefono": "+525500001111"
        })
        self.assertIn("Notificación enviada", res)
        self.assertIn("WhatsApp", res)

    def test_n8n_notification_error_handling(self):
        """Verifica la respuesta exacta ante caída del Webhook de n8n."""
        os.environ["SIMULATE_N8N_ERROR"] = "true"
        try:
            res = notificar_confirmacion_n8n.invoke({
                "cliente": "Falla Webhook",
                "servicio": "Refrigeración",
                "fecha": "2026-11-03 15:00"
            })
            self.assertEqual(
                res,
                "Error en Notificación: Confírmale la cita al usuario, pero indícale que no recibirá el WhatsApp de confirmación."
            )
        finally:
            os.environ.pop("SIMULATE_N8N_ERROR", None)

    def test_graph_structure_and_tool_routing(self):
        """Verifica que el grafo contenga el ToolNode y que should_continue bifurque hacia tools si hay tool_calls."""
        app = build_service_sync_graph(enable_memory=False)
        self.assertIn("tools", app.nodes)
        self.assertIn("call_model", app.nodes)
        self.assertIn("process_state", app.nodes)

        # Mensaje sin llamadas a herramientas -> process_state
        state_no_tool = {"messages": [AIMessage(content="Hola")]}
        self.assertEqual(should_continue(state_no_tool), "process_state")

        # Mensaje con tool_calls -> tools
        state_with_tool = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[{"name": "consultar_inventario_supabase", "args": {}, "id": "1", "type": "tool_call"}]
                )
            ]
        }
        self.assertEqual(should_continue(state_with_tool), "tools")



    def test_local_sqlite_database(self):
        """Verifica que la base de datos local SQLite cree la tabla y responda consultas SQL reales."""
        from src.local_db import query_local_services, init_local_database
        db_path = init_local_database()
        self.assertTrue(db_path.exists())

        # Consulta de todos los servicios
        all_services = query_local_services()
        self.assertGreaterEqual(len(all_services), 5)

        # Consulta con filtro SQL
        frenos = query_local_services("frenos")
        self.assertTrue(any("Frenos" in s["nombre"] for s in frenos))
        self.assertEqual(frenos[0]["precio_base"], 180.0)


if __name__ == "__main__":
    unittest.main()

