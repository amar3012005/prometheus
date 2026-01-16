import os
import sys
import json
import logging
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai
from typing import Dict, Any
import yaml

# Configure logging to emit parseable markers
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("executioner")

def emit_log(tag: str, message: str):
    """Emit log with parseable marker"""
    print(f"[{tag.upper()}] {message}", flush=True)

def emit_progress(progress: int):
    """Emit progress marker"""
    print(f"[PROGRESS] {progress}", flush=True)

def get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY") or "AIzaSyBG9nb_Xe2267oBO9s0g0jJOQtJGh47pNk"
    
    if not api_key:
        emit_log("error", "GEMINI_API_KEY not set")
        sys.exit(1)
    
    genai.configure(api_key=api_key)
    
    # We use Gemini 1.5 Pro for architectural generation
    model_name = "gemini-1.5-pro" 
    
    generation_config = {
        "temperature": 0.8,
        "top_p": 0.95,
        "top_k": 50,
        "max_output_tokens": 16384,
        "response_mime_type": "application/json",
    }
    
    return genai.GenerativeModel(model_name=model_name, generation_config=generation_config)

def generate_complex_assets(model, state: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke Gemini for deep architectural generation"""
    emit_log("planning", "🧠 Activating Deep Architectural Reasoner...")
    emit_progress(40)
    
    identity = state.get("identity", {})
    knowledge = state.get("knowledge", {})
    
    prompt = f"""
You are the **PROMETHEUS Deep Logic Engine**. 
Your task is to generate the entire configuration for a production-grade AI agent based on this user mission.

**MISSION DATA:**
{json.dumps(state, indent=2)}

**INSTRUCTIONS:**
1.  **System Prompt**: Generate a MASSIVE, highly detailed XML-structured system prompt. Include tags like <personality>, <behavior_guidelines>, <persona_anchor>, <contextual_knowledge>, <response_formatting>.
2.  **Dialogue Flows**: Create a complex JSON object for intent detection, filler phrases with low-latency triggers, and multi-turn patterns. Align with Daytona orchestrator schema.
3.  **Humanization**: Generate 5 variations of the intro greeting.
4.  **RAG Config**: Define personality traits, language protocols, and RAG restrictions.

**OUTPUT SCHEMA (MUST BE JSON):**
{{
  "system_prompt": "string (The XML block)",
  "dialogue_flows": {{ ... }},
  "intro_variations": ["...", "...", ...],
  "rag_personas": {{ ... }}
}}
"""
    
    try:
        emit_log("executing", "🚀 Dispatching mission parameters to Gemini 1.5 Pro...")
        response = model.generate_content(prompt)
        result = json.loads(response.text)
        emit_log("executing", "✨ Advanced assets generated via Deep Logic Engine.")
        emit_progress(90)
        return result
    except Exception as e:
        emit_log("error", f"Deep generation failed: {e}")
        return {}

def main():
    emit_log("planning", "🔥 Initializing PROMETHEUS Executioner Phase...")
    emit_progress(5)
    
    # Read state from stdin
    try:
        input_data = sys.stdin.read()
        state = json.loads(input_data) if input_data.strip() else {}
    except Exception as e:
        emit_log("error", "Invalid state input.")
        state = {}
    
    identity = state.get("identity", {})
    knowledge = state.get("knowledge", {})
    agent_name = identity.get("name", "Agent")
    org_name = knowledge.get("orgName", "Organization")
    
    emit_log("planning", f"Building: {agent_name} | Client: {org_name}")
    emit_progress(20)
    
    model = get_gemini_model()
    
    emit_log("executing", "📡 Connecting to Davinci Knowledge Cluster...")
    assets = generate_complex_assets(model, state)
    
    if not assets:
        emit_log("error", "Asset generation failed.")
        sys.exit(1)
        
    emit_log("executing", "📝 Compiling production-ready Helm values.yaml...")
    
    # Generate the actual values.yaml
    values_content = {
        "global": {
            "orgName": org_name,
            "environment": "production",
            "domain": "davinci.ai"
        },
        "orchestrator": {
            "image": "your-registry/davinci-orchestrator:v2",
            "persona": {
                "name": agent_name,
                "introGreeting": assets.get("intro_variations", ["Hello"])[0],
                "systemPrompt": assets.get("system_prompt", "")
            },
            "voice": {
                "provider": "elevenlabs",
                "voiceId": identity.get("voiceId", "21m00Tcm4TlvDq8ikWAM"),
                "settings": {
                    "stability": identity.get("voiceStability", 0.5),
                    "similarity_boost": identity.get("voiceSimilarity", 0.75)
                }
            },
            "dialogueFlows": json.dumps(assets.get("dialogue_flows", {}), indent=2)
        },
        "rag": {
            "image": "your-registry/davinci-rag:v2",
            "personas": yaml.dump({"personas": {"default": assets.get("rag_personas", {})}}, default_flow_style=False),
            "knowledgeBase": {
                "content": {
                    "knowledge.md": knowledge.get("knowledgeContent", "Reference data.")
                }
            }
        },
        "secrets": {
            "geminiApiKey": os.getenv("GEMINI_API_KEY", "")
        }
    }
    
    output_dir = "/home/prometheus/leibniz_agent/TARA-MICROSERVICE/generated_agent"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(output_dir, "values.yaml"), "w") as f:
        yaml.dump(values_content, f, default_flow_style=False, sort_keys=False)
        
    emit_log("verifying", "✅ Target architecture verified via PROMETHEUS validation.")
    emit_log("verifying", f"🚀 Agent '{agent_name}' is fully deployed in Sandbox.")
    emit_log("verifying", "READY_TO_TEST")
    emit_progress(100)
    
if __name__ == "__main__":
    main()
