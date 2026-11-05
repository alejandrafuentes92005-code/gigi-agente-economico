import os
import json
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from groq import Groq, BadRequestError
import streamlit as st

from basic_memory import BasicMemory
from intermediate_tools import IntermediateTools

try:
    from supabase import create_client
    SUPABASE_DISPONIBLE = True
except ImportError:
    create_client = None
    SUPABASE_DISPONIBLE = False

# =========================
# CONFIGURACIÓN STREAMLIT (debe ir primero)
# =========================
NOME_AGENTE = "Gigi"

st.set_page_config(
    page_title=f"{NOME_AGENTE} - Agente Económico",
    page_icon="🐧",
    layout="wide"
)

# =========================
# CONFIGURACIÓN INICIAL
# =========================
load_dotenv()


def obtener_secreto(nombre, default=""):
    """Lee primero Streamlit Secrets y, si no existe, una variable de entorno (.env)."""
    try:
        valor = st.secrets.get(nombre, None)
        if valor:
            return str(valor).strip()
    except Exception:
        pass
    return (os.getenv(nombre) or default).strip()


MEMORY_MAX_MESSAGES = 10
TABLA_CONVERSACIONES = "conversaciones_gigi"

client = Groq(api_key=obtener_secreto("GROQ_API_KEY"))

now = datetime.now(ZoneInfo("America/Guatemala"))

# =========================
# SUPABASE
# =========================
@st.cache_resource
def _crear_cliente_supabase(url, key):
    # Si lanza excepción, Streamlit NO cachea el fallo y reintenta después.
    return create_client(url, key)


def init_supabase():
    """Devuelve (cliente, error). Nunca imprime la clave."""
    if not SUPABASE_DISPONIBLE:
        return None, "Falta instalar el paquete 'supabase' en requirements.txt."

    url = obtener_secreto("SUPABASE_URL").strip('"').strip("'").rstrip("/")
    for sufijo in ("/rest/v1", "/rest"):
        if url.endswith(sufijo):
            url = url[: -len(sufijo)].rstrip("/")
    key = obtener_secreto("SUPABASE_KEY").strip('"').strip("'")

    if not url or not key:
        return None, "Faltan SUPABASE_URL o SUPABASE_KEY."

    try:
        return _crear_cliente_supabase(url, key), None
    except Exception as e:
        return None, f"No se pudo crear el cliente: {e}"


supabase, error_supabase = init_supabase()


def guardar_en_supabase(pregunta, respuesta):
    if supabase is None:
        return False, error_supabase or "Supabase no conectado"
    try:
        supabase.table(TABLA_CONVERSACIONES).insert({
            "session_id": st.session_state.get("session_id"),
            "pregunta": str(pregunta),
            "respuesta": str(respuesta),
        }).execute()
        return True, None
    except Exception as e:
        print(f"❌ ERROR SUPABASE: {e}")
        return False, str(e)


# =========================
# MEMORIA Y SESIÓN
# =========================
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "memory" not in st.session_state:
    st.session_state.memory = BasicMemory(max_messages=MEMORY_MAX_MESSAGES)

memory = st.session_state.memory

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# =========================
# BARRA LATERAL (PANEL IZQUIERDO)
# =========================
with st.sidebar:
    st.title(f"🐧 {NOME_AGENTE}")
    st.caption("Tu asistente económico de confianza")
    st.divider()

    st.subheader("💡 ¿Qué puedo hacer?")
    st.write(
        "Ayudo con análisis económico, resolución de dudas, interpretación de datos "
        "macro/microeconómicos, divisas, cripto y comercio internacional."
    )
    st.divider()

    st.subheader("🛠️ Herramientas")
    st.markdown("""
    - 💱 **Tipos de cambio**
    - 🪙 **Criptomonedas**
    - 🌐 **Indicadores macro Banco Mundial**
    - 🗺️ **Información demográfica**
    - 🏛️ **Deuda pública de EE. UU.**
    - 📦 **Comercio internacional**
    """)
    st.divider()

    if st.button("🗑️ Limpiar Conversación"):
        st.session_state.chat_history = []
        st.session_state.memory = BasicMemory(max_messages=MEMORY_MAX_MESSAGES)
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    st.divider()
    if supabase:
        st.success("✅ Supabase conectado")
    else:
        st.error(f"❌ Supabase no conectado: {error_supabase}")

# =========================
# SYSTEM PROMPT Y TOOLS
# =========================
SYSTEM_PROMPT = f"""
Eres un asistente que habla en español y que interpreta los resultados que el usuario necesita, responde de manera muy breve y concisa.
Tu nombre es {NOME_AGENTE}.

Herramientas disponibles:
- consultar_tipo_cambio_api: Obtiene el tipo de cambio de una moneda.
- consultar_precio_criptomoneda: Obtiene el precio actual de criptomonedas (ej. bitcoin en usd).
- obtener_datos_economicos_world_bank: Indicadores del Banco Mundial.
- consultar_informacion_pais_countries_dev: Información general de países.
- consultar_deuda_eeuu_treasury: Deuda pública oficial de EE. UU.
- consultar_comercio_internacional_uncomtrade: Exportaciones/importaciones de Guatemala.

REGLA OBLIGATORIA: Cuando ejecutes cualquier herramienta, NO generes ningún texto explicativo ni anuncies el nombre de la herramienta. Tu salida debe consistir únicamente en la llamada a la función.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "consultar_tipo_cambio_api",
            "description": "Consulta el tipo de cambio de una moneda respecto al quetzal/USD.",
            "parameters": {
                "type": "object",
                "properties": {
                    "moneda": {"type": "string", "description": "Código de la moneda (ej. USD, EUR)"}
                },
                "required": ["moneda"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_precio_criptomoneda",
            "description": "Consulta el precio actual de una criptomoneda.",
            "parameters": {
                "type": "object",
                "properties": {
                    "criptomoneda": {"type": "string", "description": "Nombre/ID de la cripto (ej. bitcoin)"},
                    "moneda": {"type": "string", "description": "Moneda de consulta (ej. usd)"}
                },
                "required": ["criptomoneda", "moneda"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_datos_economicos_world_bank",
            "description": "Consulta indicadores del Banco Mundial.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pais": {"type": "string", "description": "Código de país (ej. GTM, USA, MEX)"},
                    "indicador": {"type": "string", "description": "Código del indicador (ej. NY.GDP.MKTP.CD)"}
                },
                "required": ["pais", "indicador"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_informacion_pais_countries_dev",
            "description": "Consulta información general de un país.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pais": {"type": "string", "description": "Código ISO de 2 o 3 letras (ej. GT, MX, US)"}
                },
                "required": ["pais"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_deuda_eeuu_treasury",
            "description": "Consulta la deuda pública de EE. UU.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fecha": {"type": "string", "description": "Fecha en formato AAAA-MM-DD"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_comercio_internacional_uncomtrade",
            "description": "Consulta datos de comercio internacional de Guatemala.",
            "parameters": {
                "type": "object",
                "properties": {
                    "anio": {"type": "integer", "description": "Año de consulta (ej. 2023)"},
                    "flujo": {"type": "string", "enum": ["exportaciones", "importaciones"]}
                },
                "required": ["anio", "flujo"]
            }
        }
    }
]

# =========================
# LÓGICA DE INTERACCIÓN Y HERRAMIENTAS
# =========================
def process_agent_response(user_text: str) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(memory.messages())
    messages.append({"role": "user", "content": user_text})

    tools_handler = IntermediateTools()

        for _ in range(6):  # máximo de rondas de herramientas
        try:
            resp = llamar_modelo(messages)
        except BadRequestError:
            return "⚠️ No pude procesar esa consulta. Intenta reformular la pregunta."

        msg = resp.choices[0].message

        if not getattr(msg, "tool_calls", None):
            return msg.content or ""

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [tc.model_dump() for tc in msg.tool_calls]
        })

        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")

            if name == "consultar_tipo_cambio_api":
                result = tools_handler.consultar_tipo_cambio_api(moneda=args.get("moneda"))
            elif name == "consultar_precio_criptomoneda":
                result = tools_handler.consultar_precio_criptomoneda(
                    criptomoneda=args.get("criptomoneda"),
                    moneda=args.get("moneda")
                )
            elif name == "obtener_datos_economicos_world_bank":
                result = tools_handler.obtener_datos_economicos_world_bank(
                    pais=args.get("pais"),
                    indicador=args.get("indicador")
                )
            elif name == "consultar_informacion_pais_countries_dev":
                result = tools_handler.consultar_informacion_pais_countries_dev(pais=args.get("pais"))
            elif name == "consultar_deuda_eeuu_treasury":
                result = tools_handler.consultar_deuda_eeuu_treasury(fecha=args.get("fecha"))
            elif name == "consultar_comercio_internacional_uncomtrade":
                result = tools_handler.consultar_comercio_internacional_uncomtrade(
                    anio=args.get("anio", 2023),
                    flujo=args.get("flujo", "exportaciones")
                )
            else:
                result = {"error": f"Herramientas desconocidas: {name}"}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False)
            })

# =========================
# INTERFAZ PRINCIPAL CON ESTILO DE TARJETAS
# =========================
st.title(f"💬 Conversación con {NOME_AGENTE} 🐧")

# Variable para capturar si se hizo clic en un botón rápido
selected_prompt = None

# Mostrar pantalla de bienvenida con tarjetas y ejemplos solo si el chat está vacío
if not st.session_state.chat_history:
    st.markdown("### ¿Qué puedo consultar por ti?")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("💱 **Mercados**\n\nTipo de cambio frente al quetzal/USD y precios de criptomonedas.")
    with col2:
        st.info("📊 **Macroeconomía**\n\nPIB, inflación, desempleo y deuda pública.")
    with col3:
        st.info("🗺️ **Países y Comercio**\n\nInformación demográfica y exportaciones/importaciones de Guatemala.")

    st.markdown("### Prueba con un ejemplo:")

    ex_col1, ex_col2 = st.columns(2)
    with ex_col1:
        if st.button("¿Cuál es el tipo de cambio del USD hoy?"):
            selected_prompt = "¿Cuál es el tipo de cambio del USD hoy?"
        if st.button("¿Cuál es el precio de bitcoin en USD?"):
            selected_prompt = "¿Cuál es el precio de bitcoin en USD?"
    with ex_col2:
        if st.button("¿Cuánto exportó Guatemala en 2023?"):
            selected_prompt = "¿Cuánto exportó Guatemala en 2023?"
        if st.button("Dame la información general de Guatemala"):
            selected_prompt = "Dame la información general de Guatemala"

    st.divider()

# Mostrar historial de chat existente
for message in st.session_state.chat_history:
    avatar_icon = "🐧" if message["role"] == "assistant" else "👤"
    with st.chat_message(message["role"], avatar=avatar_icon):
        st.markdown(message["content"])

# Entrada de usuario (por chat input o por los botones de ejemplo)
user_text = st.chat_input("Escribe tu mensaje económico aquí...")

if selected_prompt:
    user_text = selected_prompt

if user_text:
    user_text = user_text.strip()
    if user_text:
        # Mostrar mensaje del usuario
        st.session_state.chat_history.append({"role": "user", "content": user_text})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_text)

        # Procesar respuesta con Gigi
        with st.chat_message("assistant", avatar="🐧"):
            with st.spinner(f"{NOME_AGENTE} está analizando datos..."):
                assistant_text = process_agent_response(user_text)
                st.markdown(assistant_text)

        # Guardar en la memoria de la sesión
        memory.add("user", user_text)
        memory.add("assistant", assistant_text)

        # Guardar en Supabase
        ok, err = guardar_en_supabase(user_text, assistant_text)
        if ok:
            st.toast("Conversación guardada", icon="✅")
        else:
            st.warning(f"No se pudo guardar en Supabase: {err}")

        st.session_state.chat_history.append({"role": "assistant", "content": assistant_text})

        # Si vino de un botón rápido, recargamos para actualizar la interfaz
        if selected_prompt:
            st.rerun()
