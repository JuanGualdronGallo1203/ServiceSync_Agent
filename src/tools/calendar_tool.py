"""
Herramienta de agendamiento y verificación de disponibilidad en Google Calendar.
Conexión mediante Service Account de Google.
Detecta superposiciones de eventos, evita duplicados (idempotencia por cliente)
y gestiona errores estrictos para Hito S2.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from langchain_core.tools import tool

# Zona horaria operativa del taller.
# Bogotá no aplica horario de verano, por lo que el offset fijo -05:00 es exacto
# y evita depender del paquete 'tzdata' en Windows.
TIMEZONE_NAME = "America/Bogota"
TZ_BOGOTA = timezone(timedelta(hours=-5), name=TIMEZONE_NAME)

# Almacén de citas en memoria para pruebas y demostraciones locales
_MOCK_CALENDAR_EVENTS: list[dict] = []

_DATE_FORMATS = [
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M:%S",
]


def _parse_local_datetime(dt_str: str) -> datetime:
    """
    Convierte una cadena de fecha/hora en un datetime 'naive' interpretado como hora local de Bogotá.
    Ignora sufijos 'Z' u offsets enviados por el modelo para evitar desfases.
    Lanza ValueError si el formato no es reconocible.
    """
    clean_str = dt_str.strip().replace("Z", "")
    # Remover offset explícito (+HH:MM / -HH:MM) posterior a la hora, si existe
    if "T" in clean_str or " " in clean_str:
        sep = "T" if "T" in clean_str else " "
        date_part, time_part = clean_str.split(sep, 1)
        for sign in ("+", "-"):
            if sign in time_part:
                time_part = time_part.split(sign)[0]
        clean_str = f"{date_part}{sep}{time_part}"

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(clean_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Formato de fecha/hora no reconocido: '{dt_str}'")


def _to_rfc3339_with_offset(dt: datetime) -> str:
    """Formato RFC3339 con offset de Bogotá (ej. 2026-10-26T10:00:00-05:00) para timeMin/timeMax."""
    return dt.replace(tzinfo=TZ_BOGOTA).isoformat()


def _client_matches(cliente: str, summary: str) -> bool:
    """Determina si el nombre del cliente está contenido en el summary del evento (sin distinguir mayúsculas)."""
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
    Usa hora local de Bogotá (America/Bogota, UTC-05:00). Permite bloques de varias horas.
    Si ya existe una cita del mismo cliente en ese rango, no la duplica.

    Args:
        fecha_hora_inicio: Fecha y hora de inicio en hora local (ej. '2026-10-26 10:00' o '2026-10-26T10:00:00').
        fecha_hora_fin: Fecha y hora de finalización en hora local (ej. '2026-10-26 12:00'). Debe ser posterior al inicio.
        cliente: Nombre completo del cliente o propietario del vehículo.
        servicio: Nombre del servicio mecánico a realizar.
        vehiculo: Marca, modelo o placas del vehículo (opcional).
    """
    # 1. Verificación de bandera de simulación de error
    if os.getenv("SIMULATE_CALENDAR_ERROR", "false").lower() == "true":
        return "Error en Calendario: Dile al usuario que no es posible agendar digitalmente en este instante."

    # 2. Validación de entrada (errores de datos, no de infraestructura)
    try:
        start_dt = _parse_local_datetime(fecha_hora_inicio)
        end_dt = _parse_local_datetime(fecha_hora_fin)
    except ValueError:
        return (
            "Datos inválidos: no se pudo interpretar la fecha/hora. "
            "Solicita al cliente la fecha y hora en formato 'AAAA-MM-DD HH:MM'."
        )

    if end_dt <= start_dt:
        return (
            "Datos inválidos: la hora de finalización debe ser posterior a la hora de inicio. "
            "Verifica el rango horario con el cliente."
        )

    rango_legible = f"{start_dt.strftime('%Y-%m-%d %H:%M')} a {end_dt.strftime('%H:%M')} (hora Bogotá)"
    if start_dt.date() != end_dt.date():
        rango_legible = f"{start_dt.strftime('%Y-%m-%d %H:%M')} a {end_dt.strftime('%Y-%m-%d %H:%M')} (hora Bogotá)"

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

            # 3. Consulta de disponibilidad con offset explícito -05:00
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=_to_rfc3339_with_offset(start_dt),
                timeMax=_to_rfc3339_with_offset(end_dt),
                timeZone=TIMEZONE_NAME,
                singleEvents=True,
                orderBy="startTime"
            ).execute()

            items = events_result.get("items", [])

            # 4. Idempotencia: si el mismo cliente ya tiene un evento en el rango, no duplicar
            for item in items:
                summary = item.get("summary", "")
                if _client_matches(cliente, summary):
                    link = item.get("htmlLink", f"https://calendar.google.com/calendar/event?eid={item.get('id')}")
                    return (
                        f"Cita ya registrada previamente: {cliente} ya tiene una cita en Google Calendar "
                        f"en el horario {rango_legible} ('{summary}'). No se creó un duplicado. "
                        f"Enlace de la cita existente: {link}"
                    )

            # 5. Conflicto real: el horario pertenece a otro cliente
            if items:
                ocupado_por = items[0].get("summary", "Cita existente")
                return (
                    f"Conflicto de disponibilidad: El horario {rango_legible} ya se encuentra ocupado por otra cita "
                    f"en Google Calendar ('{ocupado_por}'). "
                    "Por favor solicita al cliente que elija otra fecha u hora disponible."
                )

            # 6. Inserción del evento: ISO local sin 'Z' + timeZone explícito
            event_body = {
                "summary": f"ServiceSync: {servicio} - {cliente}",
                "description": f"Servicio: {servicio}\nCliente: {cliente}\nVehículo: {vehiculo}\nAgendado por: ServiceSync Agent",
                "start": {"dateTime": start_dt.isoformat(), "timeZone": TIMEZONE_NAME},
                "end": {"dateTime": end_dt.isoformat(), "timeZone": TIMEZONE_NAME},
            }
            created_event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
            link = created_event.get("htmlLink", f"https://calendar.google.com/calendar/event?eid={created_event.get('id')}")

            return (
                f"Cita confirmada exitosamente en Google Calendar para {cliente} el {rango_legible}. "
                f"Servicio: {servicio}. Vehículo: {vehiculo}. Enlace de confirmación: {link}"
            )

        else:
            # Modo demostración y pruebas locales: replica la misma lógica de solapamiento e idempotencia
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
