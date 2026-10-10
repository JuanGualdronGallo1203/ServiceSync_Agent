"""
Script de simulación automatizada End-to-End para ServiceSync Agent.
Valida memoria conversacional de LangGraph, directrices del prompt y políticas anti-alucinación.
"""

import sys
from pathlib import Path

# Asegurar que la raíz del proyecto esté en sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Configuración de codificación segura para Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import uuid
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from langchain_core.messages import HumanMessage, AIMessage

from src.config import validate_config, MODEL_NAME, API_BASE_URL
from src.graph import build_service_sync_graph

console = Console(highlight=False)


def run_e2e_simulation():
    console.print(Panel(
        f"[bold cyan]Simulacion End-to-End Automatica[/bold cyan]\n"
        f"Modelo: [green]{MODEL_NAME}[/green] | Endpoint: [green]{API_BASE_URL}[/green]",
        title="ServiceSync Agent Tests",
        border_style="cyan"
    ))

    is_valid, validation_msg = validate_config()
    if not is_valid:
        console.print(f"[bold yellow][!] Aviso:[/bold yellow] {validation_msg}")
        console.print("[dim]Para ejecutar la simulacion con llamadas en vivo a Platica API, asegurate de configurar RETO_KEY en .env.[/dim]\n")

    app = build_service_sync_graph(enable_memory=True)
    thread_id = f"test_sim_{uuid.uuid4().hex[:6]}"
    config = {"configurable": {"thread_id": thread_id}}

    scenarios = [
        {
            "step": "Paso 1: Saludo e identificacion vehicular",
            "prompt": "Hola, tengo un Honda Civic 2019 con 65,000 km.",
            "test_objective": "Recepcion tecnica y amabilidad operativa.",
        },
        {
            "step": "Paso 2: Consulta de servicio y prueba anti-alucinacion de precios",
            "prompt": "¿Cuanto me cuesta el cambio de aceite y que incluye exactamente?",
            "test_objective": "Verificar memoria del Honda Civic 2019 y regla estricta de NO inventar precios.",
        },
        {
            "step": "Paso 3: Consulta de servicio fuera de catalogo",
            "prompt": "¿Hacen ustedes blindaje balistico nivel 4 o pintura completa para reparar choques grandes?",
            "test_objective": "Verificar delimitacion estricta al catalogo oficial (no soportado).",
        },
        {
            "step": "Paso 4: Reporte de alerta critica de seguridad",
            "prompt": "Noto que cuando presiono el pedal del freno se va hasta el fondo y rechina metalico.",
            "test_objective": "Verificar advertencia de seguridad vial y revision de frenos.",
        },
    ]

    table = Table(title="Resultados de la Simulacion")
    table.add_column("#", style="bold cyan")
    table.add_column("Turno / Mensaje Usuario", style="white")
    table.add_column("Respuesta del Agente", style="green")
    table.add_column("Estado de Memoria", style="yellow")

    console.print(f"[bold blue]Iniciando simulacion con thread_id: {thread_id}...[/bold blue]\n")

    for idx, sc in enumerate(scenarios, 1):
        console.print(f"[bold yellow]>>> Turno {idx}:[/bold yellow] [white]{sc['prompt']}[/white] [dim]({sc['test_objective']})[/dim]")
        
        state_input = {
            "messages": [HumanMessage(content=sc["prompt"])],
            "turn_count": idx - 1,
            "next_step": "start",
            "vehicle_data": {},
            "error": None,
        }

        try:
            result = app.invoke(state_input, config=config)
            messages = result.get("messages", [])
            last_ai = messages[-1].content if messages and isinstance(messages[-1], AIMessage) else "(Sin respuesta)"

            console.print(Panel(str(last_ai), title=f"Agente - Turno {idx}", border_style="magenta"))

            # Validar estado en memoria
            saved_state = app.get_state(config)
            mem_count = len(saved_state.values.get("messages", []))
            table.add_row(
                str(idx),
                sc["prompt"][:40] + "...",
                str(last_ai)[:70].replace("\n", " ") + "...",
                f"{mem_count} msgs en memoria"
            )

        except Exception as exc:
            console.print(f"[bold red]Error en turno {idx}:[/bold red] {exc}")
            table.add_row(str(idx), sc["prompt"][:40], f"Error: {exc}", "Falla")

    console.print("\n")
    console.print(table)
    console.print("\n[bold green]Simulacion finalizada.[/bold green]")


if __name__ == "__main__":
    run_e2e_simulation()
