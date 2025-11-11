# appointment_assistant.py
import os
from typing import TypedDict, Annotated
from datetime import datetime
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ============================================
# APPOINTMENTS DATA (Static)
# ============================================
APPOINTMENTS = [
    "2025-05-15 09:00",
    "2025-05-15 14:30",
    "2025-05-16 10:00",
    "2025-05-17 16:00",
    "2025-05-20 11:30",
    "2025-05-22 15:00",
    "2025-05-25 09:30",
    "2025-05-28 13:00",
]

# ============================================
# STATE DEFINITION
# ============================================
class State(TypedDict):
    messages: Annotated[list, add_messages]

# ============================================
# TOOL: GET APPOINTMENTS
# ============================================
@tool
def get_appointments(query: str = "all") -> str:
    """Get appointment information from the schedule.
    
    Args:
        query: Can be 'all' for all appointments, a specific date like '2025-05-15',
               or a day reference like 'today', 'tomorrow', 'this week'
    
    Returns:
        List of appointments matching the query
    """
    try:
        today = datetime.now()
        
        # Parse appointments
        appointments_dt = []
        for apt in APPOINTMENTS:
            try:
                dt = datetime.strptime(apt, "%Y-%m-%d %H:%M")
                appointments_dt.append(dt)
            except:
                continue
        
        # Filter based on query
        query_lower = query.lower()
        
        if query_lower == "all":
            result = [apt.strftime("%Y-%m-%d at %I:%M %p") for apt in appointments_dt]
            return f"Total appointments: {len(result)}\n" + "\n".join(f"- {apt}" for apt in result)
        
        elif "today" in query_lower:
            today_apts = [apt for apt in appointments_dt if apt.date() == today.date()]
            if today_apts:
                result = [apt.strftime("%Y-%m-%d at %I:%M %p") for apt in today_apts]
                return f"Today's appointments ({len(result)}):\n" + "\n".join(f"- {apt}" for apt in result)
            else:
                return "No appointments scheduled for today."
        
        elif "tomorrow" in query_lower:
            tomorrow = today.replace(day=today.day + 1)
            tomorrow_apts = [apt for apt in appointments_dt if apt.date() == tomorrow.date()]
            if tomorrow_apts:
                result = [apt.strftime("%Y-%m-%d at %I:%M %p") for apt in tomorrow_apts]
                return f"Tomorrow's appointments ({len(result)}):\n" + "\n".join(f"- {apt}" for apt in result)
            else:
                return "No appointments scheduled for tomorrow."
        
        elif "week" in query_lower or "this week" in query_lower:
            week_end = today.replace(day=today.day + 7)
            week_apts = [apt for apt in appointments_dt if today.date() <= apt.date() <= week_end.date()]
            if week_apts:
                result = [apt.strftime("%Y-%m-%d at %I:%M %p") for apt in week_apts]
                return f"This week's appointments ({len(result)}):\n" + "\n".join(f"- {apt}" for apt in result)
            else:
                return "No appointments scheduled for this week."
        
        # Try to parse as specific date
        else:
            # Try different date formats
            for fmt in ["%Y-%m-%d", "%m-%d-%Y", "%d-%m-%Y"]:
                try:
                    target_date = datetime.strptime(query, fmt).date()
                    matching = [apt for apt in appointments_dt if apt.date() == target_date]
                    if matching:
                        result = [apt.strftime("%Y-%m-%d at %I:%M %p") for apt in matching]
                        return f"Appointments on {target_date} ({len(result)}):\n" + "\n".join(f"- {apt}" for apt in result)
                    else:
                        return f"No appointments scheduled for {target_date}."
                except:
                    continue
            
            # If no format worked, return all and let LLM interpret
            result = [apt.strftime("%Y-%m-%d at %I:%M %p") for apt in appointments_dt]
            return f"All appointments ({len(result)}):\n" + "\n".join(f"- {apt}" for apt in result)
    
    except Exception as e:
        return f"Error retrieving appointments: {str(e)}"

# ============================================
# LLM SETUP
# ============================================
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.7
)

# Bind tool
llm_with_tools = llm.bind_tools([get_appointments])

# System prompt
SYSTEM_PROMPT = """You are Mark, a helpful appointment assistant.

Your role is to help users check their appointment schedule. You can:
- Tell them how many appointments they have
- Check if they have appointments on specific dates
- List appointments for today, tomorrow, or specific time periods
- Answer questions about their schedule

IMPORTANT INSTRUCTIONS:
1. ALWAYS use the get_appointments tool to retrieve schedule information
2. Be friendly and conversational - you're Mark, not a formal AI
3. When asked about specific dates or times (morning/afternoon/evening), use the tool and interpret the results
4. You can ONLY read appointments - you cannot create, modify, or cancel them
5. If someone asks to book/cancel, politely tell them you only have read access to the schedule

Examples of time interpretations:
- Morning: before 12:00 PM
- Afternoon: 12:00 PM - 5:00 PM  
- Evening: after 5:00 PM

Be natural and helpful!"""

# ============================================
# GRAPH NODES
# ============================================
def assistant_node(state: State):
    """Process user message and generate response."""
    messages = state["messages"]
    
    # Add system prompt if needed
    if not any(isinstance(msg, SystemMessage) for msg in messages):
        messages_with_system = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    else:
        messages_with_system = messages
    
    # Call LLM
    response = llm_with_tools.invoke(messages_with_system)
    
    return {"messages": [response]}

def tool_node(state: State):
    """Execute the get_appointments tool."""
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_messages = []
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call['name'] == 'get_appointments':
                # Execute tool
                result = get_appointments.invoke(tool_call['args'])
                
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
def should_continue(state: State):
    """Decide if we need to run tools or finish."""
    messages = state["messages"]
    last_message = messages[-1]
    
    # If tool calls exist, go to tools
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    # Otherwise end
    return END

# ============================================
# BUILD GRAPH
# ============================================
def create_graph():
    """Build the LangGraph workflow."""
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("assistant", assistant_node)
    workflow.add_node("tools", tool_node)
    
    # Add edges
    workflow.add_edge(START, "assistant")
    
    # Conditional routing
    workflow.add_conditional_edges(
        "assistant",
        should_continue,
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
    """Run Mark in terminal."""
    
    # Header
    print("\n" + "="*60)
    print("📅  MARK - Your Appointment Assistant  📅".center(60))
    print("="*60)
    print("I can help you check your appointment schedule!")
    print("Commands: 'quit', 'exit', or 'bye' to end")
    print("="*60 + "\n")
    
    # Initialize graph
    graph = create_graph()
    
    # Initial greeting
    print("Mark: ¿En qué le puedo ayudar hoy?\n")
    
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
            print("\nMark: ¡Que tenga un excelente día! 📅\n")
            break
        
        # Add user message
        conversation_state["messages"].append(HumanMessage(content=user_input))
        
        # Run graph
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
                print(f"\nMark: {final_response.content}\n")
            else:
                print("\nMark: (No pude generar una respuesta)\n")
        
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