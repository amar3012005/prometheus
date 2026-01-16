
import os
import google.generativeai as genai
from tabulate import tabulate

api_key = os.getenv("GEMINI_API_KEY") or "AIzaSyBG9nb_Xe2267oBO9s0g0jJOQtJGh47pNk"
genai.configure(api_key=api_key)

print("Listing available models...")
try:
    models = genai.list_models()
    table_data = []
    for m in models:
        table_data.append([m.name, m.supported_generation_methods])
    
    print(tabulate(table_data, headers=["Name", "Methods"]))
except Exception as e:
    print(f"Error: {e}")
