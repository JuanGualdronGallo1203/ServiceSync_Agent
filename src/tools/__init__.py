"""
Módulo de herramientas reales para ServiceSync Agent (Hito S2).
Integra Supabase (inventario/precios), Google Calendar (citas) y n8n (notificaciones WhatsApp).
"""

from src.tools.inventory import consultar_inventario_supabase
from src.tools.calendar_tool import gestionar_cita_calendar
from src.tools.notification import notificar_confirmacion_n8n

ALL_TOOLS = [
    consultar_inventario_supabase,
    gestionar_cita_calendar,
    notificar_confirmacion_n8n,
]

__all__ = [
    "consultar_inventario_supabase",
    "gestionar_cita_calendar",
    "notificar_confirmacion_n8n",
    "ALL_TOOLS",
]
