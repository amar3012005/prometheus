import os
import sys
import json
import logging
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai
from typing import Dict, Any, List
import yaml

# Configure logging to suppress everything but the JSON result
logging.basicConfig(level=logging.ERROR)

SYSTEM_INSTRUCTION = """
You are the **PROMETHEUS Architect**, a ruthless perfectionist in AI Agent design. 
Your mission is to extract EVERY DETAIL needed for a production Helm deployment. 

**DO NOT STOP ASKING until you have high-quality data for every field.**
If a user response is short or lazy, ask them to elaborate. 

FIELDS YOU MUST SATISFY:
1.  **Identity**: 
    - `name`: Must be a distinct agent name.
    - `introGreeting`: A catchy, high-energy greeting.
    - `systemPrompt`: A deep, 300+ word XML-structured prompt (Inferred is okay, but confirm with user).
    - `voiceStability`: Specific float (0.0 to 1.0).
    - `voiceSimilarity`: Specific float (0.0 to 1.0).
2.  **Knowledge**:
    - `orgName`: The exact organization name.
    - `knowledgeContent`: AT LEAST 2-3 paragraphs of reference context.
    - `responseStyle`: [friendly_casual, professional_clear, concise_technical].
3.  **Voice**:
    - `voiceId`: Identify a specific ElevenLabs voice.

**ROLES:**
- You are strictly JSON-only.
- You increment `completeness_score` slowly. Do not hit 100 until you have at least 3-4 turns of solid information.
- If information is semi-complete, set `completeness_score` < 90.
- Only when `completeness_score` is 100, set `next_question` to "DONE".

Output Schema:
{
  "identity": { "name": "...", "introGreeting": "...", "systemPrompt": "...", "voiceStability": 0.5, "voiceSimilarity": 0.75, "voiceId": "..." },
  "knowledge": { "orgName": "...", "knowledgeContent": "...", "responseStyle": "..." },
  "missing_fields": ["detailed list of what is still needed"],
  "next_question": "Your probing follow-up question here",
  "completeness_score": 0
}
"""

def get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY") or "AIzaSyBG9nb_Xe2267oBO9s0g0jJOQtJGh47pNk"
    if not api_key:
        print(json.dumps({"error": "GEMINI_API_KEY not set"}))
        sys.exit(1)
    
    genai.configure(api_key=api_key)
    generation_config = {
        "temperature": 0.7,
        "response_mime_type": "application/json",
    }
    
    return genai.GenerativeModel(
        model_name="gemini-2.0-flash-lite",
        generation_config=generation_config,
        system_instruction=SYSTEM_INSTRUCTION,
    )

def generate_files(data: Dict[str, Any], output_dir: str = "/home/prometheus/leibniz_agent/TARA-MICROSERVICE/generated_agent"):
    """Generates values.yaml and state.json for the executioner"""
    os.makedirs(output_dir, exist_ok=True)
    
    identity = data.get("identity", {})
    knowledge = data.get("knowledge", {})
    
    # Save raw state
    state_path = os.path.join(output_dir, "state.json")
    with open(state_path, "w") as f:
        json.dump(data, f, indent=2)
    
    # Construct values.yaml
    response_style = knowledge.get("responseStyle", "friendly_casual")
    
    personas_dict = {
        "personas": {
            "default": {
                "name": f"{identity.get('name', 'agent').lower()}_default",
                "display_name": identity.get("name", "Agent"),
                "personality_traits": ["helpful", response_style.split('_')[0]],
                "response_style": response_style,
                "restrictions": ["Never mention being an AI"]
            }
        }
    }
    
    values_content = {
        "global": {
            "orgName": knowledge.get("orgName", "My Org"),
            "environment": "production"
        },
        "orchestrator": {
            "persona": {
                "name": identity.get("name", "Agent"),
                "introGreeting": identity.get("introGreeting", "Hello."),
                "systemPrompt": identity.get("systemPrompt", "You are a helpful agent.")
            }
        },
        "rag": {
            "personas": yaml.dump(personas_dict, default_flow_style=False, sort_keys=False),
            "knowledgeBase": {
                "content": {
                    "knowledge.md": knowledge.get("knowledgeContent", "")
                }
            }
        }
    }
    
    values_path = os.path.join(output_dir, "values.yaml")
    with open(values_path, "w") as f:
        yaml.dump(values_content, f, default_flow_style=False, sort_keys=False)

def main():
    # Read input from stdin
    try:
        input_data = sys.stdin.read()
        payload = json.loads(input_data)
        user_message = payload.get("message", "")
        history = payload.get("history", []) # List of {role: ..., content: ...}
    except Exception as e:
        print(json.dumps({"error": f"Invalid input: {str(e)}"}))
        sys.exit(1)

    model = get_gemini_model()
    
    # Map roles to Gemini roles
    gemini_history = []
    for entry in history[:-1]: # Previous messages
        role = "user" if entry["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [entry["content"]]})
    
    chat = model.start_chat(history=gemini_history)
    
    try:
        response = chat.send_message(user_message)
        # The result should be the JSON string from Gemini
        # We ensure it's on a single line for the backend parser
        data = json.loads(response.text)
        
        # If complete, generate files
        if data.get("completeness_score", 0) >= 100 or data.get("next_question") == "DONE":
            generate_files(data)
            
        print(json.dumps(data))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
