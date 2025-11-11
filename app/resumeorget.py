# text_analyzer.py
import os
import re
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ============================================
# STATE DEFINITION
# ============================================
class State(TypedDict):
    messages: Annotated[list, add_messages]

# ============================================
# TOOLS
# ============================================
@tool
def summarize_text(text: str) -> str:
    """Create a brief summary of the provided text.
    
    Args:
        text: The text to summarize
    
    Returns:
        A concise summary of the main points
    """
    try:
        # Count words for context
        word_count = len(text.split())
        
        # Use LLM to summarize
        summary_llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.3
        )
        
        prompt = f"""Provide a brief, clear summary of the following text in 2-3 sentences.
Focus on the main points and key information.

Text to summarize:
{text}

Summary:"""
        
        response = summary_llm.invoke(prompt)
        summary = response.content.strip()
        
        return f"📝 Summary ({word_count} words):\n\n{summary}"
    
    except Exception as e:
        return f"Error creating summary: {str(e)}"

@tool
def extract_names(text: str) -> str:
    """Extract all person names from the provided text.
    
    Args:
        text: The text to extract names from
    
    Returns:
        List of names found in the text
    """
    try:
        # Use LLM to extract names with NER capabilities
        ner_llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0
        )
        
        prompt = f"""Extract ALL person names from the following text.
Return ONLY the names, one per line, without any additional explanation.
If there are no names, respond with "No names found."

Text:
{text}

Names:"""
        
        response = ner_llm.invoke(prompt)
        names_text = response.content.strip()
        
        # Parse the response
        if "no names" in names_text.lower():
            return "👤 No person names found in the text."
        
        # Clean up and format names
        names_list = [name.strip("- •*") for name in names_text.split('\n') if name.strip()]
        
        if names_list:
            return f"👤 Names found ({len(names_list)}):\n\n" + "\n".join(f"• {name}" for name in names_list)
        else:
            return "👤 No person names found in the text."
    
    except Exception as e:
        return f"Error extracting names: {str(e)}"

# ============================================
# LLM SETUP
# ============================================
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.7
)

# Bind tools
llm_with_tools = llm.bind_tools([summarize_text, extract_names])

# System prompt
SYSTEM_PROMPT = """You are a helpful text analysis assistant.

Your capabilities:
1. Summarize texts - Create brief, clear summaries
2. Extract names - Find all person names mentioned in texts

IMPORTANT INSTRUCTIONS:
- When the user asks to "summarize" or wants a "summary", use the summarize_text tool
- When the user asks to "extract names" or "find names", use the extract_names tool
- Always use the appropriate tool based on what the user is asking for
- Be friendly and concise in your responses
- After using a tool, present the results clearly

You are here to help users analyze their texts efficiently!"""

# ============================================
# CONFIGURATION
# ============================================
MIN_WORDS_THRESHOLD = 20  # Minimum words required

# ============================================
# GRAPH NODES
# ============================================
def middleware_check_length(state: State):
    """Middleware: Check if the user's text is long enough."""
    messages = state["messages"]
    
    # Get last user message
    user_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
    
    if not user_messages:
        return state
    
    last_user_msg = user_messages[-1].content
    
    # Count words (simple split)
    word_count = len(last_user_msg.split())
    
    # If too short, add error message
    if word_count < MIN_WORDS_THRESHOLD:
        error_msg = AIMessage(
            content=f"⚠️ Lo siento, el texto es demasiado corto para procesar. "
                   f"Necesito al menos {MIN_WORDS_THRESHOLD} palabras para realizar mis funciones. "
                   f"Tu mensaje tiene {word_count} palabras. Por favor, proporciona un texto más largo."
        )
        return {"messages": [error_msg]}
    
    # If long enough, continue normally
    return state

def assistant_node(state: State):
    """Process user request and decide which tool to use."""
    messages = state["messages"]
    
    # Add system prompt if needed
    if not any(isinstance(msg, SystemMessage) for msg in messages):
        messages_with_system = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    else:
        messages_with_system = messages
    
    # Call LLM with tools
    response = llm_with_tools.invoke(messages_with_system)
    
    return {"messages": [response]}

def tool_node(state: State):
    """Execute the tools requested by the assistant."""
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_messages = []
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            # Execute appropriate tool
            if tool_call['name'] == 'summarize_text':
                result = summarize_text.invoke(tool_call['args'])
            elif tool_call['name'] == 'extract_names':
                result = extract_names.invoke(tool_call['args'])
            else:
                result = f"Unknown tool: {tool_call['name']}"
            
            # Create ToolMessage
            tool_msg = ToolMessage(
                content=result,
                tool_call_id=tool_call['id']
            )
            tool_messages.append(tool_msg)
    
    return {"messages": tool_messages}

# ============================================
# CONDITIONAL LOGIC
# ============================================
def check_text_length(state: State):
    """Check if we should proceed or reject due to short text."""
    messages = state["messages"]
    
    # Get last user message
    user_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
    
    if not user_messages:
        return "continue"
    
    last_user_msg = user_messages[-1].content
    word_count = len(last_user_msg.split())
    
    # If too short, reject
    if word_count < MIN_WORDS_THRESHOLD:
        return "reject"
    
    return "continue"

def should_use_tools(state: State):
    """Decide if assistant needs to use tools."""
    messages = state["messages"]
    last_message = messages[-1]
    
    # If tool calls exist, use them
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    return END

# ============================================
# BUILD GRAPH
# ============================================
def create_graph():
    """Build the LangGraph workflow with middleware."""
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("check_length", middleware_check_length)
    workflow.add_node("assistant", assistant_node)
    workflow.add_node("tools", tool_node)
    
    # Start with middleware
    workflow.add_edge(START, "check_length")
    
    # Conditional: proceed or reject based on length
    workflow.add_conditional_edges(
        "check_length",
        check_text_length,
        {
            "continue": "assistant",
            "reject": END  # Skip to end if too short
        }
    )
    
    # Conditional: use tools or end
    workflow.add_conditional_edges(
        "assistant",
        should_use_tools,
        {
            "tools": "tools",
            END: END
        }
    )
    
    # Loop back after tools
    workflow.add_edge("tools", "assistant")
    
    return workflow.compile()

# ============================================
# MAIN CHAT LOOP
# ============================================
def main():
    """Run the text analyzer in terminal."""
    
    # Header
    print("\n" + "="*60)
    print("📄  TEXT ANALYZER - Summarize & Extract Names  📄".center(60))
    print("="*60)
    print("I can help you:")
    print("  • Summarize texts")
    print("  • Extract person names from texts")
    print(f"\nNote: Texts must have at least {MIN_WORDS_THRESHOLD} words")
    print("Commands: 'quit', 'exit', or 'bye' to end")
    print("="*60 + "\n")
    
    # Initialize graph
    graph = create_graph()
    
    # Initial greeting
    print("AI: ¿En qué le puedo ayudar?\n")
    
    # Conversation state
    conversation_state = {"messages": []}
    
    # Chat loop
    while True:
        # Get user input
        user_input = input("You: ").strip()
        
        # Skip empty
        if not user_input:
            continue
        
        # Exit commands
        if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
            print("\nAI: ¡Gracias por usar el analizador de textos! 📄\n")
            break
        
        # Add user message
        conversation_state["messages"].append(HumanMessage(content=user_input))
        
        # Run graph (with middleware)
        try:
            result = graph.invoke(conversation_state)
            
            # Update state
            conversation_state = result
            
            # Get final AI response
            ai_responses = [
                msg for msg in result["messages"] 
                if isinstance(msg, AIMessage)
            ]
            
            if ai_responses:
                final_response = ai_responses[-1]
                print(f"\nAI: {final_response.content}\n")
            else:
                print("\nAI: (No se pudo generar respuesta)\n")
        
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")
            print("Por favor intenta de nuevo.\n")

# ============================================
# ENTRY POINT
# ============================================
if __name__ == "__main__":
    # Verify API key
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("\n❌ ERROR: OPENAI_API_KEY not found!")
        print("\nPlease create a .env file with:")
        print("OPENAI_API_KEY=your_api_key_here\n")
    else:
        main()