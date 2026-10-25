"""
Pruebas unitarias para los componentes centrales de ServiceSync Agent.
Valida configuración, catálogo, prompts, estructura del grafo y memoria de estado.
"""

import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from src.config import API_BASE_URL, MODEL_NAME, get_http_headers
from src.catalog import AUTOMOTIVE_SERVICES_CATALOG, SERVICES_NOT_SUPPORTED, get_catalog_summary
from src.prompts import get_system_prompt
from src.graph import build_service_sync_graph, route_decision, process_state_node


class TestServiceSyncComponents(unittest.TestCase):

    def test_config_endpoints_and_headers(self):
        """Verifica que el endpoint base y los headers cumplan las especificaciones del reto."""
        self.assertEqual(API_BASE_URL, "https://api.reto.pltk.mx/v1")
        self.assertEqual(MODEL_NAME, "grok-4.6")

        headers = get_http_headers()
        self.assertIn("Authorization", headers)
        self.assertIn("Content-Type", headers)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertTrue(headers["Authorization"].startswith("Bearer "))

    def test_catalog_integrity(self):
        """Verifica que el catálogo oficial contenga los servicios clave y exclusiones."""
        self.assertIn("mantenimiento_preventivo", AUTOMOTIVE_SERVICES_CATALOG)
        self.assertIn("sistema_de_frenos", AUTOMOTIVE_SERVICES_CATALOG)
        self.assertIn("diagnostico_electronico", AUTOMOTIVE_SERVICES_CATALOG)
        self.assertTrue(len(SERVICES_NOT_SUPPORTED) >= 3)

        summary = get_catalog_summary()
        self.assertIn("CATÁLOGO OFICIAL", summary)
        self.assertIn("POLÍTICA DE PRECIOS", summary)

    def test_system_prompt_rules(self):
        """Verifica que el System Prompt contenga las directrices operativas y reglas anti-alucinación."""
        prompt = get_system_prompt()
        self.assertIn("ServiceSync Agent", prompt)
        self.assertIn("no inventes precios ni servicios", prompt.lower())
        self.assertIn("REGLAS ESTRICTAS CONTRA ALUCINACIONES", prompt)
        self.assertIn("Triaje y Captura de Información Vehicular", prompt)
        self.assertIn("Seguridad Mecánica Primaria", prompt)

    def test_graph_structure_and_nodes(self):
        """Verifica que el grafo contenga los nodos requeridos y compile correctamente."""
        app = build_service_sync_graph(enable_memory=True)
        self.assertIsNotNone(app)
        
        # Verificar nodos en el grafo
        nodes = app.get_graph().nodes
        self.assertIn("call_model", nodes)
        self.assertIn("tools", nodes)
        self.assertIn("process_state", nodes)

    def test_process_state_node(self):
        """Verifica que el nodo process_state evalúe el estado e incremente el contador de turnos."""
        state = {
            "messages": [HumanMessage(content="Hola"), AIMessage(content="Buenas tardes, centro de servicio.")],
            "turn_count": 0,
            "next_step": "start",
            "vehicle_data": {},
            "error": None,
        }
        res = process_state_node(state)
        self.assertEqual(res["turn_count"], 1)
        self.assertEqual(res["next_step"], "respond")
        self.assertIsNone(res["error"])

    def test_route_decision(self):
        """Verifica el enrutamiento condicional para responder de forma fluida."""
        self.assertEqual(route_decision({"next_step": "respond"}), "respond")
        self.assertEqual(route_decision({"next_step": "error"}), "error")
        self.assertEqual(route_decision({"next_step": "end"}), "end")
        self.assertEqual(route_decision({}), "respond")


if __name__ == "__main__":
    unittest.main()
