"""LLM Service - Groq Llama 3.1 8B Integration"""
from groq import Groq
from typing import Dict, Any, List
import json
import logging

from app.config import settings

logger = logging.getLogger("app.services.llm")
logger.setLevel(logging.DEBUG)

# Initialize Groq Client
client = Groq(api_key=settings.groq_api_key)

EXTRACTION_SYSTEM_PROMPT = """
You are the **PROMETHEUS Context Architect**, a meticulous expert in AI Agent design.
Your goal is to extract EXPLICIT information from the user's request.

### THE "SIDE-UPDATE" RULE:
Users often change their mind or provide a correction while answering a different question. 
- You MUST detect if the user updated OR corrected a field and report it in `metadata.updates`.

### EXTRACTION SEQUENCE (STRICT PRIORITY):
1. **GENDER & LANGUAGE**: Look for these FIRST. If the user says "A female translator for German", extract both immediately.
2. **PERSONA**: Character traits, formality, and use-case.
3. **TONE & TEXTURE**: Detailed voice descriptors (warm, professional, raspy, energetic).

### FIELD RULES:
1. `agent_type`: "organization" or "personal".
2. `org_name`: Company name or entity description.
3. `agent_name`: Explicit name (e.g., "Emma").
4. `persona_vibe`: ONLY extract if user describes character traits. Avoid defaults.
5. `voice_parameters`: Extract object IF AND ONLY IF user provides descriptors.
   - `gender`: **CRITICAL PRIORITY**. Must be "male", "female", or "neutral".
   - `accent`: Explicit accent (e.g., "german", "british").
   - `age`: "young", "middle_aged", or "old".
   - `tone`: List of adjectives describing texture (e.g., ["warm", "clear", "friendly"]).
   - `search_query`: A high-fidelity descriptive sentence for semantic search.
6. `knowledge_url`: Extract website if provided.
7. `supported_languages`: **HIGH PRIORITY**. List of codes (e.g., ["de", "en"]) if mentioned.

### CRITICAL EXTRACTION RULES:
- If user says "German female professional", extract: gender=female, accent=german, tone=["professional"].
- If user says "warm British male", extract: gender=male, accent=british, tone=["warm"].
- ALWAYS extract language codes from language names (German=de, English=en, Spanish=es, French=fr).

### OUTPUT FORMAT (JSON):
{
    "extracted": {
        "agent_type": "...",
        "org_name": "...",
        "agent_name": "...",
        "persona_vibe": "...",
        "voice_parameters": {...},
        "knowledge_url": "...",
        "supported_languages": [...]
    },
    "metadata": {
        "updates": ["List of updated fields"],
        "confidence": 0.0-1.0
    }
}
"""

CLARIFICATION_SYSTEM_PROMPT = """
You are the **PROMETHEUS Architect**, a premium AI agent designer.

### CURRENT CONTEXT:
{current_context}

### MISSING FIELD:
{missing_fields}

### RULES:
1. Ask ONE short question about the missing field.
2. Use **bold** for names, organizations, or key terms.
3. Keep response under 2 sentences. Be warm and friendly.
4. Suggest 4 clickable options relevant to the field.

### FIELD-SPECIFIC PROMPTS:
- **agent_name**: "What should we call your agent? Here are some ideas:"
- **voice_parameters**: "How should **[agent_name]** sound? Pick a voice style:"
- **persona_vibe**: "What personality should **[agent_name]** have?"
- **org_name**: "What company or project is this agent for?"

### OUTPUT (JSON):
{{
    "message": "Your short, friendly question with **bold** highlights.",
    "suggestions": ["Option 1", "Option 2", "Option 3", "Option 4"]
}}
"""

GENERATION_SYSTEM_PROMPT = """
You are the **PROMETHEUS Code Generator**. Your goal is to generate the high-resolution core of the agent.

## SPECIFICATION:
{spec}

## THE PRIME DIRECTIVE:
USER INSTRUCTIONS OVERRIDE EVERYTHING. If the user provided a specific constraint, it is LAW.

## OUTPUT REQUIREMENTS:
1. **system_prompt**: A comprehensive, conversational, and multi-language capable prompt. 
   - include a `LANGUAGE_PROTOCOL` section for auto-detection.
   - include a `PERSONALITY` section matching the vibe.
2. **knowledge_content**: A 500+ word logical breakdown of the organization/entity in Markdown.
3. **intro_greeting**: A warm greeting in the primary language.
4. **dialogue_flows**: Intents and patterns.
5. **elevenlabs_mapping**: Specific fields for the ElevenLabs template.

OUTPUT FORMAT (JSON):
{{
    "agent_name": "...",
    "system_prompt": "...",
    "knowledge_content": "...",
    "intro_greeting": "...",
    "dialogue_flows": {{
        "intents": [...],
        "filler_latency": [...]
    }},
    "elevenlabs_overrides": {{
        "temperature": 0.0-1.0,
        "stability": 0.0-1.0,
        "similarity_boost": 0.0-1.0
    }}
}}
"""

async def extract_context(user_message: str, conversation_history: List[Dict[str, str]], current_fields: Dict[str, Any] = None) -> Dict[str, Any]:
    """Extract agent configuration fields from user message."""
    
    # Build context from history
    history_text = "\n".join([
        f"{msg['role']}: {msg['content']}" 
        for msg in conversation_history[-5:]  # Last 5 messages
    ])
    
    # Build already-extracted fields context
    already_extracted = ""
    if current_fields:
        filled = {k: v for k, v in current_fields.items() if v is not None and v != ""}
        if filled:
            already_extracted = f"""
ALREADY EXTRACTED (DO NOT OVERWRITE with null - these are CONFIRMED):
{json.dumps(filled, indent=2)}

IMPORTANT: If a field is already extracted above, you MUST return the same value for it.
Only extract NEW fields or update fields that the user explicitly provides new values for.
"""
    
    prompt = f"""
{EXTRACTION_SYSTEM_PROMPT}

{already_extracted}

CONVERSATION HISTORY:
{history_text}

LATEST USER MESSAGE:
{user_message}

Extract the configuration fields:
"""

    logger.info("[LLM] 🛰️ Calling Groq (Llama 3.1 8B) for extraction...")
    
    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=settings.llm_temperature,
            response_format={"type": "json_object"}
        )
        text = response.choices[0].message.content
        logger.debug(f"[LLM] Raw response: {text}")
        result = json.loads(text)
        
        if not isinstance(result, dict):
            logger.error(f"Unexpected result type: {type(result)}")
            return {"extracted": {}, "confidence": 0.0}

        logger.info(f"Extraction result: {result}")
        return result
    except Exception as e:
        logger.error(f"Extraction failed: {type(e).__name__}: {e}")
        return {"extracted": {}, "confidence": 0.0}

async def generate_clarification(missing_fields: List[str], current_context: Dict[str, Any], updates: List[str] = None) -> Dict[str, Any]:
    """Generate a clarifying question for missing fields."""
    
    context_with_updates = {
        "fields": current_context,
        "metadata": {"updates": updates or []}
    }
    
    prompt = CLARIFICATION_SYSTEM_PROMPT.format(
        missing_fields=", ".join(missing_fields),
        current_context=json.dumps(context_with_updates, indent=2)
    )
    
    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        return {
            "message": data.get("message", f"I need a bit more info about the {missing_fields[0]}."),
            "suggestions": data.get("suggestions", [])
        }
    except Exception as e:
        logger.error(f"Clarification generation failed: {e}")
        return {
            "message": f"I need a bit more info. Can you tell me more about the {missing_fields[0]}?",
            "suggestions": []
        }

async def generate_artifacts(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Generate full agent configuration artifacts."""
    
    prompt = GENERATION_SYSTEM_PROMPT.format(spec=json.dumps(spec, indent=2))
    
    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=settings.llm_temperature,
            response_format={"type": "json_object"}
        )
        text = response.choices[0].message.content
        result = json.loads(text)
        logger.info(f"Generated artifacts: {list(result.keys())}")
        return result
    except Exception as e:
        logger.error(f"Artifact generation failed: {e}")
        # Return minimal fallback
        return {
            "system_prompt": f"You are {spec.get('agent_name', 'an AI assistant')} for {spec.get('org_name', 'the organization')}.",
            "intro_greeting": f"Hello! I'm {spec.get('agent_name', 'your assistant')}. How can I help?",
            "knowledge_content": f"# Knowledge Base for {spec.get('agent_name', 'Agent')}\n\nOrganization: {spec.get('org_name', 'Organization')}\n\n## About\nGeneral knowledge about {spec.get('org_name', 'the organization')}.",
            "dialogue_flows": {"intents": [], "filler_latency": []},
            "rag_persona": {
                "name": spec.get("agent_name", "agent").lower(),
                "display_name": spec.get("agent_name", "Agent"),
                "personality_traits": ["helpful"],
                "response_style": spec.get("persona_vibe", "casual"),
                "restrictions": []
            }
        }

async def rerank_voices(
    voice_candidates: List[Dict[str, Any]], 
    agent_context: Dict[str, Any]
) -> List[str]:
    """
    Use Gemini as a 'Voice Casting Director' to re-rank voice candidates.
    
    Args:
        voice_candidates: List of 10 voice dicts from ElevenLabs
        agent_context: Original agent spec (org_name, agent_name, persona, etc.)
    
    Returns:
        List of top 3 voice_ids ranked by brand fit
    """
    
    # Build simplified candidate list for Gemini
    candidate_summaries = []
    for i, voice in enumerate(voice_candidates, 1):
        summary = f"{i}. {voice['name']} (ID: {voice['voice_id']})\n"
        summary += f"   Category: {voice.get('category', 'N/A')}\n"
        summary += f"   Description: {voice.get('description', 'N/A')}\n"
        if voice.get('labels'):
            summary += f"   Tags: {', '.join([f'{k}: {v}' for k, v in voice['labels'].items()])}\n"
        candidate_summaries.append(summary)
    
    candidates_text = "\n".join(candidate_summaries)
    
    # Build agent brief
    agent_brief = f"""
AGENT SPECIFICATION:
- Organization: {agent_context.get('org_name', 'N/A')}
- Agent Name: {agent_context.get('agent_name', 'N/A')}
- Persona: {agent_context.get('persona_vibe', 'N/A')}
- Voice Requirements: {agent_context.get('voice_parameters', {}).get('search_query', 'N/A')}
- Use Case: {agent_context.get('system_prompt_hints', 'N/A')}
"""
    
    prompt = f"""
You are the **PROMETHEUS Voice Architect**, an elite casting director for high-performance AI Agents. 
Your mission: Select the Top 3 voices from the provided library that perfectly embody the agent's unique brand identity and linguistic requirements.

{agent_brief}
TARGET LANGUAGES: {agent_context.get('supported_languages', ['en'])}

### VOICE CANDIDATES FROM ELEVENLABS LIBRARY:
{candidates_text}

### SELECTION PROTOCOL (PRIORITY HIERARCHY):
1. **Linguistic Authenticity**: The voice MUST sound like a native speaker of the primary target language. For international brands (e.g., European), prioritize voices with labels verifying that specific language proficiency.
2. **Brand-Persona Vibe Alignment**: 
   - If Persona is 'Flirty/Sexy/Alluring': Prioritize descriptions like 'sultry', 'breathy', 'warm', 'soft', or 'raspy'.
   - If Persona is 'Professional/Corporate/Expert': Prioritize 'clear', 'authoritative', 'articulate', or 'formal'.
   - If Persona is 'Friendly/Casual/Companion': Prioritize 'cheerful', 'approachable', 'young', or 'conversational'.
3. **Accent Sensitivity**: Strictly avoid "Generic American" accents for European, British, or Australian roles unless the 'Voice Requirements' explicitly demand it.
4. **Vocal Texture**: Prefer 'Professional' or 'Premier' grade voices. Pay attention to labels like 'warbly' or 'nasal' and avoid them unless they fit a specific "Character" role.

### OUTPUT SPECIFICATION:
- Return a JSON array of the top 3 raw `voice_id` strings.
- Rank from index 0 (Perfect Match) to 2 (Strong Alternative).
- Do NOT include names, reasoning, or markdown formatting. Just the raw array of strings.

Format: ["id_1", "id_2", "id_3"]
"""
    
    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # Strict adherence to constraints
            response_format={"type": "json_object"}
        )
        
        text = response.choices[0].message.content
        logger.debug(f"[VOICE RE-RANK] Raw output: {text}")
        
        data = json.loads(text)
        
        # Groq might wrap the list in an object if we asked for json_object
        # The prompt says: Return a JSON array. If it's an object with a key, find the list.
        if isinstance(data, dict):
            for val in data.values():
                if isinstance(val, list):
                    data = val
                    break

        # Ensure we only have a list of strings
        if not isinstance(data, list):
            logger.warning("[VOICE RE-RANK] LLM did not return a list. Attempting fallback.")
            return [v["voice_id"] for v in voice_candidates[:3]]

        # Clean IDs and filter out any non-id strings
        final_ids = []
        for item in data:
            if isinstance(item, str):
                # Remove any accidental descriptions (e.g., "id - name")
                clean_id = item.split(' ')[0].split('-')[0].strip('()')
                if clean_id and clean_id in [v["voice_id"] for v in voice_candidates]:
                    final_ids.append(clean_id)
        
        logger.info(f"[VOICE RE-RANK] Final Selection: {final_ids[:3]}")
        return final_ids[:3] if final_ids else [v["voice_id"] for v in voice_candidates[:3]]
        
    except Exception as e:
        logger.error(f"Voice re-ranking failed: {e}")
        return [v["voice_id"] for v in voice_candidates[:3]]
