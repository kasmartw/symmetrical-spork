# one_piece_chatbot.py
import os
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


# ============================================
# STATE DEFINITION
# ============================================
class State(TypedDict):
    messages: Annotated[list, add_messages]

# ============================================
# TOOL: ONE PIECE WIKI SEARCH
# ============================================
@tool
def search_one_piece_wiki(query: str) -> str:
    """Search the One Piece Wiki for information about characters, arcs, Devil Fruits, or concepts.
    
    Args:
        query: The topic to search for (e.g., 'Luffy', 'Marineford', 'Gomu Gomu no Mi')
    
    Returns:
        Information from the One Piece Wiki
    """
    try:
        # Formatear query para URL de Fandom
        search_term = query.replace(" ", "_").title()
        url = f"https://onepiece.fandom.com/wiki/{search_term}"
        
        # Headers para simular navegador
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Intentar extraer el primer párrafo con información
            content_div = soup.find('div', {'class': 'mw-parser-output'})
            
            if content_div:
                # Buscar párrafos con contenido sustancial
                paragraphs = []
                for p in content_div.find_all('p'):
                    text = p.get_text().strip()
                    # Filtrar párrafos vacíos o muy cortos
                    if len(text) > 50:
                        paragraphs.append(text)
                    if len(paragraphs) >= 2:  # Primeros 2 párrafos
                        break
                
                if paragraphs:
                    result = ' '.join(paragraphs)
                    # Limitar longitud para no saturar el contexto
                    return result[:1500] if len(result) > 1500 else result
                else:
                    return f"Found the page for '{query}' but couldn't extract detailed info. Try being more specific."
            else:
                return f"Page found but content couldn't be extracted for '{query}'."
        else:
            # Sugerir búsqueda alternativa
            return f"Couldn't find a wiki page for '{query}'. Try searching for the full name or a different term."
            
    except Exception as e:
        return f"Error accessing One Piece Wiki: {str(e)}. The wiki might be temporarily unavailable."

# ============================================
# LLM SETUP
# ============================================
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.5,
)

# Bind the tool to the LLM
llm_with_tools = llm.bind_tools([search_one_piece_wiki])

# System prompt
SYSTEM_PROMPT = """You are an expert on One Piece, the legendary manga and anime series by Eiichiro Oda.

Your role is to help fans discover and learn about:
- Characters and their abilities
- Story arcs and major events  
- Devil Fruits and their powers
- The Straw Hat Pirates and other crews
- Locations in the One Piece world
- Lore, theories, and mysteries

IMPORTANT INSTRUCTIONS:
1. When you need factual information, ALWAYS use the search_one_piece_wiki tool first
2. After getting wiki results, provide a clear, enthusiastic answer based on that information
3. Feel free to add your own insights after presenting the facts
4. If the wiki search doesn't find what you need, acknowledge it and offer to search for something related
5. Be conversational and fun - use phrases like "Yohohoho!" or "Set sail!" occasionally

Remember: Accuracy is important, so rely on the wiki tool for facts!"""

# ============================================
# GRAPH NODES
# ============================================
def chatbot_node(state: State):
    """Process user message and generate response (potentially with tool calls)."""
    messages = state["messages"]
    
    # Add system prompt if this is the start
    if not any(isinstance(msg, SystemMessage) for msg in messages):
        messages_with_system = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    else:
        messages_with_system = messages
    
    # Call LLM (might return tool calls)
    response = llm_with_tools.invoke(messages_with_system)
    
    return {"messages": [response]}

def tool_node(state: State):
    """Execute the tools that the LLM requested."""
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_messages = []
    
    # Execute each tool call
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call['name'] == 'search_one_piece_wiki':
                # Execute the tool
                result = search_one_piece_wiki.invoke(tool_call['args'])
                
                # Create ToolMessage with the result
                tool_msg = ToolMessage(
                    content=result,
                    tool_call_id=tool_call['id']
                )
                tool_messages.append(tool_msg)
    
    return {"messages": tool_messages}

# ============================================
# CONDITIONAL LOGIC
# ============================================
def should_continue(state: State):
    """Decide whether to run tools or end the turn."""
    messages = state["messages"]
    last_message = messages[-1]
    
    # If LLM made tool calls, go to tools node
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    # Otherwise, end this turn (response is ready)
    return END

# ============================================
# BUILD GRAPH
# ============================================
def create_graph():
    """Build the LangGraph workflow."""
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("chatbot", chatbot_node)
    workflow.add_node("tools", tool_node)
    
    # Add edges
    workflow.add_edge(START, "chatbot")
    
    # Conditional edge: continue to tools or end
    workflow.add_conditional_edges(
        "chatbot",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )
    
    # After tools, go back to chatbot to generate final response
    workflow.add_edge("tools", "chatbot")
    
    return workflow.compile()

# ============================================
# MAIN CHAT LOOP
# ============================================
def main():
    """Run the chatbot in terminal."""
    
    # Header
    print("\n" + "="*60)
    print("🏴‍☠️  ONE PIECE EXPERT CHATBOT  🏴‍☠️".center(60))
    print("="*60)
    print("Ask me anything about One Piece!")
    print("Commands: 'quit', 'exit', or 'bye' to end")
    print("="*60 + "\n")
    
    # Initialize graph
    graph = create_graph()
    
    # Initial bot message
    print("AI: What would you like to know about One Piece?\n")
    
    # Conversation state (persists across turns)
    conversation_state = {"messages": []}
    
    # Chat loop
    while True:
        # Get user input
        user_input = input("You: ").strip()
        
        # Skip empty inputs
        if not user_input:
            continue
        
        # Exit commands
        if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
            print("\nAI: Thanks for sailing with me! See you on the Grand Line! 🏴‍☠️\n")
            break
        
        # Add user message to state
        conversation_state["messages"].append(HumanMessage(content=user_input))
        
        # Run the graph
        try:
            # Invoke returns final state after all nodes execute
            result = graph.invoke(conversation_state)
            
            # Update conversation state with ALL messages (includes tool calls, etc.)
            conversation_state = result
            
            # Extract final AI response (last AIMessage)
            ai_responses = [
                msg for msg in result["messages"] 
                if isinstance(msg, AIMessage)
            ]
            
            if ai_responses:
                final_response = ai_responses[-1]
                print(f"\nAI: {final_response.content}\n")
            else:
                print("\nAI: (No response generated)\n")
        
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")
            print("Please try again or rephrase your question.\n")

# ============================================
# ENTRY POINT
# ============================================
if __name__ == "__main__":
    # Verify API key exists
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("\n❌ ERROR: OPENAI_API_KEY not found!")
        print("\nPlease create a .env file with:")
        print("OPENAI_API_KEY=your_api_key_here\n")
    else:
        main()