"""
Configuración centralizada para ServiceSync Agent (Hitos S1 y S2).
Maneja variables de entorno, credenciales y parámetros de conexión hacia:
- Plática API (grok-4.6)
- Supabase (Inventario y cotizaciones en tiempo real)
- Google Calendar (Service Account para agendamiento de citas)
- n8n (Webhook para notificaciones automáticas por WhatsApp)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Ubicación base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Carga segura del archivo .env
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE)
else:
    load_dotenv()

# Parámetros del servicio LLM (Plática API)
RETO_KEY = os.getenv("RETO_KEY", "").strip()
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.reto.pltk.mx/v1").rstrip("/")
MODEL_NAME = os.getenv("MODEL_NAME", "grok-4.6")

# Parámetros operativos del modelo
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.2"))
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "1024"))

# Parámetros Supabase (Hito S2)
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

# Parámetros Google Calendar API (Hito S2)
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary").strip()

# Parámetros n8n Webhook (Hito S2)
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "").strip()

# Banderas de simulación para pruebas de resiliencia y errores
SIMULATE_SUPABASE_ERROR = os.getenv("SIMULATE_SUPABASE_ERROR", "false").lower() == "true"
SIMULATE_CALENDAR_ERROR = os.getenv("SIMULATE_CALENDAR_ERROR", "false").lower() == "true"
SIMULATE_N8N_ERROR = os.getenv("SIMULATE_N8N_ERROR", "false").lower() == "true"


def get_http_headers() -> dict[str, str]:
    """
    Retorna los headers HTTP requeridos para las peticiones a la API de Plática.
    Incluye Authorization: Bearer $RETO_KEY y Content-Type: application/json.
    """
    return {
        "Authorization": f"Bearer {RETO_KEY}",
        "Content-Type": "application/json",
    }


def validate_config(raise_on_error: bool = False) -> tuple[bool, str]:
    """
    Valida que la configuración esencial esté presente y sea válida.
    """
    if not RETO_KEY or RETO_KEY == "tu_clave_de_platica_aqui":
        msg = (
            "La variable 'RETO_KEY' no está configurada o contiene el valor por defecto. "
            "Por favor edita el archivo .env e introduce tu clave de acceso de Plática."
        )
        if raise_on_error:
            raise ValueError(msg)
        return False, msg

    return True, "Configuración validada exitosamente."
