"""
CLI Interactivo de ServiceSync Agent.
Simula una conversación continua con memoria conversacional (LangGraph + grok-4.6).
Permite verificar la estabilidad del endpoint Plática, la coherencia de grok-4.6 y la gestión de memoria.
"""

import sys
import uuid

# Configuración de codificación segura para Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from src.config import RETO_KEY, API_BASE_URL, MODEL_NAME, validate_config
from src.graph import graph_app

console = Console(highlight=False)


def print_banner():
    banner_text = (
        "[bold cyan]ServiceSync Agent - Terminal CLI (Hito S1)[/bold cyan]\n"
        "[dim]Asistente Operativo Automotriz inteligente con memoria persistente[/dim]\n\n"
        f"• [bold]Endpoint:[/bold] {API_BASE_URL}\n"
        f"• [bold]Modelo:[/bold] {MODEL_NAME}\n"
        f"• [bold]Headers:[/bold] Authorization: Bearer $RETO_KEY | Content-Type: application/json\n"
        "• [bold]Comandos:[/bold] [yellow]/help[/yellow], [yellow]/reset[/yellow], [yellow]/history[/yellow], [yellow]/status[/yellow], [yellow]/exit[/yellow]"
    )
    console.print(Panel(banner_text, border_style="cyan", title="[bold]ServiceSync[/bold]"))


def print_help():
    help_md = """
### Comandos Disponibles:
- **/help**: Muestra esta lista de comandos.
- **/reset**: Reinicia la sesión de memoria y comienza una nueva conversación.
- **/history**: Muestra el historial completo de mensajes en el hilo de memoria actual.
- **/status**: Muestra el estado técnico de la sesión y las configuraciones.
- **/exit** o **/quit**: Salir del asistente.
"""
    console.print(Markdown(help_md))


def show_history(thread_id: str):
    """Inspecciona y muestra el estado actual almacenado en el checkpointer para el thread."""
    try:
        current_state = graph_app.get_state({"configurable": {"thread_id": thread_id}})
        messages = current_state.values.get("messages", []) if current_state and current_state.values else []

        if not messages:
            console.print("[yellow]No hay mensajes almacenados en la sesión actual.[/yellow]")
            return

        console.print(f"\n[bold green]Historial de la sesión ({thread_id}):[/bold green]")
        for idx, msg in enumerate(messages, 1):
            if isinstance(msg, HumanMessage):
                console.print(f"[bold cyan][{idx}] Cliente:[/bold cyan] {msg.content}")
            elif isinstance(msg, AIMessage):
                console.print(f"[bold magenta][{idx}] ServiceSync Agent:[/bold magenta] {msg.content}")
            elif isinstance(msg, SystemMessage):
                console.print(f"[dim][{idx}] System Prompt ({len(msg.content)} caracteres)[/dim]")
        console.print("")
    except Exception as exc:
        console.print(f"[red]Error al consultar el historial: {exc}[/red]")


def main():
    print_banner()

    # Verificación de credenciales
    is_valid, validation_msg = validate_config()
    if not is_valid:
        console.print(Panel(
            f"[bold red]Atencion:[/] {validation_msg}\n\n"
            "[yellow]Para probar con el LLM real:[/yellow]\n"
            "1. Abre el archivo [bold].env[/bold] en la raiz del proyecto.\n"
            "2. Establece tu clave real: [green]RETO_KEY=tu_token_aqui[/green]\n"
            "3. Ejecuta de nuevo este script o corre [cyan]python test_connection.py[/cyan].",
            title="[bold yellow]Configuracion Incompleta[/bold yellow]",
            border_style="yellow"
        ))

    # Identificador único para el hilo de memoria de LangGraph
    thread_id = str(uuid.uuid4())[:8]
    console.print(f"[dim]Sesion iniciada con Thread ID:[/] [bold cyan]{thread_id}[/bold cyan]\n")

    while True:
        try:
            user_input = Prompt.ask("[bold green]Tu[/bold green]").strip()

            if not user_input:
                continue

            # Gestión de comandos internos
            lower_input = user_input.lower()
            if lower_input in ["/exit", "/quit", "exit", "quit"]:
                console.print("\n[bold cyan]ServiceSync Agent:[/] Gracias por contactar al centro automotriz. ¡Hasta pronto!\n")
                break
            elif lower_input == "/help":
                print_help()
                continue
            elif lower_input in ["/reset", "/new"]:
                thread_id = str(uuid.uuid4())[:8]
                console.print(f"[bold yellow]Memoria reiniciada. Nuevo Thread ID:[/] [cyan]{thread_id}[/cyan]\n")
                continue
            elif lower_input == "/history":
                show_history(thread_id)
                continue
            elif lower_input == "/status":
                console.print(f"[cyan]Thread ID actual:[/] {thread_id}")
                console.print(f"[cyan]Endpoint:[/cyan] {API_BASE_URL}")
                console.print(f"[cyan]Modelo:[/cyan] {MODEL_NAME}")
                continue

            # Ejecución a través del grafo de LangGraph
            config = {"configurable": {"thread_id": thread_id}}
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "turn_count": 0,
                "next_step": "start",
                "vehicle_data": {},
                "error": None,
            }

            with console.status("[bold cyan]ServiceSync Agent está analizando y respondiendo...[/bold cyan]", spinner="dots"):
                result = graph_app.invoke(initial_state, config=config)

            messages = result.get("messages", [])
            error = result.get("error")

            if messages and isinstance(messages[-1], AIMessage):
                ai_text = messages[-1].content
                console.print(f"\n[bold magenta]ServiceSync Agent:[/bold magenta]")
                console.print(Markdown(str(ai_text)))
                console.print("")
            elif error:
                console.print(f"\n[bold red][Error]:[/bold red] {error}\n")
            else:
                console.print("\n[yellow]No se recibió respuesta del modelo.[/yellow]\n")

        except (KeyboardInterrupt, EOFError):
            console.print("\n\n[bold cyan]Sesion terminada por el usuario.[/bold cyan]")
            break
        except Exception as exc:
            console.print(f"\n[bold red]Error imprevisto en la ejecucion:[/bold red] {exc}\n")


if __name__ == "__main__":
    main()
