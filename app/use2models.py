from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.agents.middleware import wrap_model_call, ModelRequest
from langchain.tools import tool
import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()

# ✅ Verificar que las API keys existan
openai_key = os.getenv("OPENAI_API_KEY")
google_key = os.getenv("GOOGLE_API_KEY")

if not openai_key:
    raise ValueError("❌ OPENAI_API_KEY no encontrada en .env")
if not google_key:
    raise ValueError("❌ GOOGLE_API_KEY no encontrada en .env")

# ✅ Modelo básico (OpenAI)
basic_model = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=openai_key
)

# ✅ Modelo avanzado (Gemini)
learning_model = init_chat_model(
    model="gemini-2.0-flash-exp",  # O "gemini-1.5-flash" si prefieres
    model_provider="google_genai",
    api_key=google_key,
    temperature=0.7
)

@wrap_model_call
def select_llm(request: ModelRequest, handler):
    """Selecciona modelo según contenido del mensaje."""
    
    # Obtener mensajes del state
    state_messages = request.state.get("messages", [])
    user_messages = ""
    
    # Construir string con todos los mensajes del usuario
    for msg in state_messages:
        if hasattr(msg, 'content'):
            content = str(msg.content)
            user_messages += content.lower() + " "
    
    # Lógica de selección: si menciona "know", usa básico
    if "know" in user_messages:
        request.model = basic_model
        print("🔵 Usando GPT-4o-mini (palabra clave: 'know')")
    else:
        request.model = learning_model
        print("🟢 Usando Gemini (avanzado)")
    
    return handler(request)


@tool
def recipe(food: str) -> str:
    """Return a starter instruction for generating a recipe."""
    return f"The best recipe for making {food} is: start by preparing fresh ingredients..."


# Crear agente
agent = create_agent(
    model=basic_model,  # Modelo por defecto
    tools=[recipe],
    middleware=[select_llm]
)

# ✅ TEST 1: Debería usar GPT-4o-mini (tiene "know")
print("\n" + "="*60)
print("TEST 1: Mensaje con 'know' (debería usar GPT-4o-mini)")
print("="*60)

result1 = agent.invoke({
    "messages": [
        {"role": "user", "content": "I wanna know what is the best recipe for chicken"}
    ]
})

print("\nRESPUESTA:")
print(result1["messages"][-1].content)


# ✅ TEST 2: Debería usar Gemini (NO tiene "know")
print("\n" + "="*60)
print("TEST 2: Mensaje sin 'know' (debería usar Gemini)")
print("="*60)

result2 = agent.invoke({
    "messages": [
        {"role": "user", "content": "What is the best recipe for chicken?"}
    ]
})

print("\nRESPUESTA:")
print(result2["messages"][-1].content)