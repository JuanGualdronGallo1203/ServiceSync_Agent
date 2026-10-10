"""
Definición del estado del agente para LangGraph.
Gestiona el flujo de mensajes y el contexto operativo de la conversación automotriz.
"""

from typing import Annotated, Any, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Estado global de la conversación en ServiceSync Agent.

    - messages: Secuencia de mensajes históricos y nuevos acumulados con add_messages.
    - next_step: Acción siguiente determinada por los nodos ('respond', 'end', 'error').
    - turn_count: Contador de turnos en la sesión.
    - vehicle_data: Datos técnicos del vehículo capturados durante la conversación.
    - error: Mensaje de error si ocurre alguna excepción durante la ejecución.
    """
    messages: Annotated[list[BaseMessage], add_messages]
    next_step: str
    turn_count: int
    vehicle_data: dict[str, Any]
    error: Optional[str]
