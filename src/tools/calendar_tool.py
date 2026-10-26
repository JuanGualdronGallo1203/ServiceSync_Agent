"""
Herramienta de agendamiento y verificación de disponibilidad en Google Calendar.
Conexión mediante Service Account de Google.
Garantiza:
1. Parámetros obligatorios fecha_hora_inicio y fecha_hora_fin (sin valores por defecto).
2. Limpieza estricta de cualquier rastro de UTC (Z, offsets) para manejar datetimes ingenuos (naive).
3. Inyección en Google Calendar con formato ISO (%Y-%m-%dT%H:%M:%S) y timeZone "America/Bogota".
4. Detección inteligente de duplicados (idempotencia por cliente) y detección de conflictos.
"""

import os
import re
from datetime import datetime
from typing import Optional
from langchain_core.tools import tool

TIMEZONE_NAME = "America/Bogota"

# Almacén de citas en memoria para pruebas y demostraciones locales cuando no hay credenciales
_MOCK_CALENDAR_EVENTS: list[dict] = []

_DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
]


def _parse_local_datetime(dt_str: str) -> datetime:
    """
    Limpia forzosamente cualquier información de zona horaria ('Z', '+00:00', '-05:00', etc.)
    y retorna un objeto datetime estrictamente ingenuo (naive).
    Esto garantiza que las 17:00 enviadas por el usuario se interpreten como 17:00 ingenuas,
    evitando que Python o Google resten 5 horas asumiéndolas como UTC.
    """
    clean_str = str(dt_str).strip()

    # 1. Quitar 'Z' o 'z' al final
    clean_str = re.sub(r"[zZ]$", "", clean_str)

    # 2. Quitar offsets numéricos al final (+HH:MM, -HH:MM, +HHMM, -HHMM)
    clean_str = re.sub(r"([+-]\d{2}:?\d{2})$", "", clean_str)

    # 3. Quitar fracciones de segundo (.000, .123456)
    clean_str = re.sub(r"\.\d+", "", clean_str)

    clean_str = clean_str.strip()

    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(clean_str, fmt)
            return dt.replace(tzinfo=None)
        except ValueError:
            continue

    raise ValueError(f"Formato de fecha/hora no reconocido: '{dt_str}'")


def _client_matches(cliente: str, summary: str) -> bool:
    """Determina si el nombre del cliente está contenido en el summary del evento (case-insensitive)."""
    return bool(cliente.strip()) and cliente.strip().lower() in (summary or "").lower()


@tool
def gestionar_cita_calendar(
    fecha_hora_inicio: str,
    fecha_hora_fin: str,
    cliente: str,
    servicio: str,
    vehiculo: Optional[str] = "No especificado"
) -> str:
    """
    Verifica disponibilidad y agenda una cita en Google Calendar para un servicio automotriz.
    
    IMPORTANTE: 'fecha_hora_inicio' y 'fecha_hora_fin' son AMBAS OBLIGATORIAS.
    Debes enviar ambas en hora local de Colombia (America/Bogota), formato 'YYYY-MM-DDTHH:MM:SS'
    o 'YYYY-MM-DD HH:MM'. NUNCA agregues 'Z' ni conviertas a UTC.
    Si el cliente no especifica la hora de fin, calcula 'fecha_hora_fin' sumando la duración
    estimada del servicio (obtenida de Supabase) o 1 hora por defecto.

    Args:
        fecha_hora_inicio: Fecha y hora de inicio de la cita en hora local de Colombia (ej. '2026-10-26T10:00:00' o '2026-10-26 10:00').
        fecha_hora_fin: Fecha y hora de finalización de la cita en hora local de Colombia (ej. '2026-10-26T11:30:00' o '2026-10-26 11:30').
        cliente: Nombre completo del cliente o propietario del vehículo.
        servicio: Nombre del servicio mecánico a realizar.
        vehiculo: Marca, modelo o placas del vehículo (opcional).
    """
    # 1. Verificación de bandera de simulación de error
    if os.getenv("SIMULATE_CALENDAR_ERROR", "false").lower() == "true":
        return "Error en Calendario: Dile al usuario que no es posible agendar digitalmente en este instante."

    # 2. Validación y limpieza estricta a datetime ingenuo (naive)
    try:
        start_dt = _parse_local_datetime(fecha_hora_inicio)
        end_dt = _parse_local_datetime(fecha_hora_fin)
    except ValueError:
        return (
            "Datos inválidos: no se pudo interpretar la fecha/hora. "
            "Debes proporcionar 'fecha_hora_inicio' y 'fecha_hora_fin' en formato 'AAAA-MM-DD HH:MM'."
        )

    if end_dt <= start_dt:
        return (
            "Datos inválidos: la hora de finalización debe ser posterior a la hora de inicio. "
            "Verifica el rango horario de la cita."
        )

    # Formatos string ingenuos exactos (sin 'Z') para Google Calendar
    start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
    end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

    rango_legible = f"{start_dt.strftime('%Y-%m-%d %H:%M')} a {end_dt.strftime('%H:%M')} (hora Colombia)"
    if start_dt.date() != end_dt.date():
        rango_legible = f"{start_dt.strftime('%Y-%m-%d %H:%M')} a {end_dt.strftime('%Y-%m-%d %H:%M')} (hora Colombia)"

    try:
        creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
        calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary").strip()

        # Conexión real con Google Calendar API si existe el archivo de Service Account
        if creds_file and os.path.exists(creds_file):
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build

            scopes = ["https://www.googleapis.com/auth/calendar"]
            creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
            service = build("calendar", "v3", credentials=creds, cache_discovery=False)

            # Consulta de disponibilidad con offset explícito de Bogotá (-05:00)
            time_min_str = f"{start_iso}-05:00"
            time_max_str = f"{end_iso}-05:00"

            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min_str,
                timeMax=time_max_str,
                timeZone=TIMEZONE_NAME,
                singleEvents=True,
                orderBy="startTime"
            ).execute()

            items = events_result.get("items", [])

            # Idempotencia: si el mismo cliente ya tiene un evento en este rango, no duplicar
            for item in items:
                summary = item.get("summary", "")
                if _client_matches(cliente, summary):
                    link = item.get("htmlLink", f"https://calendar.google.com/calendar/event?eid={item.get('id')}")
                    return (
                        f"Cita ya registrada previamente: {cliente} ya tiene una cita en Google Calendar "
                        f"en el horario {rango_legible} ('{summary}'). No se creó un duplicado. "
                        f"Enlace de la cita existente: {link}"
                    )

            # Conflicto real: el horario está ocupado por otro cliente
            if items:
                ocupado_por = items[0].get("summary", "Cita existente")
                return (
                    f"Conflicto de disponibilidad: El horario {rango_legible} ya se encuentra ocupado por otra cita "
                    f"en Google Calendar ('{ocupado_por}'). "
                    "Por favor solicita al cliente que elija otra fecha u hora disponible."
                )

            # Inserción con datetime ingenuo en string ISO y timeZone explícito America/Bogota
            event_body = {
                "summary": f"ServiceSync: {servicio} - {cliente}",
                "description": f"Servicio: {servicio}\nCliente: {cliente}\nVehículo: {vehiculo}\nAgendado por: ServiceSync Agent",
                "start": {
                    "dateTime": start_iso,
                    "timeZone": TIMEZONE_NAME
                },
                "end": {
                    "dateTime": end_iso,
                    "timeZone": TIMEZONE_NAME
                },
            }
            created_event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
            link = created_event.get("htmlLink", f"https://calendar.google.com/calendar/event?eid={created_event.get('id')}")

            return (
                f"Cita confirmada exitosamente en Google Calendar para {cliente} el {rango_legible}. "
                f"Servicio: {servicio}. Vehículo: {vehiculo}. Enlace de confirmación: {link}"
            )

        else:
            # Modo demostración y pruebas locales en memoria
            overlapping = [
                evt for evt in _MOCK_CALENDAR_EVENTS
                if evt["start"] < end_dt and start_dt < evt["end"]
            ]

            for evt in overlapping:
                if _client_matches(cliente, evt["summary"]):
                    return (
                        f"Cita ya registrada previamente: {cliente} ya tiene una cita en Google Calendar "
                        f"en el horario {rango_legible} ('{evt['summary']}'). No se creó un duplicado. "
                        f"Enlace de la cita existente: {evt['link']}"
                    )

            if overlapping:
                existing = overlapping[0]
                return (
                    f"Conflicto de disponibilidad: El horario {rango_legible} ya se encuentra ocupado por otra cita "
                    f"en Google Calendar (Cita previa: {existing['servicio']} de {existing['cliente']}). "
                    "Por favor solicita al cliente que elija otra fecha u hora disponible."
                )

            mock_id = f"evt_{len(_MOCK_CALENDAR_EVENTS) + 1:04d}"
            mock_link = f"https://calendar.google.com/calendar/event?eid=servicesync_{mock_id}"
            _MOCK_CALENDAR_EVENTS.append({
                "id": mock_id,
                "summary": f"ServiceSync: {servicio} - {cliente}",
                "cliente": cliente,
                "servicio": servicio,
                "vehiculo": vehiculo,
                "start": start_dt,
                "end": end_dt,
                "link": mock_link,
            })

            return (
                f"Cita confirmada exitosamente en Google Calendar para {cliente} el {rango_legible}. "
                f"Servicio: {servicio}. Vehículo: {vehiculo}. Enlace de confirmación: {mock_link}"
            )

    except Exception:
        # Requisito estricto Fase 2
        return "Error en Calendario: Dile al usuario que no es posible agendar digitalmente en este instante."
