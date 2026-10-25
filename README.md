# 🚗 ServiceSync Agent (Hitos S1 y S2)

> **Asistente operativo automotriz inteligente para triaje de servicio, cotizaciones en tiempo real, agendamiento de citas y atención al cliente, impulsado por LangGraph, grok-4.6 y herramientas reales (Supabase, Google Calendar y n8n).**

---

## 📋 Tabla de Contenidos
1. [Descripción del Problema que Resuelve](#-descripción-del-problema-que-resuelve)
2. [Arquitectura Técnica](#-arquitectura-técnica)
   - [Grafo de Ejecución Multi-Herramienta (LangGraph)](#grafo-de-ejecución-multi-herramienta-langgraph)
   - [Herramientas Reales Integradas (@tool)](#herramientas-reales-integradas-tool)
   - [Capa de Resiliencia y Manejo de Errores](#capa-de-resiliencia-y-manejo-de-errores)
   - [Gestión de Estado y Memoria Conversacional](#gestión-de-estado-y-memoria-conversacional)
   - [Conexión con Plática API y Headers HTTP](#conexión-con-plática-api-y-headers-http)
3. [Estructura del Proyecto](#-estructura-del-proyecto)
4. [Prerrequisitos](#-prerrequisitos)
5. [Instrucciones de Instalación y Configuración](#-instrucciones-de-instalación-y-configuración)
6. [Guía de Ejecución y Pruebas](#-guía-de-ejecución-y-pruebas)
   - [Suite de 10 Ejecuciones Comprobables (Hito S2)](#1-suite-de-10-ejecuciones-comprobables-hito-s2)
   - [Diagnóstico de Conectividad HTTP](#2-diagnóstico-de-conectividad-http)
   - [CLI Interactivo de Conversación Continua](#3-cli-interactivo-de-conversación-continua)
   - [Simulación End-to-End Automatizada](#4-simulación-end-to-end-automatizada)
   - [Pruebas Unitarias de Componentes y Herramientas](#5-pruebas-unitarias-de-componentes-y-herramientas)
7. [Políticas y Reglas del Sistema](#-políticas-y-reglas-del-sistema)

---

## 🎯 Descripción del Problema que Resuelve

En la industria automotriz y en los talleres de servicio mecánico, la etapa inicial de recepción y atención al cliente presenta desafíos operativos recurrentes:
1. **Pérdida de tiempo en triaje:** Los asesores dedican tiempo excesivo recopilando datos básicos del automóvil (marca, modelo, año, kilometraje) y síntomas dispersos antes de generar una orden de servicio.
2. **Alucinaciones financieras (precios inventados):** Los modelos de lenguaje convencionales tienden a fabricar tarifas o precios fijos si no cuentan con un anclaje a base de datos.
3. **Agendamiento ciego:** Errores al reservar citas sin validar disponibilidad en tiempo real o colisiones de horarios.
4. **Falta de confirmación multicanal:** Pérdida de citas por ausencia de notificaciones automáticas por WhatsApp al cliente.
5. **Desatención de emergencias mecánicas:** Falta de protocolos para identificar fallas críticas inmediatas (falla de frenos, pedal esponjoso, alertas de temperatura o baja presión de aceite).

**ServiceSync Agent** resuelve estos problemas actuando como el **primer filtro operativo**:
- **Cotizaciones vivas en tiempo real:** Consulta Supabase (tabla `servicios`: id, nombre, precio_base, tiempo_estimado).
- **Agendamiento inteligente:** Verifica colisiones y crea eventos en Google Calendar mediante Service Account.
- **Notificación por WhatsApp:** Dispara Webhooks en n8n para confirmar la cita al usuario.
- **Resiliencia extrema:** Capa de `try/except` que orienta al usuario ante cualquier caída de servicios externos.
- **Seguridad mecánica prioritaria:** Protocolo de emergencia que ordena detener el vehículo si detecta fallas críticas.

---

## 🏗 Arquitectura Técnica

### Grafo de Ejecución Multi-Herramienta (LangGraph)

El flujo de control de ServiceSync Agent está modelado como un grafo de estados (`StateGraph`) con ciclo cerrado de retroalimentación de herramientas (`ToolNode`):

```mermaid
graph TD
    START([START: Inicio de Petición]) --> call_model[Nodo: call_model<br/>System Prompt + grok-4.6 + bind_tools]
    call_model --> should_continue{¿Hay tool_calls?}
    should_continue -->|tools| tools_node[Nodo: tools / ToolNode<br/>Supabase | Google Calendar | n8n]
    tools_node -->|ToolMessage con salida/error| call_model
    should_continue -->|process_state| process_state[Nodo: process_state<br/>Validación de Respuesta + Métricas de Turno]
    process_state --> route_decision{Arista Condicional<br/>route_decision}
    route_decision -->|respond| END([END: Respuesta al Usuario])
    route_decision -->|error| END([END: Manejo Seguro de Error])
    route_decision -->|end| END([END: Cierre de Sesión])
```

### Herramientas Reales Integradas (@tool)

1. **`consultar_inventario_supabase` (`src/tools/inventory.py`):**
   - Conexión con Supabase Python SDK.
   - Consulta tabla `servicios` con campos: `id`, `nombre`, `precio_base`, `tiempo_estimado`.
   - Proporciona cotizaciones exactas y tiempos operativos.

2. **`gestionar_cita_calendar` (`src/tools/calendar_tool.py`):**
   - Conexión con Google Calendar API mediante Service Account.
   - Parámetros dinámicos `fecha_hora_inicio` y `fecha_hora_fin` con soporte para bloques multihorarios.
   - Zona horaria explícita `America/Bogota` (UTC-05:00) en eventos y offsets `timeMin`/`timeMax`.
   - Detección inteligente de duplicados (idempotencia por cliente en el `summary`) y prevención de colisiones con otros clientes.

3. **`notificar_confirmacion_n8n` (`src/tools/notification.py`):**
   - Envío de payload JSON mediante `httpx` hacia el Webhook de n8n.
   - Dispara flujo de confirmación por WhatsApp con los datos del cliente, servicio y fecha.

### Capa de Resiliencia y Manejo de Errores

Cada herramienta envuelve sus llamadas externas en bloques `try/except` retornando directivas estrictas de contingencia:
- **Fallo en Supabase:** Retorna `"Error en BD: Indica al usuario que los sistemas de precios están en mantenimiento, pero invítalo al taller."`
- **Fallo en Google Calendar:** Retorna `"Error en Calendario: Dile al usuario que no es posible agendar digitalmente en este instante."`
- **Fallo en n8n:** Retorna `"Error en Notificación: Confírmale la cita al usuario, pero indícale que no recibirá el WhatsApp de confirmación."`

### Gestión de Estado y Memoria Conversacional

El estado global está tipado mediante `AgentState` (`TypedDict`):

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    next_step: str
    turn_count: int
    vehicle_data: dict[str, Any]
    error: Optional[str]
```

- **`messages` con `add_messages`:** Gestiona el historial acumulado de `HumanMessage` y `AIMessage`.
- **`MemorySaver` Checkpointer:** Cada conversación se indexa mediante un `thread_id` único. Cuando el usuario envía múltiples mensajes de seguimiento, LangGraph recupera el estado previo y preserva la memoria de los datos del vehículo.

### Conexión con Plática API y Headers HTTP

La integración utiliza la interfaz de compatibilidad OpenAI v1 de LangChain (`ChatOpenAI`), apuntando directamente al endpoint asignado:

- **Base URL:** `https://api.reto.pltk.mx/v1`
- **Modelo:** `grok-4.6`
- **Headers HTTP Requeridos:**
  ```http
  Authorization: Bearer $RETO_KEY
  Content-Type: application/json
  ```

### Mitigación Estricta de Alucinaciones

El sistema incorpora tres barreras para impedir alucinaciones:
1. **Catálogo Oficial Anclado (`src/catalog.py`):** Define el alcance exhaustivo de los servicios permitidos (mantenimiento preventivo, frenos, alineación/balanceo, diagnóstico OBD-II, sistema de refrigeración) y una lista explícita de servicios no soportados.
2. **Regla de Oro Anti-precios y Cotizaciones Reales:** NUNCA se inventan costos numéricos. Los precios provienen estrictamente de la consulta en tiempo real a Supabase (`consultar_inventario_supabase`). Si el servicio de base de datos no está disponible, se activa la política de contingencia informando que los sistemas están en mantenimiento e invitando al cliente al taller.
3. **Regla Fundamental en System Prompt (`src/prompts.py`):**
   > *"No inventes precios ni servicios que no estén en tu contexto base ni hayan sido devueltos por tus herramientas."*

---

## 📂 Estructura del Proyecto

```text
ServiceSync_Agent/
├── .env                     # Archivo de variables secretas (IGNORADO por git)
├── .env.example             # Plantilla de variables de entorno para despliegue
├── .gitignore               # Configuración estricta de exclusión (.env, .venv, etc.)
├── requirements.txt         # Dependencias reproducibles del proyecto
├── README.md                # Documentación técnica completa (Hitos S1 y S2)
├── run_executions.py        # Suite de 10 ejecuciones comprobables de Hito S2
├── executions_S2.log        # Registro de auditoría persistente de las 10 ejecuciones
├── test_connection.py       # Script de diagnóstico de conectividad HTTP a Plática
├── cli.py                   # CLI interactivo con herramientas reales y memoria continua
├── src/
│   ├── __init__.py          # Inicializador del paquete
│   ├── config.py            # Carga de .env, headers HTTP y validaciones
│   ├── catalog.py           # Catálogo oficial de servicios automotrices (Ground Truth)
│   ├── prompts.py           # System Prompt operativo, herramientas y reglas anti-alucinación
│   ├── state.py             # Definición del esquema AgentState de LangGraph
│   ├── llm_client.py        # Configuración del cliente ChatOpenAI y llamadas HTTP
│   ├── graph.py             # StateGraph de LangGraph con ToolNode y MemorySaver
│   └── tools/               # Herramientas reales integradas (@tool)
│       ├── __init__.py      # Registro centralizado ALL_TOOLS
│       ├── inventory.py     # consultar_inventario_supabase (Precios y cotizaciones en BD)
│       ├── calendar_tool.py # gestionar_cita_calendar (Agendamiento y colisiones en Google Calendar)
│       └── notification.py  # notificar_confirmacion_n8n (Webhook n8n para confirmación WhatsApp)
├── supabase/                # Configuración de base de datos y migraciones locales
└── tests/
    ├── __init__.py
    ├── test_components.py   # Pruebas unitarias de componentes, prompts y grafo
    ├── test_tools_s2.py     # Pruebas unitarias de herramientas, colisiones y resiliencia S2
    └── test_simulation.py   # Simulación conversacional End-to-End automatizada
```

---

## ⚙️ Prerrequisitos

- **Python:** Versión `3.10` o superior (validado en `Python 3.13.7`).
- **Git:** Para control de versiones.
- **Plática API Key (`RETO_KEY`):** Llave de autenticación provista para el reto.

---

## 🚀 Instrucciones de Instalación y Configuración

### 1. Clonar el Repositorio
```bash
git clone https://github.com/JuanGualdronGallo1203/ServiceSync_Agent.git
cd ServiceSync_Agent
```

### 2. Crear y Activar el Entorno Virtual

**En Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**En Linux / macOS (Bash):**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar Dependencias
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar las Variables de Entorno

Copia el archivo de plantilla `.env.example` para generar tu archivo `.env`:

**En Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**En Linux / macOS:**
```bash
cp .env.example .env
```

Abre el archivo `.env` con tu editor y coloca tu llave:
```ini
# Configuración del Reto Plática API
RETO_KEY=tu_token_real_aqui
```

> 🔒 **Seguridad Garantizada:** El archivo `.gitignore` excluye estrictamente `.env`, garantizando que tu credencial nunca se exponga ni se suba a repositorios remotos.

---

## 🧪 Guía de Ejecución y Pruebas

### 1. Suite de 10 Ejecuciones Comprobables (Hito S2)
Ejecuta la suite automatizada de 10 escenarios que prueban cotizaciones en Supabase, agendamientos en Google Calendar, confirmaciones por WhatsApp vía n8n, manejo de colisiones horarias y resiliencia ante caídas:

```bash
python run_executions.py
```

- Salida enriquecida con `rich` en terminal (ideal para grabación del video demostrativo).
- Genera el reporte de auditoría persistente en **`executions_S2.log`**.

---

### 2. Diagnóstico de Conectividad HTTP
Valida que la URL base, los headers y la `RETO_KEY` estén listos y verificados:

```bash
python test_connection.py
```

*Salida esperada:*
```text
┌──────────────────────────────────────────────────────────────┐
│ ServiceSync Agent - Diagnostico de Conexion HTTP Platica API │
└──────────────────────────────────────────────────────────────┘
                      1. Configuracion de Entorno                       
┌─────────────────┬─────────────────────────────┬──────────────┐
│ Parametro       │ Valor Actual                │ Estado       │
├─────────────────┼─────────────────────────────┼──────────────┤
│ API Base URL    │ https://api.reto.pltk.mx/v1 │ [OK]         │
│ Modelo Objetivo │ grok-4.6                    │ [OK]         │
│ RETO_KEY        │ abc12...999                 │ [CONFIGURADA]│
└─────────────────┴─────────────────────────────┴──────────────┘
       2. Headers HTTP Requeridos       
┌───────────────┬──────────────────────┐
│ Header        │ Valor de Envio       │
├───────────────┼──────────────────────┤
│ Authorization │ Bearer abc12...999   │
│ Content-Type  │ application/json     │
└───────────────┴──────────────────────┘
[OK] Conexion exitosa! (HTTP 200)
```

---

### 2. CLI Interactivo de Conversación Continua
Ejecuta la terminal interactiva para conversar de forma fluida con el agente:

```bash
python cli.py
```

#### Comandos Disponibles dentro del CLI:
| Comando | Descripción |
| :--- | :--- |
| `/help` | Despliega el menú de ayuda y comandos interactivos. |
| `/history` | Inspecciona todos los mensajes almacenados en la memoria activa del `thread_id`. |
| `/status` | Muestra el estado del modelo (`grok-4.6`), endpoint y sesión. |
| `/reset` o `/new` | Reinicia la memoria e inicia un nuevo hilo de conversación. |
| `/exit` o `/quit` | Finaliza la sesión de la terminal. |

---

### 3. Simulación End-to-End Automatizada
Ejecuta un flujo de 4 turnos consecutivos que evalúan el triaje, la memoria persistente de datos del vehículo y las políticas anti-alucinación:

```bash
python tests/test_simulation.py
```

*Escenarios evaluados en la simulación:*
1. **Turno 1:** Saludo y captura de vehículo (*"Honda Civic 2019 con 65,000 km"*).
2. **Turno 2:** Consulta de precio de cambio de aceite -> Comprueba retención del modelo y rechazo de precios inventados.
3. **Turno 3:** Consulta de servicio no soportado (*"Blindaje nivel 4"* -> Rechazo amable basado en catálogo).
4. **Turno 4:** Alerta crítica de frenos -> Alerta de seguridad preventiva.

---

### 4. Pruebas Unitarias de Componentes
Ejecuta la suite formal de pruebas unitarias (`unittest`):

```bash
python -m unittest tests/test_components.py
```

*Verifica:*
- Integridad de endpoints (`https://api.reto.pltk.mx/v1`), modelo (`grok-4.6`) y headers.
- Estructura del catálogo oficial y exclusiones.
- Presencia de directrices operativas y reglas anti-alucinación en el System Prompt.
- Estructura del grafo de LangGraph (`call_model`, `process_state`, aristas condicionales).
- Funcionamiento del nodo de procesamiento de estado y la función de enrutamiento.

---

## 🛡 Políticas y Reglas del Sistema

| Dimensión | Regla Implementada |
| :--- | :--- |
| **Rol y Tono** | Asistente de recepción automotriz amable, técnico pero directo y sin divagaciones. |
| **Anti-Alucinación (Precios)** | Prohibición absoluta de inventar cifras. Explicación de variables y derivación a cotización formal. |
| **Anti-Alucinación (Servicios)** | Estricta adhesión a los servicios contemplados en `AUTOMOTIVE_SERVICES_CATALOG`. |
| **Seguridad Vial** | Prioridad inmediata de advertencia mecánica ante anomalías de frenos o sobrecalentamiento. |
| **Memoria** | Persistencia nativa por hilos mediante el checkpointer `MemorySaver` de LangGraph. |

---

## 👨‍💻 Autor y Contacto
- **Desarrollador:** Juan Sebastián Gualdrón Gallo
- **Proyecto:** ServiceSync Agent - Hitos S1 y S2
- **Plataforma:** LangGraph + Plática API (Reto 2026)