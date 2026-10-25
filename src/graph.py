"""
Construcción y compilación del Grafo de Ejecución con LangGraph (Hito S2).
Integra ToolNode con herramientas reales (@tool), enlace dinámico (bind_tools) a grok-4.6,
orquestación multi-herramienta con ciclo de retroalimentación y memoria conversacional.
"""

from typing import Literal
from langchain_core.messages import SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from src.state import AgentState
from src.llm_client import create_llm_client
from src.prompts import get_system_prompt
from src.tools import ALL_TOOLS


def call_model_node(state: AgentState) -> dict:
    """
    Nodo de Invocación del Modelo.
    Inyecta el System Prompt automotriz, enlaza las herramientas (bind_tools)
    e invoca al LLM grok-4.6 a través del gateway de Plática.
    """
    messages = list(state.get("messages", []))

    # Asegurar que el System Prompt esté al inicio del contexto
    if not messages or not isinstance(messages[0], SystemMessage):
        system_msg = SystemMessage(content=get_system_prompt())
        messages_to_send = [system_msg] + messages
    else:
        messages_to_send = messages

    # Inicializar cliente LLM y enlazar las 3 herramientas reales (@tool)
    llm = create_llm_client()
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    try:
        response = llm_with_tools.invoke(messages_to_send)
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


def should_continue(state: AgentState) -> Literal["tools", "process_state"]:
    """
    Evalúa si el último mensaje del modelo contiene llamadas a herramientas (tool_calls).
    Si hay llamadas pendientes, transfiere el flujo a 'tools'. De lo contrario, avanza a 'process_state'.
    """
    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
        return "tools"
    return "process_state"


def process_state_node(state: AgentState) -> dict:
    """
    Nodo de Procesamiento del Estado.
    Evalúa la respuesta generada por el modelo una vez completadas las herramientas,
    actualiza métricas de turno y prepara la decisión de enrutamiento.
    """
    current_turns = state.get("turn_count", 0) + 1
    error = state.get("error")

    if error:
        return {
            "turn_count": current_turns,
            "next_step": "error",
        }

    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], AIMessage):
        content = messages[-1].content
        if not content or str(content).strip() == "":
            return {
                "turn_count": current_turns,
                "error": "El modelo devolvió una respuesta vacía tras la ejecución.",
                "next_step": "error",
            }

    return {
        "turn_count": current_turns,
        "next_step": "respond",
        "error": None,
    }


def route_decision(state: AgentState) -> Literal["respond", "error", "end"]:
    """
    Enrutamiento condicional final hacia el usuario.
    """
    action = state.get("next_step", "respond")
    if action == "error":
        return "error"
    elif action == "end":
        return "end"
    return "respond"


def build_service_sync_graph(enable_memory: bool = True):
    """
    Construye y compila el StateGraph de LangGraph para Hito S2.
    Flujo:
      START -> call_model -> [¿Hay tool_calls?]
                                  |-- Si --> tools -> call_model (ciclo de retroalimentación)
                                  |-- No --> process_state -> route_decision -> END
    """
    builder = StateGraph(AgentState)

    # 1. Nodos de ejecución
    builder.add_node("call_model", call_model_node)
    builder.add_node("tools", ToolNode(ALL_TOOLS))
    builder.add_node("process_state", process_state_node)

    # 2. Flujo inicial
    builder.add_edge(START, "call_model")

    # 3. Arista condicional: bifurcación hacia herramientas o procesamiento final
    builder.add_conditional_edges(
        "call_model",
        should_continue,
        {
            "tools": "tools",
            "process_state": "process_state",
        },
    )

    # 4. Ciclo de retorno desde ToolNode hacia el modelo para sintetizar la respuesta
    builder.add_edge("tools", "call_model")

    # 5. Salida condicional hacia el usuario
    builder.add_conditional_edges(
        "process_state",
        route_decision,
        {
            "respond": END,
            "error": END,
            "end": END,
        },
    )

    # 6. Memoria conversacional aislada por thread_id
    checkpointer = MemorySaver() if enable_memory else None

    return builder.compile(checkpointer=checkpointer)


# Instancia por defecto del grafo compilado
graph_app = build_service_sync_graph(enable_memory=True)
