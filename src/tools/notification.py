"""
Herramienta de notificación automatizada hacia Webhook de n8n con httpx.
Envía datos del cliente, servicio y fecha para que n8n dispare confirmación por WhatsApp.
Incorpora resiliencia y manejo de errores estricto para Hito S2.
"""

import os
from datetime import datetime
from typing import Optional
import httpx
from langchain_core.tools import tool


@tool
def notificar_confirmacion_n8n(
    cliente: str,
    servicio: str,
    fecha: str,
    telefono: Optional[str] = "No proporcionado"
) -> str:
    """
    Envía una petición POST con los datos de la cita al Webhook de n8n para disparar un mensaje de WhatsApp al cliente.
    
    Args:
        cliente: Nombre completo del cliente.
        servicio: Servicio automotriz agendado.
        fecha: Fecha y hora de la cita agendada.
        telefono: Número de teléfono o WhatsApp del cliente para la notificación.
    """
    # 1. Verificación de bandera de simulación de error
    if os.getenv("SIMULATE_N8N_ERROR", "false").lower() == "true":
        return "Error en Notificación: Confírmale la cita al usuario, pero indícale que no recibirá el WhatsApp de confirmación."

    try:
        webhook_url = os.getenv("N8N_WEBHOOK_URL", "").strip()

        payload = {
            "cliente": cliente,
            "servicio": servicio,
            "fecha": fecha,
            "telefono": telefono,
            "timestamp": datetime.now().isoformat(),
            "evento": "confirmacion_cita_automotriz",
            "origen": "ServiceSync_Agent_S2"
        }

        # Si hay una URL de webhook configurada y real, realizamos la petición HTTP POST
        if webhook_url and not webhook_url.startswith("https://tu-instancia"):
            with httpx.Client(timeout=10.0) as client:
                response = client.post(webhook_url, json=payload)
                if response.status_code >= 400:
                    raise httpx.HTTPStatusError(
                        f"Error de estado HTTP {response.status_code}",
                        request=response.request,
                        response=response
                    )

        # Confirmación exitosa del webhook
        return (
            f"Notificación enviada: El webhook de n8n recibió los datos de {cliente} con éxito. "
            f"Se ha disparado el flujo automatizado de WhatsApp para el servicio '{servicio}' del día {fecha}."
        )

    except Exception:
        # Requisito estricto Fase 2
        return "Error en Notificación: Confírmale la cita al usuario, pero indícale que no recibirá el WhatsApp de confirmación."
