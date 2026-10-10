"""
Script de diagnóstico y prueba de conectividad con Plática API.
Valida la configuración de entorno, headers HTTP requeridos y respuesta del modelo grok-4.6.
"""

import sys

# Configuración de codificación segura para Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.config import RETO_KEY, API_BASE_URL, MODEL_NAME, validate_config, get_http_headers
from src.llm_client import test_raw_http_connection

console = Console(highlight=False)


def run_diagnostics():
    console.print(Panel.fit(
        "[bold cyan]ServiceSync Agent[/bold cyan] - [bold green]Diagnostico de Conexion HTTP Platica API[/bold green]",
        border_style="cyan"
    ))

    # 1. Validación de variables de entorno
    is_valid, validation_msg = validate_config()
    table = Table(title="1. Configuracion de Entorno")
    table.add_column("Parametro", style="bold yellow")
    table.add_column("Valor Actual", style="white")
    table.add_column("Estado", style="bold")

    table.add_row(
        "API Base URL",
        API_BASE_URL,
        "[green][OK][/green]" if API_BASE_URL == "https://api.reto.pltk.mx/v1" else "[yellow][MODIFICADO][/yellow]"
    )
    table.add_row(
        "Modelo Objetivo",
        MODEL_NAME,
        "[green][OK][/green]" if MODEL_NAME == "grok-4.6" else "[yellow][MODIFICADO][/yellow]"
    )

    key_display = (RETO_KEY[:6] + "..." + RETO_KEY[-4:]) if len(RETO_KEY) > 10 else ("CONFIGURADA" if (RETO_KEY and RETO_KEY != "tu_clave_de_platica_aqui") else "NO CONFIGURADA")
    table.add_row(
        "RETO_KEY",
        key_display,
        "[green][CONFIGURADA][/green]" if is_valid else "[red][FALTANTE / DEFAULT][/red]"
    )

    console.print(table)

    # 2. Validación de Headers requeridos
    headers = get_http_headers()
    headers_table = Table(title="2. Headers HTTP Requeridos")
    headers_table.add_column("Header", style="bold cyan")
    headers_table.add_column("Valor de Envio", style="white")

    headers_table.add_row("Authorization", f"Bearer {key_display}")
    headers_table.add_row("Content-Type", headers.get("Content-Type", "Desconocido"))
    console.print(headers_table)

    if not is_valid:
        console.print(f"\n[bold red][!] ADVERTENCIA:[/bold red] {validation_msg}")
        console.print("[dim]Edita el archivo .env y asigna tu RETO_KEY antes de continuar.[/dim]\n")
        return False

    # 3. Prueba de llamada HTTP en vivo
    console.print("\n[bold blue]Realizando peticion de prueba POST a https://api.reto.pltk.mx/v1/chat/completions...[/bold blue]")
    result = test_raw_http_connection()

    if result.get("success"):
        console.print(f"[bold green][OK] Conexion exitosa! (HTTP {result.get('status_code')})[/bold green]")
        resp_json = result.get("response_json") or {}
        choices = resp_json.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            console.print(Panel(content, title="Respuesta del Modelo grok-4.6", border_style="green"))
        return True
    else:
        status = result.get("status_code")
        error = result.get("error") or result.get("response_text")
        console.print(f"[bold red][ERROR] Fallo en la llamada (HTTP {status}):[/bold red] {error}")
        return False


if __name__ == "__main__":
    success = run_diagnostics()
    sys.exit(0 if success else 1)
