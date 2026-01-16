
import os
import sys
import json
import logging
import google.generativeai as genai
from typing import Dict, Any, List, Optional
import yaml

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("agent_builder")

# ANSI Colors for nicer CLI
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

AGENT_SCHEMA = {
    "type": "object",
    "properties": {
        "identity": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the agent (e.g., TARA, MediBot)"},
                "introGreeting": {"type": "string", "description": "The initial greeting message"},
                "systemPrompt": {"type": "string", "description": "The core behavioral instructions for the agent"},
                "voiceStability": {"type": "number", "description": "ElevenLabs voice stability (0.0-1.0), higher is calmer"},
                "voiceSimilarity": {"type": "number", "description": "ElevenLabs voice similarity boost (0.0-1.0)"}
            },
            "required": ["name", "introGreeting", "systemPrompt"]
        },
        "knowledge": {
            "type": "object",
            "properties": {
                "orgName": {"type": "string", "description": "The organization or domain name"},
                "knowledgeContent": {"type": "string", "description": "The actual knowledge base text/content"},
                "responseStyle": {"type": "string", "enum": ["friendly_casual", "professional_clear", "concise_technical"], "description": "The style of response"}
            },
            "required": ["orgName"]
        },
        "credentials": {
            "type": "object",
            "properties": {
                "llmKey": {"type": "string", "description": "API Key for LLM (OpenAI/Gemini)"},
                "voiceKey": {"type": "string", "description": "API Key for ElevenLabs"}
            },
            # Credentials can be optional in the builder if user wants to add them later
            "required": [] 
        },
        "missing_fields": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of required fields that are still missing or incomplete"
        },
        "next_question": {
            "type": "string",
            "description": "The next question to ask the user to gather missing information"
        },
        "completeness_score": {
            "type": "integer",
            "description": "0-100 score of how complete the configuration is"
        }
    },
    "required": ["identity", "knowledge", "missing_fields", "next_question", "completeness_score"]
}

SYSTEM_INSTRUCTION = """
You are an expert Agent Architect for the Daytona platform. Your goal is to interview the user to build a custom AI Agent configuration.

You need to extract specific information to fill a configuration schema. 
The schema includes:
1.  **Identity**: Name, Greeting, System Prompt (Behavior), Voice Settings.
2.  **Knowledge**: Organization Name. Knowledge Base Content: IGNORE if not provided, DO NOT ASK for it. Response Style.
3.  **Credentials**: API Keys (optional during build, but good to ask).

**Process:**
1.  Analyze the user's input.
2.  Update the JSON object conforming to `AGENT_SCHEMA`.
3.  If information is missing, formulate a specific `next_question` to ask the user.
    - Be polite but direct.
    - Ask for one or two things at a time, don't overwhelm.
    - If the user provides a high-level intent (e.g., "I want a medical bot"), infer reasonable defaults for System Prompt and Greeting, but ask for confirmation or specifics like the Agent's Name or Knowledge Base.
4.  **Infer Voice Settings**: based on description (e.g., "calm" -> stability 0.8, "excited" -> stability 0.3).
5.  **Infer Response Style**: based on description (e.g. "professional" -> professional_clear).
6.  **Construct Knowledge**: If the user pastes text, put it in `knowledgeContent`.
7.  Set `completeness_score` from 0 to 100. When 100, `next_question` should be "DONE".

**Output Format**:
Return ONLY valid JSON. No markdown formatting.
"""

def get_gemini_model():
    # Try getting from env var, otherwise use the provided key
    api_key = os.getenv("GEMINI_API_KEY") or "AIzaSyBG9nb_Xe2267oBO9s0g0jJOQtJGh47pNk"
    
    if not api_key:
        print(f"{RED}Error: GEMINI_API_KEY environment variable not set.{RESET}")
        print("Please export your key: export GEMINI_API_KEY='your_key'")
        sys.exit(1)
    
    genai.configure(api_key=api_key)
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json",
    }
    
    return genai.GenerativeModel(
        model_name="gemini-2.0-flash-lite",
        generation_config=generation_config,
        system_instruction=SYSTEM_INSTRUCTION,
    )

def main():
    print(f"{BLUE}========================================={RESET}")
    print(f"{BLUE}   Daytona Agent Builder (Davinci AI)    {RESET}")
    print(f"{BLUE}========================================={RESET}")
    print("Welcome! I'll help you configure your custom agent.")
    print("Tell me what kind of agent you want to build (e.g., 'A medical assistant named MediBot').\n")

    model = get_gemini_model()
    chat = model.start_chat(history=[])
    
    current_state = {}
    
    while True:
        try:
            user_input = input(f"{GREEN}You: {RESET}").strip()
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit']:
                print("Exiting builder...")
                break

            # Send input + current context (implicitly handled by chat history, 
            # but we explicitly remind the model of the schema goal if needed, 
            # mostly the system prompt handles it).
            # To ensure state persistence, we could inject the previous JSON state, 
            # but Gemini's chat history is usually sufficient for short sessions.
            # For robustness, let's just send the user input.
            
            response = chat.send_message(user_input)
            
            try:
                response_data = json.loads(response.text)
                current_state = response_data
                
                # Extract fields
                completeness = response_data.get("completeness_score", 0)
                next_q = response_data.get("next_question", "")
                
                # Print Agent response
                if next_q and next_q != "DONE":
                    print(f"{YELLOW}Architect: {RESET}{next_q}")
                
                # Check for completion
                if completeness >= 100 or next_q == "DONE":
                    print(f"\n{BLUE}✨ Configuration Complete! generating files...{RESET}")
                    generate_files(current_state)
                    break
                    
            except json.JSONDecodeError:
                print(f"{RED}Error parsing AI response. Please try again.{RESET}")
                logger.error(f"Raw response: {response.text}")

        except KeyboardInterrupt:
            print("\nExiting...")
            break

def generate_files(data: Dict[str, Any]):
    """Generates values.yaml and other necessary files"""
    
    identity = data.get("identity", {})
    knowledge = data.get("knowledge", {})
    credentials = data.get("credentials", {})
    
    # Construct values.yaml content
    # We load the output as a dict structure compatible with the Helm chart
    
    # Map 'responseStyle' to persona definition
    response_style = knowledge.get("responseStyle", "friendly_casual")
    
    # Serialize personas to YAML string block to match Chart expectations
    personas_dict = {
        "personas": {
            "default": {
                "name": f"{identity.get('name', 'agent').lower()}_default",
                "display_name": identity.get("name", "Agent"),
                "language": "english", # Defaulting for now
                "personality_traits": ["helpful", response_style.split('_')[0]],
                "response_style": response_style,
                "restrictions": ["Never mention being an AI"]
            }
        }
    }
    
    values_content = {
        "global": {
            "orgName": knowledge.get("orgName", "My Org"),
            "environment": "production",
            "domain": "davinci.ai"
        },
        "orchestrator": {
            "image": "your-registry/davinci-orchestrator:v2", # Default
            "persona": {
                "name": identity.get("name", "Agent"),
                "introGreeting": identity.get("introGreeting", "Hello."),
                "systemPrompt": identity.get("systemPrompt", "You are a helpful agent.")
            },
            "voice": {
                "provider": "elevenlabs",
                "settings": {
                    "stability": identity.get("voiceStability", 0.5),
                    "similarity_boost": identity.get("voiceSimilarity", 0.75)
                }
            }
        },
        "rag": {
            "personas": yaml.dump(personas_dict, default_flow_style=False, sort_keys=False),
            "knowledgeBase": {
                "filenames": ["knowledge.md"],
                "content": {
                    "knowledge.md": knowledge.get("knowledgeContent", "TODO: Add knowledge base content here.")
                }
            }
        },
        "secrets": {
            "openaiApiKey": credentials.get("llmKey", ""),
            "elevenlabsApiKey": credentials.get("voiceKey", ""),
            "geminiApiKey": credentials.get("llmKey", "") # Assuming same key or user can edit
        }
    }
    
    # Write to files
    output_dir = "generated_agent"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save raw state for Executioner
    state_path = os.path.join(output_dir, "state.json")
    with open(state_path, "w") as f:
        json.dump(data, f, indent=2)

    values_path = os.path.join(output_dir, "values.yaml")
    
    # Custom YAML dumper to handle block strings nicely (optional, but standard dump is fine for now)
    with open(values_path, "w") as f:
        yaml.dump(values_content, f, default_flow_style=False, sort_keys=False)
        
    print(f"{GREEN}✓ Generated {values_path}{RESET}")
    print(f"{GREEN}✓ Saved state to {state_path}{RESET}")
    print(f"\n{BLUE}To refine your agent with advanced AI generation:{RESET}")
    print(f"agent_builder/venv/bin/python3 agent_builder/executioner.py")
    print(f"\n{BLUE}To deploy immediately:{RESET}")
    print(f"helm install my-agent ./davinci-agent-chart -f {values_path}")

if __name__ == "__main__":
    main()
