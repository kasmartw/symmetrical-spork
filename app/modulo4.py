# joke_bot.py
import os
import re
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Cargar variables de entorno
load_dotenv()

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
    # Remove spaces and check if at least 70% are letters
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
    """Ask how many jokes."""
    # Check if there was an error
    if state.get("error"):
        return state
    
    topic = state["topic"]
    
    question = AIMessage(content=f"¿Cuántos chistes desea de {topic}? (1-9)")
    
    return {"messages": [question]}

def parse_quantity_node(state: State):
    """Parse and validate quantity from user's message."""
    messages = state["messages"]
    
    # Get only messages AFTER the quantity question
    # Find the last AI message asking for quantity
    last_ai_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], AIMessage) and "¿Cuántos chistes" in messages[i].content:
            last_ai_idx = i
            break
    
    # Get user messages after that
    if last_ai_idx >= 0:
        user_msgs_after = [
            msg for i, msg in enumerate(messages)
            if i > last_ai_idx and isinstance(msg, HumanMessage)
        ]
        
        if user_msgs_after:
            text = user_msgs_after[-1].content.strip()
            
            num = parse_number(text)
            
            if num is None:
                return {
                    "error": "invalid_number",
                    "messages": [
                        AIMessage(content="❌ Por favor ingresa un número válido entre 1 y 9.")
                    ]
                }
            
            return {"num_jokes": num, "error": None}
    
    # Default fallback
    return {"num_jokes": 3, "error": None}

def generate_jokes_parallel_node(state: State):
    """Generate N jokes in PARALLEL about the TOPIC."""
    # Skip if there's an error
    if state.get("error"):
        return state
    
    topic = state.get("topic")
    num_jokes = state.get("num_jokes")
    
    if not topic or not num_jokes:
        return state
    
    print(f"[DEBUG] Generating {num_jokes} jokes about: {topic}")
    
    jokes = []
    
    # Execute in parallel
    with ThreadPoolExecutor(max_workers=num_jokes) as executor:
        # IMPORTANTE: Pasar el TOPIC, no num_jokes
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
    
    # Map-Reduce
    formatted = "\n---\n".join(
        f"Chiste {i+1}:\n{joke}"
        for i, joke in enumerate(jokes)
    )
    
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
    """Build the graph with error handling."""
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("extract_topic", extract_topic_node)
    workflow.add_node("ask_quantity", ask_quantity_node)
    workflow.add_node("parse_quantity", parse_quantity_node)
    workflow.add_node("generate_parallel", generate_jokes_parallel_node)
    workflow.add_node("map_reduce", map_reduce_node)
    
    # Flow
    workflow.add_edge(START, "extract_topic")
    
    # Check if topic is valid
    workflow.add_conditional_edges(
        "extract_topic",
        check_error,
        {
            "error": END,  # Stop if invalid topic
            "continue": "ask_quantity"
        }
    )
    
    workflow.add_edge("ask_quantity", "parse_quantity")
    
    # Check if quantity is valid
    workflow.add_conditional_edges(
        "parse_quantity",
        check_error,
        {
            "error": END,  # Stop if invalid number
            "continue": "generate_parallel"
        }
    )
    
    workflow.add_edge("generate_parallel", "map_reduce")
    workflow.add_edge("map_reduce", END)
    
    return workflow.compile()

# ============================================
# MAIN
# ============================================
def main():
    """Run the joke bot."""
    
    print("\n" + "="*60)
    print("😂  PARALLEL JOKE GENERATOR  😂".center(60))
    print("="*60)
    print("Ingresa un tema para generar chistes")
    print("="*60 + "\n")
    
    graph = create_graph()
    
    # ============================================
    # STEP 1: Get and validate topic
    # ============================================
    while True:
        state = {
            "messages": [],
            "topic": None,
            "num_jokes": None,
            "jokes": [],
            "error": None
        }
        
        print("User: ", end="")
        topic_input = input().strip()
        
        if not topic_input:
            print("No ingresaste nada. Intenta de nuevo.\n")
            continue
        
        state["messages"].append(HumanMessage(content=topic_input))
        
        # Validate topic
        result = graph.invoke(state)
        
        # Check if there was an error
        if result.get("error") == "invalid_topic":
            ai_msgs = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
            if ai_msgs:
                print(f"\nAI: {ai_msgs[-1].content}\n")
            continue  # Ask for topic again
        
        # Topic is valid, show question
        ai_msgs = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        if ai_msgs:
            print(f"\nAI: {ai_msgs[0].content}\n")
        
        break  # Exit topic loop
    
    # ============================================
    # STEP 2: Get and validate quantity
    # ============================================
    while True:
        print("User: ", end="")
        quantity_input = input().strip()
        
        if not quantity_input:
            print("No ingresaste nada. Intenta de nuevo.\n")
            continue
        
        # Add to messages
        result["messages"].append(HumanMessage(content=quantity_input))
        
        # Continue graph
        print("\n🎭 Generando chistes en paralelo...\n")
        
        final_result = graph.invoke(result)
        
        # Check if there was an error with the number
        if final_result.get("error") == "invalid_number":
            ai_msgs = [msg for msg in final_result["messages"] if isinstance(msg, AIMessage)]
            if ai_msgs:
                print(f"\nAI: {ai_msgs[-1].content}\n")
            
            # Remove the invalid input and try again
            result["messages"] = result["messages"][:-1]
            continue
        
        # Success! Show jokes
        ai_final = [msg for msg in final_result["messages"] if isinstance(msg, AIMessage)]
        
        if ai_final:
            print(f"AI:\n{ai_final[-1].content}\n")
        
        break  # Exit quantity loop
    
    print("="*60)
    print("Conversación finalizada. ¡Gracias! 😂")
    print("="*60 + "\n")

# ============================================
# ENTRY POINT
# ============================================
if __name__ == "__main__":
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("\n❌ ERROR: OPENAI_API_KEY not found!")
        print("Create .env with: OPENAI_API_KEY=your_key\n")
    else:
        main()
