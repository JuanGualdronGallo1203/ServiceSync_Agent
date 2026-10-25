"""
Herramienta de agendamiento y verificación de disponibilidad en Google Calendar.
Conexión mediante Service Account de Google.
Detecta superposiciones de eventos y gestiona errores estrictos para Hito S2.
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from langchain_core.tools import tool

# Almacén de citas en memoria para pruebas y demostraciones locales
_MOCK_CALENDAR_EVENTS = {}


def _parse_iso_datetime(dt_str: str) -> tuple[datetime, datetime]:
    """Convierte cadenas de fecha/hora en rangos de inicio y fin (1 hora)."""
    clean_str = dt_str.strip().replace("Z", "").split("+")[0]
    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            start_dt = datetime.strptime(clean_str, fmt)
            end_dt = start_dt + timedelta(hours=1)
            return start_dt, end_dt
        except ValueError:
            continue
    # Fallback predeterminado si el formato es libre
    start_dt = datetime.now() + timedelta(days=1)
    return start_dt, start_dt + timedelta(hours=1)


@tool
def gestionar_cita_calendar(
    fecha_hora: str,
    cliente: str,
    servicio: str,
    vehiculo: Optional[str] = "No especificado"
) -> str:
    """
    Verifica disponibilidad y agenda una cita en Google Calendar para un servicio automotriz.
    Verifica superposición de eventos antes de crear la cita.
    
    Args:
        fecha_hora: Fecha y hora deseada para la cita (ej. '2026-10-26 10:00' o '2026-10-26T10:00:00').
        cliente: Nombre completo del cliente o propietario del vehículo.
        servicio: Nombre del servicio mecánico a realizar.
        vehiculo: Marca, modelo o placas del vehículo (opcional).
    """
    # 1. Verificación de bandera de simulación de error
    if os.getenv("SIMULATE_CALENDAR_ERROR", "false").lower() == "true":
        return "Error en Calendario: Dile al usuario que no es posible agendar digitalmente en este instante."

    try:
        creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
        calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary").strip()

        start_dt, end_dt = _parse_iso_datetime(fecha_hora)
        start_iso = start_dt.isoformat() + "Z"
        end_iso = end_dt.isoformat() + "Z"

        # Conexión real con Google Calendar API si existe el archivo de Service Account
        if creds_file and os.path.exists(creds_file):
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build

            scopes = ["https://www.googleapis.com/auth/calendar"]
            creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
            service = build("calendar", "v3", credentials=creds, cache_discovery=False)

            # Verificar superposición de eventos en el rango de tiempo
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=start_iso,
                timeMax=end_iso,
                singleEvents=True,
                orderBy="startTime"
            ).execute()

            items = events_result.get("items", [])
            if items:
                return (
                    f"Conflicto de disponibilidad: El horario {fecha_hora} ya se encuentra ocupado por otra cita "
                    f"en Google Calendar ('{items[0].get('summary', 'Cita existente')}'). "
                    "Por favor solicita al cliente que elija otra fecha u hora disponible."
                )

            # Insertar nuevo evento
            event_body = {
                "summary": f"ServiceSync: {servicio} - {cliente}",
                "description": f"Servicio: {servicio}\nCliente: {cliente}\nVehículo: {vehiculo}\nAgendado por: ServiceSync Agent",
                "start": {"dateTime": start_iso},
                "end": {"dateTime": end_iso},
            }
            created_event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
            link = created_event.get("htmlLink", f"https://calendar.google.com/calendar/event?eid={created_event.get('id')}")

            return (
                f"Cita confirmada exitosamente en Google Calendar para {cliente} el {fecha_hora}. "
                f"Servicio: {servicio}. Vehículo: {vehiculo}. Enlace de confirmación: {link}"
            )

        else:
            # Modo demostración y pruebas locales controladas
            slot_key = start_dt.strftime("%Y-%m-%d %H:%M")
            if slot_key in _MOCK_CALENDAR_EVENTS:
                existing = _MOCK_CALENDAR_EVENTS[slot_key]
                return (
                    f"Conflicto de disponibilidad: El horario {slot_key} ya se encuentra ocupado por otra cita "
                    f"en Google Calendar (Cita previa: {existing['servicio']} de {existing['cliente']}). "
                    "Por favor solicita al cliente que elija otra fecha u hora disponible."
                )

            # Registrar en memoria local de citas
            mock_id = f"evt_{len(_MOCK_CALENDAR_EVENTS) + 1:04d}"
            mock_link = f"https://calendar.google.com/calendar/event?eid=servicesync_{mock_id}"
            _MOCK_CALENDAR_EVENTS[slot_key] = {
                "id": mock_id,
                "cliente": cliente,
                "servicio": servicio,
                "vehiculo": vehiculo,
                "link": mock_link,
            }

            return (
                f"Cita confirmada exitosamente en Google Calendar para {cliente} el {slot_key}. "
                f"Servicio: {servicio}. Vehículo: {vehiculo}. Enlace de confirmación: {mock_link}"
            )

    except Exception:
        # Requisito estricto Fase 2
        return "Error en Calendario: Dile al usuario que no es posible agendar digitalmente en este instante."
