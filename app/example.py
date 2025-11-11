import os
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

model = init_chat_model("google_genai:gemini-2.5-flash-lite")


response = model.invoke("Why do parrots talk?")

print(response)