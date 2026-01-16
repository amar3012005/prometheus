
import os
import sys
import yaml
import google.generativeai as genai

# ANSI Colors
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"
RED = "\033[91m"

def get_gemini_model():
    """Configures and returns the Gemini 2.0 Flash Lite model."""
    api_key = os.getenv("GEMINI_API_KEY") or "AIzaSyBG9nb_Xe2267oBO9s0g0jJOQtJGh47pNk"
    
    if not api_key:
        print(f"{RED}Error: GEMINI_API_KEY environment variable not set.{RESET}")
        sys.exit(1)
    
    genai.configure(api_key=api_key)
    
    # Configuration for conversation flow
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }
    
    # Using Flash Lite as requested for the test chat
    return genai.GenerativeModel(
        model_name="gemini-2.0-flash-lite",
        generation_config=generation_config,
    )

def load_agent_config():
    """Loads the agent configuration from generated_agent/values.yaml."""
    values_path = "generated_agent/values.yaml"
    if not os.path.exists(values_path):
        print(f"{RED}Error: {values_path} not found. Run builder/executioner first.{RESET}")
        sys.exit(1)
        
    with open(values_path, "r") as f:
        return yaml.safe_load(f)

def main():
    print(f"{BLUE}========================================={RESET}")
    print(f"{BLUE}   Agent Test Chat (No RAG) 💬           {RESET}")
    print(f"{BLUE}========================================={RESET}")

    # 1. Load Config
    config = load_agent_config()
    try:
        persona = config["orchestrator"]["persona"]
        system_prompt = persona["systemPrompt"]
        intro = persona.get("introGreeting", "Hello!")
        name = persona.get("name", "Agent")
    except KeyError as e:
        print(f"{RED}Error parsing values.yaml: Missing key {e}{RESET}")
        sys.exit(1)

    print(f"{YELLOW}Agent: {name}{RESET}")
    print(f"{YELLOW}System Prompt Loaded ({len(system_prompt)} chars){RESET}")
    print(f"-----------------------------------------")
    
    # 2. Init Model
    model = get_gemini_model()
    
    # 3. Start Chat Session with System Prompt
    # Note: Gemini python lib chat history usually starts empty. 
    # We inject system prompt as the first "user" message or system instruction if supported.
    # gemini-2.0-flash-lite supports system_instruction at model init, but we already init'd.
    # Let's re-init with system instruction for best results.
    
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-lite",
        system_instruction=system_prompt
    )
    
    chat = model.start_chat(history=[])
    
    # 4. Print Intro
    print(f"{GREEN}{name}: {intro}{RESET}")
    
    # 5. Chat Loop
    while True:
        try:
            user_input = input(f"{BLUE}You: {RESET}")
            if user_input.lower() in ["exit", "quit", "bye"]:
                print(f"{GREEN}{name}: Goodbye!{RESET}")
                break
            
            if not user_input.strip():
                continue
                
            response = chat.send_message(user_input)
            print(f"{GREEN}{name}: {response.text}{RESET}")
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"{RED}Error: {e}{RESET}")

if __name__ == "__main__":
    main()
