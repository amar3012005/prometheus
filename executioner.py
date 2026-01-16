
import os
import sys
import json
import logging
import yaml
import google.generativeai as genai
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("executioner")

# ANSI Colors
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

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
    
    
    # Reasoning Model for Generation
    reasoning_model_name = "gemini-3-pro-preview" 
    
    # Research Model (Deep Research failed, using Gemini 3 for research too)
    research_model_name = "gemini-3-pro-preview"

    return (
        genai.GenerativeModel(model_name=research_model_name, generation_config=generation_config),
        genai.GenerativeModel(model_name=reasoning_model_name, generation_config=generation_config)
    )

def research_organization(model, org_name: str, context: str) -> str:
    """
    Step 1: Research/Recall raw context about the organization.
    """
    print(f"{BLUE}Step 1: Researching Organization '{org_name}'...{RESET}")
    print(f"{BLUE}   Using Model: Gemini 3 Pro Preview{RESET}")
    
    prompt = f"""
You are an expert researcher.
Your goal is to recall or generate a comprehensive raw data summary about the organization "{org_name}".
Use the provided user context as a starting point, but EXPAND on it using your internal knowledge.

**USER CONTEXT:**
{context}

**INSTRUCTIONS:**
- Output a detailed, unstructured text summary.
- Include: Core mission, key services/products, target audience, typical tone, and any specific terminology.
- This will be used as raw context for an AI Agent configuration.

**OUTPUT:**
Just the raw text summary.
"""
    # For Step 1, we might not want JSON output if we want raw text thinking
    # But our model config enforces JSON. So let's ask for JSON wrapper.
    json_prompt = prompt + "\n\nReturn JSON: {\"raw_research_context\": \"...string...\"}"
    
    response = model.generate_content(json_prompt)
    try:
        data = json.loads(response.text)
        research = data.get("raw_research_context", "")
        print(f"{GREEN}✓ Research Complete ({len(research)} chars){RESET}")
        return research
    except Exception as e:
        print(f"{RED}Research failed, using provided context only.{RESET}")
        return context


def construct_mega_prompt(state: Dict[str, Any], research_context: str) -> str:
    """
    Step 2: Constructs the MEGA XML Prompt using Research Context.
    """
    identity = state.get("identity", {})
    knowledge = state.get("knowledge", {})
    
    name = identity.get("name", "Agent")
    org = knowledge.get("organizationName", "Organization")
    response_style = knowledge.get("responseStyle", "friendly_casual")
    user_tone = identity.get('greeting', '')
    basic_system_prompt = identity.get('systemPrompt', '')
    
    # If user provided a specific intro, use it as a guide, but ask for variations.
    
    prompt = f"""
You are the **Executioner v2**, an advanced AI Architect.
Your input is a researched context about "{{org}}".
Your output must be a highly detailed, production-ready configuration for the agent "{{name}}".

**RESEARCHED CONTEXT (RAW DATA):**
{{research_context}}

**USER'S BASIC INTENT:**
{{basic_system_prompt}}

**CONFIGURATION GOALS:**
- **Agent Name**: {{name}}
- **Response Style**: {{response_style}}
- **Voice/Tone**: {{user_tone}} (Use this as a baseline)

**GENERATION TASKS:**

1.  **System Prompt (Zone A XML)**:
    - Structure: `<system_configuration><agent_identity>...</agent_identity></system_configuration>`
    - Include `<behavioral_system>` with `<personality>` and `<conversation_patterns>` (at least 3 specific to the domain).
    - **CRITICAL**: Use the Research Context to define specific domain expertise in `<persona_anchor>`.
    - Include `<language_protocol>` for multi-language handling if appropriate.

2.  **Dialogue Flows**:
    - Identify key intents based on the services found in Research Context.
    - Define patterns and filler phrases.
    - **Multilingual Support**: If the domain suggests broad usage, include patterns in relevant languages.

3.  **Humanized Intros**:
    - Generate 3-5 distinct variations of the introductory greeting.
    - They should vary in length and nuance (e.g., one short/punchy, one warm/detailed, one assisting).
    - If the domain is multilingual, include a mixed-language greeting.

4.  **RAG Persona**:
    - Standard YAML structure.
    - `restrictions`: Add specific restrictions.
    - `personality_traits`: Expand on the basic list.

**OUTPUT SCHEMA:**
Return ONLY valid JSON:
{{{{
  "system_prompt": "string (the huge XML string)",
  "dialogue_flows": {{{{ ... (valid JSON object for dialogue config) ... }}}},
  "intro_variations": ["string 1", "string 2", ...],
  "personas_config": {{{{ ... (dictionary structure for personas.yaml) ... }}}}
}}}}
""".format(
    org=org, 
    name=name, 
    research_context=research_context, 
    response_style=response_style, 
    user_tone=user_tone,
    basic_system_prompt=basic_system_prompt
)
    return prompt

def main():
    print(f"{BLUE}========================================={RESET}")
    print(f"{BLUE}   Daytona Executioner v2 (Gemini 3) 🧠  {RESET}")
    print(f"{BLUE}========================================={RESET}")
    
    state_path = "generated_agent/state.json"
    if not os.path.exists(state_path):
        print(f"{RED}Error: {state_path} not found. Run builder.py first.{RESET}")
        sys.exit(1)
        
    with open(state_path, "r") as f:
        state = json.load(f)
        
    identity = state.get("identity", {})
    knowledge = state.get("knowledge", {})
    org_name = knowledge.get("organizationName", "Organization")
    
    print(f"{YELLOW}Agent: {identity.get('name')} | Org: {org_name}{RESET}")
    
    research_model, reasoning_model = get_gemini_model()
    
    from tqdm import tqdm
    import time
    
    with tqdm(total=3, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}]", colour="green") as pbar:
        
        # Step 1: Research
        pbar.set_description(f"{BLUE}Step 1: Researching Organization{RESET}")
        initial_context = knowledge.get("knowledgeContent", "")
        # We suppress inner prints or just let them show (tqdm handles stdout interception nicely usually)
        research_context = research_organization(research_model, org_name, initial_context)
        pbar.update(1)
        
        # Step 2: Generate
        pbar.set_description(f"{BLUE}Step 2: Generating Advanced Assets{RESET}")
        prompt = construct_mega_prompt(state, research_context)
        
        try:
            response = reasoning_model.generate_content(prompt)
            result = json.loads(response.text)
            pbar.update(1)
            
            # Step 3: Save and Update
            pbar.set_description(f"{BLUE}Step 3: Saving Configuration{RESET}")
            
            # Update values.yaml
            values_path = "generated_agent/values.yaml"
            with open(values_path, "r") as f:
                values = yaml.safe_load(f)
                
            # Update System Prompt
            values["orchestrator"]["persona"]["systemPrompt"] = result["system_prompt"]
            
            # Update Dialogue Flows
            values["orchestrator"]["dialogueFlows"] = json.dumps(result["dialogue_flows"], indent=2)
            
            # Handle Intros
            intros = result.get("intro_variations", [])
            if intros:
                values["orchestrator"]["persona"]["introGreeting"] = intros[0]
            
            # Update Personas
            personas = result.get("personas_config", {})
            if "personas" not in personas:
                 personas = {"personas": {"default": personas}}
            values["rag"]["personas"] = yaml.dump(personas, default_flow_style=False, sort_keys=False)
            
            with open(values_path, "w") as f:
                yaml.dump(values, f, default_flow_style=False, sort_keys=False)
                
            pbar.update(1)
            pbar.set_description(f"{GREEN}Complete!{RESET}")
                
            print(f"\n{GREEN}✨ Executioner v2 Complete!{RESET}")
            print(f"Enhanced configuration saved to {values_path}")
            if intros:
                print(f"{YELLOW}Selected Intro:{RESET} {intros[0]}")
            
        except Exception as e:
            pbar.close() # Ensure clean exit
            print(f"\n{RED}Error generating content: {e}{RESET}")

if __name__ == "__main__":
    main()
