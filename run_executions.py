"""
Script de ejecución automatizada y logging para el Hito S2 de ServiceSync Agent.
Ejecuta 10 interacciones comprobables que abarcan:
- Cotizaciones de precios en tiempo real con Supabase.
- Agendamiento y detección de conflictos con Google Calendar.
- Disparo de notificaciones de WhatsApp vía Webhook de n8n.
- Pruebas de resiliencia y manejo estricto de caídas (BD, Calendar, n8n).
- Triage de emergencia automotriz y flujo multi-herramienta end-to-end.

Salida enriquecida con 'rich' para grabación de video y persistencia en 'executions_S2.log'.
"""

import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# Configuración de codificación para Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Asegurar path del proyecto
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from src.config import MODEL_NAME, API_BASE_URL, validate_config
from src.graph import build_service_sync_graph

console = Console(highlight=False)
LOG_FILE = BASE_DIR / "executions_S2.log"


# Definición de las 10 ejecuciones comprobables para el Hito S2
EXECUTIONS_SUITE = [
    {
        "id": 1,
        "titulo": "Consulta de Precio y Duración en Tiempo Real (Supabase)",
        "categoria": "SUPABASE_SUCCESS",
        "prompt": "Hola, tengo un Mazda 3 2021 con 45,000 km. ¿Cuánto cuesta el servicio de cambio de aceite y filtros y cuánto tiempo demora?",
        "env_override": {},
        "criterio_exito": "Uso de consultar_inventario_supabase para obtener precio ($120.00) y duración (45 min)."
    },
    {
        "id": 2,
        "titulo": "Consulta de Cotización para Servicio de Frenos (Supabase)",
        "categoria": "SUPABASE_SUCCESS",
        "prompt": "¿Qué precio base tiene el servicio de frenos y qué incluye el mantenimiento?",
        "env_override": {},
        "criterio_exito": "Uso de consultar_inventario_supabase para cotizar frenos ($180.00 base, 90 min)."
    },
    {
        "id": 3,
        "titulo": "Resiliencia: Caída de Base de Datos de Supabase (Error Handling)",
        "categoria": "SUPABASE_ERROR",
        "prompt": "Quisiera saber el precio de la alineación y balanceo para mi camioneta.",
        "env_override": {"SIMULATE_SUPABASE_ERROR": "true"},
        "criterio_exito": "Captura del error de BD y respuesta al usuario invitándolo al taller debido a mantenimiento de sistemas."
    },
    {
        "id": 4,
        "titulo": "Agendamiento de Cita Disponible en Google Calendar",
        "categoria": "CALENDAR_SUCCESS",
        "prompt": "Por favor agéndame una cita para cambio de aceite a nombre de Carlos Mendoza para el 2026-10-26 a las 10:00 en un Mazda 3.",
        "env_override": {},
        "criterio_exito": "Uso de gestionar_cita_calendar, confirmación de cita y generación de enlace de calendario."
    },
    {
        "id": 5,
        "titulo": "Detección de Conflicto / Superposición en Google Calendar",
        "categoria": "CALENDAR_CONFLICT",
        "prompt": "Hola, soy Laura Gómez y necesito agendar mi vehículo para revisión de frenos exactamente el 2026-10-26 a las 10:00.",
        "env_override": {},
        "criterio_exito": "Detección de horario ocupado (cita de Carlos Mendoza) y solicitud de horario alternativo."
    },
    {
        "id": 6,
        "titulo": "Resiliencia: Caída de Google Calendar API (Error Handling)",
        "categoria": "CALENDAR_ERROR",
        "prompt": "Deseo agendar para el 2026-10-27 a las 15:00 a nombre de Andrés Silva para alineación computarizada.",
        "env_override": {"SIMULATE_CALENDAR_ERROR": "true"},
        "criterio_exito": "Captura del fallo de calendario indicando que no es posible agendar digitalmente en este instante."
    },
    {
        "id": 7,
        "titulo": "Agendamiento con Notificación de WhatsApp Exitosa (n8n Webhook)",
        "categoria": "N8N_SUCCESS",
        "prompt": "Confírmame cita para sistema de refrigeración el 2026-10-28 a las 09:00 a nombre de Roberto Durán, teléfono +525512345678, y envíame confirmación por WhatsApp.",
        "env_override": {},
        "criterio_exito": "Agendamiento en Calendar y disparo exitoso del Webhook de n8n para WhatsApp."
    },
    {
        "id": 8,
        "titulo": "Resiliencia: Caída de Webhook de n8n (Error Handling en Notificación)",
        "categoria": "N8N_ERROR",
        "prompt": "Agenda cita para scanner electrónico el 2026-10-29 a las 11:00 a nombre de Mariana Ruiz, WhatsApp +525587654321.",
        "env_override": {"SIMULATE_N8N_ERROR": "true"},
        "criterio_exito": "Cita confirmada, pero aclara que no recibirá el WhatsApp de confirmación por error de notificación."
    },
    {
        "id": 9,
        "titulo": "Flujo Multi-Herramienta Completo (Supabase + Calendar + n8n)",
        "categoria": "E2E_MULTI_TOOL",
        "prompt": "Cotízame el diagnóstico con scanner OBD-II y luego agéndalo para el 2026-10-30 a las 16:00 para Felipe Castro al teléfono +525599887766 con aviso a su WhatsApp.",
        "env_override": {},
        "criterio_exito": "Secuencia autónoma: consulta precio en Supabase, agenda en Calendar y dispara WhatsApp en n8n."
    },
    {
        "id": 10,
        "titulo": "Triage Crítico de Seguridad Vial + Protocolo de Recepción",
        "categoria": "SAFETY_EMERGENCY",
        "prompt": "¡Ayuda urgente! Mi auto bota humo blanco por el motor, la temperatura está en rojo y el pedal de freno se hunde hasta el fondo.",
        "env_override": {},
        "criterio_exito": "Alerta crítica de NO rodar el vehículo, recomendación de grúa inmediata y triaje de seguridad vial."
    }
]


def log_to_file(file_handle, text: str):
    """Escribe texto plano con timestamp en el archivo de log."""
    file_handle.write(text + "\n")
    file_handle.flush()


def run_all_executions():
    # Inicializar archivo de log limpio
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write(f"SERVICESYNC AGENT - REGISTRO DE 10 EJECUCIONES COMPROBABLES (HITO S2)\n")
        f.write(f"Fecha de Ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Modelo: {MODEL_NAME} | Gateway: {API_BASE_URL}\n")
        f.write(f"Herramientas: consultar_inventario_supabase, gestionar_cita_calendar, notificar_confirmacion_n8n\n")
        f.write("=" * 80 + "\n\n")

    log_f = open(LOG_FILE, "a", encoding="utf-8")

    console.print("\n")
    console.print(Panel.fit(
        f"[bold cyan]🚗 ServiceSync Agent[/bold cyan] - [bold green]Hito S2: 10 Ejecuciones Comprobables[/bold green]\n"
        f"[bold white]Modelo:[/bold white] [yellow]{MODEL_NAME}[/yellow] | "
        f"[bold white]Gateway:[/bold white] [green]{API_BASE_URL}[/green]\n"
        f"[bold white]Herramientas Reales:[/bold white] [cyan]Supabase (BD)[/cyan] · [cyan]Google Calendar[/cyan] · [cyan]n8n Webhook[/cyan]\n"
        f"[bold white]Registro Persistente:[/bold white] [yellow]{LOG_FILE.name}[/yellow]",
        border_style="cyan"
    ))

    # Validar credenciales de Plática
    is_valid, msg = validate_config()
    if not is_valid:
        console.print(f"[bold red][!] Advertencia de Configuración:[/bold red] {msg}")
        log_to_file(log_f, f"[CONFIG ERROR] {msg}")

    # Tabla resumen de las ejecuciones
    summary_table = Table(title="Resumen General de las 10 Ejecuciones (Hito S2)")
    summary_table.add_column("#", style="bold cyan", width=4)
    summary_table.add_column("Caso de Prueba", style="bold white", width=38)
    summary_table.add_column("Herramientas Utilizadas", style="yellow", width=28)
    summary_table.add_column("Estado de Ejecución", style="bold green", width=18)

    # Inicializar grafo de LangGraph
    app = build_service_sync_graph(enable_memory=True)

    for case in EXECUTIONS_SUITE:
        idx = case["id"]
        titulo = case["titulo"]
        categoria = case["categoria"]
        prompt = case["prompt"]
        criterio = case["criterio_exito"]
        overrides = case["env_override"]

        # Aplicar variables de entorno específicas para simulación de errores
        original_env = {}
        for k, v in overrides.items():
            original_env[k] = os.environ.get(k)
            os.environ[k] = v

        thread_id = f"exec_s2_{idx}_{uuid.uuid4().hex[:4]}"
        config = {"configurable": {"thread_id": thread_id}}

        console.print("\n" + "=" * 80)
        console.print(f"[bold cyan][EJECUCIÓN {idx}/10][/bold cyan] [bold white]{titulo}[/bold white]")
        console.print(f"[dim]Categoría: {categoria} | Criterio de Éxito: {criterio}[/dim]")

        log_to_file(log_f, f"\n{'='*70}\nEJECUCIÓN #{idx}: {titulo}\nCategoría: {categoria}\nTimestamp: {datetime.now().isoformat()}")
        log_to_file(log_f, f"Prompt: {prompt}")

        # Mostrar Prompt en terminal
        console.print(Panel(prompt, title=f"Prompt #{idx} (Usuario)", border_style="yellow"))

        start_time = time.time()
        tools_called = []
        final_response = ""
        status_text = "[green]EXITOSO[/green]"

        state_input = {
            "messages": [HumanMessage(content=prompt)],
            "turn_count": 0,
            "next_step": "start",
            "vehicle_data": {},
            "error": None,
        }

        try:
            # Invocar grafo
            result = app.invoke(state_input, config=config)
            elapsed = time.time() - start_time

            messages = result.get("messages", [])

            # Extraer llamadas a herramientas y respuesta final
            for msg in messages:
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for tc in msg.tool_calls:
                        t_name = tc.get("name")
                        t_args = tc.get("args")
                        tools_called.append(t_name)
                        console.print(f"  [bold blue]🔧 Herramienta Invocada:[/bold blue] [cyan]{t_name}[/cyan]")
                        console.print(f"     [dim]Parámetros: {t_args}[/dim]")
                        log_to_file(log_f, f"Tool Call: {t_name} | Args: {t_args}")
                elif isinstance(msg, ToolMessage):
                    preview = str(msg.content)[:120].replace("\n", " ")
                    console.print(f"  [bold magenta]📥 Retorno Herramienta:[/bold magenta] [white]{preview}...[/white]")
                    log_to_file(log_f, f"Tool Output: {msg.content}")

            if messages and isinstance(messages[-1], AIMessage):
                final_response = str(messages[-1].content)
            else:
                final_response = "(Sin respuesta generada)"

            console.print(Panel(
                final_response,
                title=f"Respuesta grok-4.6 (Tiempo: {elapsed:.2f}s)",
                border_style="green"
            ))
            log_to_file(log_f, f"Respuesta Final grok-4.6:\n{final_response}\nTiempo: {elapsed:.2f}s\n")

        except Exception as exc:
            status_text = "[red]ERROR[/red]"
            final_response = f"Excepción durante ejecución: {str(exc)}"
            console.print(Panel(final_response, title="Error", border_style="red"))
            log_to_file(log_f, f"[EXCEPTION] {final_response}")

        finally:
            # Restaurar entorno
            for k, orig in original_env.items():
                if orig is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = orig

        tools_display = ", ".join(set(tools_called)) if tools_called else "Ninguna (Directo)"
        summary_table.add_row(
            str(idx),
            titulo[:36] + ("..." if len(titulo) > 36 else ""),
            tools_display[:26] + ("..." if len(tools_display) > 26 else ""),
            status_text
        )

        # Pausa sutil para visualización fluida
        time.sleep(1)

    log_f.close()

    console.print("\n" + "=" * 80)
    console.print(summary_table)
    console.print(f"\n[bold green][✓] Las 10 ejecuciones han sido procesadas y registradas con éxito.[/bold green]")
    console.print(f"[bold cyan][✓] Archivo de auditoría generado:[/bold cyan] [yellow]{LOG_FILE}[/yellow]\n")


if __name__ == "__main__":
    run_all_executions()
