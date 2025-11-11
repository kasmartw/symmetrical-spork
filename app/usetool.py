import os 
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from dotenv import load_dotenv
from langchain.agents.middleware import wrap_model_call, ModelRequest
from langchain.tools import tool

load_dotenv()
google_key = os.getenv("GOOGLE_API_KEY")

model = init_chat_model(
    model="gemini-2.0-flash-exp",
    model_provider="google_genai",
    api_key=google_key,
)

@tool
def get_date():
    """use this tool when ask for date"""
    from datetime import datetime
    return f"Today's date is {datetime.now().strftime('%Y-%m-%d')}"
    



agent = create_agent(
    model,
    tools=[get_date]
)

resp = agent.invoke({
    "messages": [
        {"role":"user", "content":"what is today's date"}
    ]
})

print(resp["messages"][-1].content)