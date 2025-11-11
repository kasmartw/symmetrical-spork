# joke_bot.py
import os
import re
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Cargar variables de entorno
load_dotenv()

def check_langsmith_config():
    """Verifica si LangSmith está configurado correctamente."""
    langsmith_key = os.getenv("LANGCHAIN_API_KEY")
    tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2")
    
    if langsmith_key and tracing_enabled == "true":
        print("✅ LangSmith tracing ACTIVADO")
        print(f"📊 Proyecto: {os.getenv('LANGCHAIN_PROJECT', 'default')}")
        return True
    else:
        print("⚠️  LangSmith NO configurado (ejecutando sin tracing)")
        return False

# ============================================
# STATE DEFINITION
# ============================================
class State(TypedDict):
    messages: Annotated[list, add_messages]
    topic: str | None
    num_jokes: int | None
    jokes: list[str]
    error: str | None

# ============================================
# FUNCTION TO GENERATE JOKE
# ============================================
def generate_single_joke(topic: str) -> str:
    """Generate one joke about a specific topic."""
    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=1.0
        )
        
        prompt = f"""Generate ONE short, funny joke specifically about: {topic}

IMPORTANT: The joke MUST be related to the topic "{topic}".

Requirements:
- Family-friendly
- Original and creative
- 2-3 sentences max
- Actually funny!

Joke about {topic}:"""
        
        response = llm.invoke(prompt)
        return response.content.strip()
    
    except Exception as e:
        return f"Error: {str(e)}"

# ============================================
# VALIDATION FUNCTIONS
# ============================================
def is_valid_topic(text: str) -> bool:
    """Check if topic is valid (not random characters)."""
    # At least 3 characters
    if len(text.strip()) < 3:
        return False
    
    # Should contain mostly letters (allow spaces and some punctuation)
    cleaned = text.replace(" ", "")
    if not cleaned:
        return False
    
    letter_count = sum(1 for c in cleaned if c.isalpha())
    ratio = letter_count / len(cleaned)
    
    return ratio >= 0.7

def parse_number(text: str) -> int | None:
    """Parse number from text, return None if invalid."""
    try:
        # Try to extract number
        numbers = re.findall(r'\d+', text)
        if numbers:
            num = int(numbers[0])
            # Must be between 1-9
            if 1 <= num <= 9:
                return num
        return None
    except:
        return None

# ============================================
# GRAPH NODES
# ============================================
def extract_topic_node(state: State):
    """Extract and validate topic from user's message."""
    messages = state["messages"]
    
    user_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
    
    if user_messages:
        topic = user_messages[-1].content.strip()
        
        # Validate topic
        if not is_valid_topic(topic):
            return {
                "error": "invalid_topic",
                "messages": [
                    AIMessage(content="❌ Por favor ingresa un tema válido (no caracteres aleatorios). Intenta de nuevo.")
                ]
            }
        
        return {"topic": topic, "error": None}
    
    return state

def ask_quantity_node(state: State):
    """Ask and validate quantity using interrupt."""
    # Check if there was an error in previous step
    if state.get("error"):
        return state
    
    topic = state["topic"]
    question = f"¿Cuántos chistes deseas sobre '{topic}'? (1-9)"
    
    # Loop de validación con interrupt
    while True:
        answer = interrupt(question)
        
        # Validar respuesta
        num = parse_number(str(answer))
        
        if num is None:
            question = f"❌ '{answer}' no es válido. Por favor ingresa un número entre 1 y 9:"
            continue
        
        # Si es válido, salir del loop
        break
    
    print(f"[DEBUG] Usuario solicitó {num} chistes sobre: {topic}")
    return {"num_jokes": num, "error": None}

def generate_jokes_parallel_node(state: State):
    """Generate N jokes in PARALLEL about the TOPIC."""
    # Skip if there's an error
    if state.get("error"):
        return state
    
    topic = state.get("topic")
    num_jokes = state.get("num_jokes")
    
    if not topic or not num_jokes:
        return state
    
    print(f"\n🎭 Generando {num_jokes} chistes en paralelo sobre '{topic}'...\n")
    
    jokes = []
    
    # Execute in parallel
    with ThreadPoolExecutor(max_workers=num_jokes) as executor:
        futures = [
            executor.submit(generate_single_joke, topic)
            for _ in range(num_jokes)
        ]
        
        for future in as_completed(futures):
            try:
                joke = future.result()
                jokes.append(joke)
            except Exception as e:
                jokes.append(f"Error: {str(e)}")
    
    return {"jokes": jokes}

def map_reduce_node(state: State):
    """Map-reduce: Combine all jokes."""
    # If there was an error, don't add more messages
    if state.get("error"):
        return state
    
    jokes = state.get("jokes", [])
    
    if not jokes:
        final_msg = AIMessage(content="No se pudieron generar chistes.")
        return {"messages": [final_msg]}
    
    # Map-Reduce: formatear todos los chistes
    formatted = "\n\n" + "="*60 + "\n"
    formatted += "🎉 AQUÍ ESTÁN TUS CHISTES 🎉\n"
    formatted += "="*60 + "\n\n"
    
    formatted += "\n\n".join(
        f"😂 Chiste {i+1}:\n{joke}"
        for i, joke in enumerate(jokes)
    )
    
    formatted += "\n\n" + "="*60
    
    final_msg = AIMessage(content=formatted)
    
    return {"messages": [final_msg]}

# ============================================
# CONDITIONAL ROUTING
# ============================================
def check_error(state: State):
    """Check if there's an error that should stop the flow."""
    if state.get("error"):
        return "error"
    return "continue"

# ============================================
# BUILD GRAPH
# ============================================
def create_graph():
    """Build the graph with interrupt support."""
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("extract_topic", extract_topic_node)
    workflow.add_node("ask_quantity", ask_quantity_node)
    workflow.add_node("generate_parallel", generate_jokes_parallel_node)
    workflow.add_node("map_reduce", map_reduce_node)
    
    # Flow simplificado
    workflow.add_edge(START, "extract_topic")
    
    # Check if topic is valid
    workflow.add_conditional_edges(
        "extract_topic",
        check_error,
        {
            "error": END,
            "continue": "ask_quantity"
        }
    )
    
    # El interrupt en ask_quantity maneja la pausa
    workflow.add_edge("ask_quantity", "generate_parallel")
    workflow.add_edge("generate_parallel", "map_reduce")
    workflow.add_edge("map_reduce", END)
    
    # IMPORTANTE: compilar con checkpointer para que interrupt funcione
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)

# ============================================
# MAIN
# ============================================
def main():
    """Run the joke bot with interrupt support."""
    
    print("\n" + "="*60)
    print("😂  GENERADOR DE CHISTES EN PARALELO  😂".center(60))
    print("="*60)
    print("Ingresa un tema para generar chistes")
    print("="*60 + "\n")
    
    graph = create_graph()
    
    # Config con thread_id para mantener estado entre invocaciones
    config = {"configurable": {"thread_id": "joke-session-1"}}
    
    # ============================================
    # STEP 1: Pedir y validar topic
    # ============================================
    while True:
        print("User: ", end="")
        topic_input = input().strip()
        
        if not topic_input:
            print("❌ No ingresaste nada. Intenta de nuevo.\n")
            continue
        
        # Estado inicial
        state = {
            "messages": [HumanMessage(content=topic_input)],
            "topic": None,
            "num_jokes": None,
            "jokes": [],
            "error": None
        }
        
        # Primera invocación - valida el topic y llega hasta el interrupt
        try:
            result = graph.invoke(state, config)
            
            # Si hay error de topic inválido, mostrar mensaje y reintentar
            if result.get("error") == "invalid_topic":
                ai_msgs = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
                if ai_msgs:
                    print(f"\n{ai_msgs[-1].content}\n")
                # Reiniciar con nuevo thread_id para limpiar estado
                config = {"configurable": {"thread_id": f"joke-session-{os.urandom(4).hex()}"}}
                continue
            
            # Si llegamos aquí, el topic es válido y estamos en el interrupt
            break
            
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            continue
    
    # ============================================
    # STEP 2: El interrupt está esperando la cantidad
    # ============================================
    # El grafo está pausado en ask_quantity esperando respuesta
    # Simplemente pedimos input y resumimos
    while True:
        print("\nUser: ", end="")
        quantity_input = input().strip()
        
        if not quantity_input:
            print("❌ No ingresaste nada. Intenta de nuevo.")
            continue
        
        try:
            # Resumir la ejecución pasando la respuesta del usuario
            # El interrupt() en ask_quantity_node recibirá quantity_input
            final_result = graph.invoke(quantity_input, config)
            
            # Si el grafo terminó completamente, mostrar resultados
            if final_result.get("jokes"):
                # Mostrar los chistes
                ai_msgs = [msg for msg in final_result["messages"] if isinstance(msg, AIMessage)]
                if ai_msgs:
                    print(f"\n{ai_msgs[-1].content}\n")
                break
            
        except Exception as e:
            print(f"\n❌ Error inesperado: {e}\n")
            break
    
    print("="*60)
    print("¡Gracias por usar el generador de chistes! 😂")
    print("="*60 + "\n")

# ============================================
# ENTRY POINT
# ============================================
if __name__ == "__main__":
    api_key = os.getenv("OPENAI_API_KEY")
    check_langsmith_config()
    
    if not api_key:
        print("\n❌ ERROR: OPENAI_API_KEY not found!")
        print("Crea un archivo .env con: OPENAI_API_KEY=tu_clave\n")
    else:
        main()
