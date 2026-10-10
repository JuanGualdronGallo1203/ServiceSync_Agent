"""
Construcción y compilación del Grafo de Ejecución con LangGraph.
Define los nodos principales (call_model, process_state), aristas condicionales
y el gestor de memoria para conversaciones continuas.
"""

from typing import Literal
from langchain_core.messages import SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.state import AgentState
from src.llm_client import create_llm_client
from src.prompts import get_system_prompt


def call_model_node(state: AgentState) -> dict:
    """
    Nodo de Invocación del Modelo.
    Inyecta el System Prompt automotriz si no está presente e invoca al LLM (grok-4.6).
    """
    messages = list(state.get("messages", []))

    # Asegurar que el System Prompt esté al inicio
    if not messages or not isinstance(messages[0], SystemMessage):
        system_msg = SystemMessage(content=get_system_prompt())
        messages_to_send = [system_msg] + messages
    else:
        messages_to_send = messages

    llm = create_llm_client()

    try:
        response = llm.invoke(messages_to_send)
        return {
            "messages": [response],
            "error": None,
            "next_step": "process",
        }
    except Exception as exc:
        error_msg = f"Error al comunicar con Plática API (grok-4.6): {str(exc)}"
        fallback_ai_message = AIMessage(
            content=(
                "Estimado cliente, en este momento experimentamos una intermitencia de conexión "
                "con el sistema central de servicio. Por favor verifica tus credenciales o intenta de nuevo."
            )
        )
        return {
            "messages": [fallback_ai_message],
            "error": error_msg,
            "next_step": "error",
        }


def process_state_node(state: AgentState) -> dict:
    """
    Nodo de Procesamiento del Estado.
    Evalúa la respuesta generada por el modelo, actualiza métricas de turno
    y prepara la decisión de enrutamiento para una respuesta fluida.
    """
    current_turns = state.get("turn_count", 0) + 1
    error = state.get("error")

    # Si hubo error en la llamada, marcamos el paso como error
    if error:
        return {
            "turn_count": current_turns,
            "next_step": "error",
        }

    # Verificación de contenido del último mensaje
    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], AIMessage):
        content = messages[-1].content
        if not content or str(content).strip() == "":
            return {
                "turn_count": current_turns,
                "error": "El modelo devolvió una respuesta vacía.",
                "next_step": "error",
            }

    # En la fase S1, el estado se valida y se autoriza responder al usuario
    return {
        "turn_count": current_turns,
        "next_step": "respond",
        "error": None,
    }


def route_decision(state: AgentState) -> Literal["respond", "error", "end"]:
    """
    Función de enrutamiento condicional.
    Determina hacia qué nodo o fin de ejecución debe fluir el estado.
    Permite responder directamente al usuario de manera fluida en esta primera etapa.
    """
    action = state.get("next_step", "respond")
    if action == "error":
        return "error"
    elif action == "end":
        return "end"
    return "respond"


def build_service_sync_graph(enable_memory: bool = True):
    """
    Construye y compila el StateGraph de LangGraph.
    Configura los nodos principales, el flujo y las aristas condicionales.
    """
    builder = StateGraph(AgentState)

    # 1. Definición de nodos principales
    builder.add_node("call_model", call_model_node)
    builder.add_node("process_state", process_state_node)

    # 2. Definición del flujo base
    builder.add_edge(START, "call_model")
    builder.add_edge("call_model", "process_state")

    # 3. Aristas condicionales para respuesta fluida al usuario
    builder.add_conditional_edges(
        "process_state",
        route_decision,
        {
            "respond": END,
            "error": END,
            "end": END,
        },
    )

    # 4. Configuración de persistencia / memoria de conversación
    checkpointer = MemorySaver() if enable_memory else None

    return builder.compile(checkpointer=checkpointer)


# Instancia predeterminada del grafo compilado
graph_app = build_service_sync_graph(enable_memory=True)
