
from google import genai
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Get the API key
api_key = os.getenv("api_key")

# Connect to Gemini
client = genai.Client(api_key=api_key)

# List models available to this API key
print("Models available to your API key:\n")

for model in client.models.list():
    print(model.name)
