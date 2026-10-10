"""
Cliente LLM para ServiceSync Agent.
Configura la conexión HTTP hacia el endpoint de Plática API usando LangChain ChatOpenAI y httpx.
Headers requeridos:
  - Authorization: Bearer $RETO_KEY
  - Content-Type: application/json
URL base personalizada:
  - https://api.reto.pltk.mx/v1
Modelo:
  - grok-4.6
"""

from typing import Any, Optional
import httpx
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage

from src.config import (
    RETO_KEY,
    API_BASE_URL,
    MODEL_NAME,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    get_http_headers,
    validate_config,
)


def create_llm_client(
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    extra_headers: Optional[dict[str, str]] = None,
) -> ChatOpenAI:
    """
    Inicializa la instancia del modelo ChatOpenAI configurada para Plática API.

    Garantiza:
    - Base URL personalizada: https://api.reto.pltk.mx/v1
    - Headers HTTP explícitos:
        Authorization: Bearer $RETO_KEY
        Content-Type: application/json
    - Modelo por defecto: grok-4.6
    """
    headers = get_http_headers()
    if extra_headers:
        headers.update(extra_headers)

    # LangChain ChatOpenAI compatible con OpenAI API v1
    return ChatOpenAI(
        model=MODEL_NAME,
        api_key=RETO_KEY if RETO_KEY else "unconfigured_key",
        base_url=API_BASE_URL,
        default_headers=headers,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=45.0,
        max_retries=2,
    )


def test_raw_http_connection() -> dict[str, Any]:
    """
    Realiza una comprobación HTTP directa al endpoint de Plática con httpx.
    Verifica headers, conectividad y estado del servicio.
    """
    headers = get_http_headers()
    url = f"{API_BASE_URL}/chat/completions"

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Ping de conectividad."},
            {"role": "user", "content": "Hola, confirma recepción."},
        ],
        "max_tokens": 15,
        "temperature": 0.0,
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, headers=headers, json=payload)
            return {
                "success": response.is_success,
                "status_code": response.status_code,
                "headers_sent": {
                    "Authorization": "Bearer " + ("*" * 8 if RETO_KEY else "MISSING"),
                    "Content-Type": headers.get("Content-Type"),
                },
                "endpoint": url,
                "model": MODEL_NAME,
                "response_json": response.json() if response.headers.get("content-type", "").startswith("application/json") else None,
                "response_text": response.text if not response.is_success else None,
            }
    except Exception as exc:
        return {
            "success": False,
            "status_code": None,
            "error": str(exc),
            "endpoint": url,
            "model": MODEL_NAME,
        }
