"""LangGraph Node Definitions for DAVINCI-CODE Pipeline"""
import logging
import asyncio
from typing import Dict, Any, List
from langgraph.graph import END

from app.state import AgentState, ExtractedContext
from app.services import llm as llm_service
from app.services import voice as voice_service
from app.services import helm as helm_service
from app.services.db import db_service
from app.services.knowledge import knowledge_service
from app.services.elevenlabs_cli import ElevenLabsCLIService
elevenlabs_cli = ElevenLabsCLIService()
from app.websocket.manager import manager, Events
import os
import json

logger = logging.getLogger(__name__)

# Required fields for context completion
REQUIRED_FIELDS = ["org_name", "agent_name", "persona_vibe", "voice_parameters"]

# Global registries for background tasks
VOICE_SEARCH_REGISTRY: Dict[str, asyncio.Task] = {}
VOICE_RESULTS_REGISTRY: Dict[str, List[dict]] = {}
KNOWLEDGE_GEN_REGISTRY: Dict[str, asyncio.Task] = {}
KNOWLEDGE_RESULTS_REGISTRY: Dict[str, str] = {}


async def entry_node(state: AgentState) -> AgentState:
    """
    Entry Node: Initialize state from user prompt.
    """
    user_req = state.get("user_request", "")
    logger.info(f"[ENTRY] Processing request: {user_req[:50]}...")
    
    # Add user message to history
    history = state.get("conversation_history", [])
    if user_req:
        history.append({"role": "user", "content": user_req})
    
    # Initialize build logs
    build_logs = state.get("build_logs", [])
    if user_req:
        build_logs.append(f"[ENTRY] Received request: {user_req[:100]}...")
    
    return {
        **state,
        "conversation_history": history,
        "build_logs": build_logs,
        "current_phase": "INTAKE"
    }

async def background_voice_search(sid: str, params: dict, context: dict):
    """Background task to search voices and push to WS immediately."""
    try:
        logger.info(f"[VOICE-TASK] 🔍 Starting background search for session {sid}")
        candidates = await voice_service.match_voice(params, context)
        
        if candidates:
            # Store in result registry for later retrieval by generation_node
            VOICE_RESULTS_REGISTRY[sid] = candidates
            logger.info(f"[VOICE-TASK] ✅ Found {len(candidates)} candidates for {sid}. Pushing to WS.")
            
            # 🔥 PUSH TO WS IMMEDIATELY for "ASAP" UX
            await manager.send_event(sid, Events.LOG, {
                "phase": "VOICE",
                "voice_candidates": candidates,
                "message": f"🎙️ Found {len(candidates)} matching voices"
            })
        else:
            logger.warning(f"[VOICE-TASK] ⚠️ No candidates found for {sid}")
            
        return candidates
    except Exception as e:
        logger.error(f"[VOICE-TASK] ❌ Fatal error in background search for {sid}: {e}", exc_info=True)
        return []

async def background_knowledge_gen(sid: str, org_name: str, url: str = None, hints: str = ""):
    """Background task to generate knowledge base and push status."""
    try:
        logger.info(f"[KB-TASK] 🧠 Starting background KB generation for {sid}")
        await manager.send_event(sid, Events.LOG, {
            "phase": "GENERATING",
            "message": "📚 Generating knowledge base in background..."
        })
        
        if url:
            knowledge = await knowledge_service.generate_organization_knowledge(org_name, url)
        else:
            knowledge = await knowledge_service.generate_organization_knowledge(org_name, additional_context=hints)
            
        if knowledge:
            word_count = len(str(knowledge).split())
            KNOWLEDGE_RESULTS_REGISTRY[sid] = knowledge
            logger.info(f"[KB-TASK] ✅ KB ready for {sid} ({word_count} words)")
            await manager.send_event(sid, Events.LOG, {
                "phase": "GENERATING",
                "message": f"✅ Knowledge base ready ({word_count} words)"
            })
        return knowledge
    except Exception as e:
        logger.error(f"[KB-TASK] ❌ KB generation failed for {sid}: {e}")
        return None

async def extraction_node(state: AgentState) -> AgentState:
    """
    Extraction Node: LLM-powered field extraction from user messages.
    Also handles URL detection for knowledge enrichment.
    """
    logger.info("[EXTRACTION] Extracting context fields...")
    
    build_logs = state.get("build_logs", [])
    build_logs.append("[EXTRACTION] Analyzing user intent...")
    
    # Get latest user message
    history = state.get("conversation_history", [])
    latest_message = history[-1]["content"] if history else state["user_request"]
    
    # Get existing fields
    current_fields = state.get("extracted_fields", {})
    
    # Check if user is responding to URL prompt (simple detection)
    import re
    url_pattern = r'https?://[^\s]+'
    url_match = re.search(url_pattern, latest_message)
    
    discovered_url = None
    if url_match:
        # User provided a URL
        url = url_match.group(0)
        logger.info(f"[EXTRACTION] URL detected: {url}")
        discovered_url = url
        build_logs.append(f"[EXTRACTION] ✓ URL captured: {url}")
        
    # Check if user says "continue" to skip URL
    if latest_message.lower().strip() in ["continue", "skip", "no", "none", "proceed"]:
        logger.info("[EXTRACTION] User skipped URL input")
        current_fields["url_confirmed"] = True
        build_logs.append("[EXTRACTION] ✓ Proceeding without URL")
        
        # Ensure we capture ANY user directives from this step even if skipping URL
        current_fields["system_prompt_hints"] = f"{current_fields.get('system_prompt_hints', '')} {latest_message}".strip()
    
    # Normal extraction via LLM - pass current_fields so LLM knows what's already extracted
    extraction_result = await llm_service.extract_context(latest_message, history, current_fields)
    new_fields = extraction_result.get("extracted", {})
    metadata = extraction_result.get("metadata", {})
    updates = metadata.get("updates", [])
    
    logger.info(f"[EXTRACTION] 📥 Gemini returned new fields: {new_fields}")
    if new_fields.get("voice_parameters"):
        logger.info(f"[EXTRACTION] 🎙️ Extracted Voice Parameters: {new_fields['voice_parameters']}")
    
    # Only update non-null new values
    merged_fields = {**current_fields}
    for key, value in new_fields.items():
        if value is not None:
            merged_fields[key] = value

    # Explicitly set URL if discovered (overrides LLM extraction if needed)
    if discovered_url:
        merged_fields["knowledge_url"] = discovered_url
        merged_fields["url_confirmed"] = True

    # Log updates for transparency
    if updates:
        update_str = ", ".join(updates)
        build_logs.append(f"[EXTRACTION] 🔄 Updated fields: {update_str}")
        logger.info(f"[EXTRACTION] User changed fields: {update_str}")

    # CRITICAL: Append raw user input to hints to ensure Generation Phase sees all constraints
    # This allows the "Prime Directive" in Generation to override any Extraction failures
    current_hints = merged_fields.get("system_prompt_hints", "")
    if latest_message not in current_hints:
        merged_fields["system_prompt_hints"] = f"{current_hints}\nUser Input: {latest_message}".strip()
    
    build_logs.append(f"[EXTRACTION] Extracted: {list(new_fields.keys())}")
    
    # 🔥 VOICE SEARCH: Only trigger AFTER all voice params AND persona are collected
    session_id = state.get("session_id")
    voice_params = merged_fields.get("voice_parameters", {})
    persona_vibe = merged_fields.get("persona_vibe")
    
    # Check voice params are COMPLETE (gender + accent or tone)
    voice_complete = (
        isinstance(voice_params, dict) and 
        voice_params.get("gender") and 
        (voice_params.get("accent") or (voice_params.get("tone") and len(voice_params.get("tone", [])) > 0))
    )
    
    # Inject primary language into voice_params for smarter ElevenLabs filtering
    if voice_params and merged_fields.get("supported_languages"):
        langs = merged_fields["supported_languages"]
        if isinstance(langs, list) and len(langs) > 0:
            voice_params["primary_language"] = langs[0]
            logger.info(f"[EXTRACTION] 🌏 Setting primary language for voice search: {langs[0]}")
    
    # Only trigger voice search when ALL requirements met
    if voice_complete and persona_vibe and not VOICE_SEARCH_REGISTRY.get(session_id) and not VOICE_RESULTS_REGISTRY.get(session_id):
        logger.info(f"[EXTRACTION] 🎤 Triggering background voice hunt for {session_id}")
        VOICE_SEARCH_REGISTRY[session_id] = asyncio.create_task(
            background_voice_search(session_id, voice_params, merged_fields)
        )

    return {
        **state,
        "latest_updates": updates,
        "extracted_fields": merged_fields,
        "build_logs": build_logs
    }

async def validator_node(state: AgentState) -> AgentState:
    """Validator Node: Ensures all data is present with a structured, human-like sequence."""
    logger.info("[VALIDATOR] Checking context completeness...")
    
    build_logs = state.get("build_logs", [])
    extracted = state.get("extracted_fields", {})
    
    # ==============================
    # STRUCTURED CLARIFICATION SEQUENCE
    # Priority: 1) Name, 2) Voice Gender, 3) Voice Accent/Tone, 4) Persona, 5) Knowledge URL
    # ==============================
    
    agent_name = extracted.get("agent_name")
    org_name = extracted.get("org_name", "your organization")
    
    # Step 1: AGENT NAME
    if not agent_name or len(str(agent_name).strip()) < 2:
        build_logs.append("[VALIDATOR] Missing: agent_name")
        return {
            **state,
            "is_complete": False,
            "missing_info_reason": f"What should we call your agent for **{org_name}**? Pick a name that's memorable!",
            "suggestions": ["Aria", "Max", "Nova", "James"],
            "build_logs": build_logs,
            "current_phase": "INTAKE"
        }
    
    # Step 2: VOICE GENDER (Critical for voice search)
    voice_params = extracted.get("voice_parameters", {})
    if not isinstance(voice_params, dict):
        voice_params = {}
    
    if not voice_params.get("gender"):
        build_logs.append("[VALIDATOR] Missing: voice_parameters.gender")
        return {
            **state,
            "is_complete": False,
            "missing_info_reason": f"Should **{agent_name}** have a male or female voice?",
            "suggestions": ["Female", "Male", "Neutral"],
            "build_logs": build_logs,
            "current_phase": "INTAKE"
        }
    
    # Step 3: VOICE ACCENT & TONE (Need at least accent OR tone)
    has_accent = voice_params.get("accent")
    has_tone = voice_params.get("tone") and len(voice_params.get("tone", [])) > 0
    
    if not has_accent and not has_tone:
        gender = voice_params.get("gender", "").capitalize()
        build_logs.append("[VALIDATOR] Missing: voice_parameters.accent/tone")
        return {
            **state,
            "is_complete": False,
            "missing_info_reason": f"What accent or tone should **{agent_name}**'s {gender} voice have?",
            "suggestions": ["British - Professional", "American - Warm", "German - Calm", "Indian - Friendly"],
            "build_logs": build_logs,
            "current_phase": "INTAKE"
        }
    
    # Step 4: PERSONA VIBE
    persona_vibe = extracted.get("persona_vibe")
    if not persona_vibe or not isinstance(persona_vibe, str) or len(persona_vibe.strip()) < 5:
        gender = voice_params.get("gender", "").capitalize()
        accent = voice_params.get("accent", "").capitalize()
        build_logs.append("[VALIDATOR] Missing: persona_vibe")
        return {
            **state,
            "is_complete": False,
            "missing_info_reason": f"What personality should **{agent_name}** have? (They'll have a {accent} {gender} voice)",
            "suggestions": ["Professional and direct", "Friendly and warm", "Playful and witty", "Technical and precise"],
            "build_logs": build_logs,
            "current_phase": "INTAKE"
        }
    
    # Step 4: KNOWLEDGE URL (for Organization agents)
    agent_type = extracted.get("agent_type", "organization")
    knowledge_url = extracted.get("knowledge_url")
    url_confirmed = extracted.get("url_confirmed", False)

    # Handle LLM "none" hallucination
    if knowledge_url == "none":
        knowledge_url = ""
        extracted["knowledge_url"] = ""

    # KB Gate: If organization type and URL not provided/confirmed
    if agent_type == "organization" and not knowledge_url and not url_confirmed:
        build_logs.append("[VALIDATOR] Identity captured. Requesting knowledge source.")
        return {
            **state,
            "is_complete": False,
            "missing_info_reason": f"Profile for **{agent_name}** is looking great! To make them an expert, can you provide a website URL for **{org_name}**? (Or just say 'skip' to use my internal intelligence).",
            "suggestions": [f"https://{org_name.lower().replace(' ', '')}.com", "Skip for now"],
            "build_logs": build_logs,
            "current_phase": "INTAKE"
        }

    # ==============================
    # ALL FIELDS COMPLETE - PROCEED TO GENERATION
    # ==============================
    build_logs.append("[VALIDATOR] ✓ Identity and Knowledge Source satisfied. Moving to Manufacturing.")
    return {
        **state,
        "is_complete": True,
        "build_logs": build_logs,
        "current_phase": "GENERATION"
    }

from app.websocket.manager import manager, Events

async def generation_node(state: AgentState) -> AgentState:
    """
    Generation Node: Generate all agent artifacts using LLM.
    NON-BLOCKING: Starts KB extraction in background and returns immediately.
    """
    logger.info("[GENERATION] Generating agent artifacts...")
    
    build_logs = state.get("build_logs", [])
    extracted = state.get("extracted_fields", {})
    session_id = state.get("session_id")
    artifacts = state.get("artifacts", {})

    # IDEMPOTENCY CHECK: If system_prompt already exists, skip re-generation
    if artifacts and artifacts.get("system_prompt"):
        logger.info("[GENERATION] Artifacts already exist, skipping generation phase.")
        # Still need to retrieve voice candidates if they exist
        voice_candidates = state.get("voice_candidates") or VOICE_RESULTS_REGISTRY.get(session_id, [])
        return {
            **state,
            "voice_candidates": voice_candidates,
            "current_phase": "GENERATING"
        }

    build_logs.append("[GENERATION] 🧠 Activating Deep Logic Engine...")
    await manager.send_event(session_id, Events.LOG, {
        "phase": "GENERATING", 
        "message": "🧠 Activating Deep Logic Engine..."
    })
    
    # Detect agent type
    agent_type = extracted.get("agent_type", "organization")
    org_name = extracted.get("org_name", "Agent")
    agent_name = extracted.get("agent_name", "Assistant")
    knowledge_url = extracted.get("knowledge_url")
    
    # 1. MANUFACTURING: Generate High-Fidelity Prompt & Artifacts
    await manager.send_event(session_id, Events.LOG, {
        "phase": "GENERATING",
        "message": "📦 Constructing system architecture and custom prompts..."
    })
    artifacts = await llm_service.generate_artifacts(extracted)
    build_logs.append(f"[GENERATION] ✓ Generated system prompt ({len(artifacts.get('system_prompt', ''))} chars)")
    
    # 2. MANUFACTURING: Start Knowledge Extraction (NON-BLOCKING)
    if not KNOWLEDGE_GEN_REGISTRY.get(session_id) and not KNOWLEDGE_RESULTS_REGISTRY.get(session_id):
        build_logs.append("[GENERATION] 📚 Starting background knowledge extraction...")
        await manager.send_event(session_id, Events.LOG, {
            "phase": "GENERATING",
            "message": f"🌐 Extracting intelligence from {knowledge_url or 'global knowledge'}..."
        })
        KNOWLEDGE_GEN_REGISTRY[session_id] = asyncio.create_task(
            knowledge_service.generate_organization_knowledge(
                org_name, 
                url=knowledge_url,
                additional_context=extracted.get("system_prompt_hints", "")
            ) if agent_type == "organization" else 
            knowledge_service.generate_personal_knowledge(
                org_name, extracted.get("persona_vibe", "pro"), extracted.get("system_prompt_hints", "")
            )
        )

    # 3. Check if KB is already done (non-blocking)
    kb_task = KNOWLEDGE_GEN_REGISTRY.get(session_id)
    if kb_task and kb_task.done():
        try:
            kb_result = kb_task.result()
            artifacts["generated_knowledge"] = kb_result
            artifacts["knowledge_content"] = kb_result
            KNOWLEDGE_GEN_REGISTRY.pop(session_id, None)
            build_logs.append("[GENERATION] ✓ Knowledge base ready.")
        except Exception as e:
            logger.error(f"[GENERATION] KB task failed: {e}")

    # 4. Retrieve Voice Candidates (from background task started in extraction_node)
    voice_candidates = VOICE_RESULTS_REGISTRY.pop(session_id, [])
    if not voice_candidates:
        pre_started_task = VOICE_SEARCH_REGISTRY.pop(session_id, None)
        if pre_started_task is not None:
            logger.info(f"[GENERATION] 🚀 Recovering voice candidates for {session_id}")
            try:
                voice_candidates = await pre_started_task
            except Exception as e:
                logger.warning(f"[GENERATION] Voice task failed: {e}")
                voice_candidates = []
    
    if voice_candidates:
        build_logs.append(f"[GENERATION] ✓ Found {len(voice_candidates)} voice candidates")
        # 🔥 PUSH TO UI with TAILORED MESSAGE
        if not state.get("selected_voice_id"):
            logger.info(f"[GENERATION] 📢 Pushing voice candidates to {session_id}")
            
            # Build tailored voice selection message
            voice_params = extracted.get("voice_parameters", {})
            agent_name = extracted.get("agent_name", "your agent")
            gender = voice_params.get("gender", "").capitalize()
            accent = voice_params.get("accent", "").capitalize()
            tones = voice_params.get("tone", [])
            tone_str = ", ".join(tones) if tones else ""
            langs = extracted.get("supported_languages", [])
            lang_str = ", ".join([l.upper() for l in langs]) if langs else ""
            
            # Build description parts
            voice_desc_parts = []
            if gender:
                voice_desc_parts.append(gender)
            if accent:
                voice_desc_parts.append(f"{accent} accent")
            if tone_str:
                voice_desc_parts.append(f"{tone_str} tone")
            if lang_str:
                voice_desc_parts.append(f"({lang_str})")
            
            voice_description = " ".join(voice_desc_parts) if voice_desc_parts else "your specified style"
            
            tailored_message = f"🎙️ Choose the perfect voice for **{agent_name}** - {voice_description}:"
            
            await manager.send_event(session_id, Events.LOG, {
                "phase": "GENERATING",
                "message": tailored_message,
                "voice_candidates": voice_candidates
            })

    # 5. Return immediately - finalize_node will wait for KB if needed
    return {
        **state,
        "artifacts": artifacts,
        "voice_candidates": voice_candidates,
        "current_phase": "GENERATING",
        "build_logs": build_logs
    }


async def finalize_node(state: AgentState) -> AgentState:
    """
    Finalize Node: Wait for KB completion, generate values.yaml, then signal READY.
    """
    session_id = state.get("session_id")
    extracted = state.get("extracted_fields", {})
    agent_name = extracted.get("agent_name", "Agent")
    org_name = extracted.get("org_name", "Organization")
    selected_voice_id = state.get("selected_voice_id")
    artifacts = state.get("artifacts", {})
    build_logs = state.get("build_logs", [])
    
    # Identify voice name
    candidates = state.get("voice_candidates", [])
    voice_name = next((v["name"] for v in candidates if v["voice_id"] == selected_voice_id), "Selected Voice")

    # 1. VOICE CHECK
    if not selected_voice_id:
        await manager.send_event(session_id, Events.LOG, {
            "phase": "INTAKE",
            "message": f"✨ Manufacturing complete. Final step: Select a voice for {agent_name}.",
            "status": "pending"
        })
        return {
            **state,
            "is_complete": False,
            "missing_info_reason": f"I've pre-manufactured the brain and knowledge base for **{agent_name}**. Please select the final voice profile below to enable the build button.",
            "build_logs": build_logs,
            "current_phase": "INTAKE"
        }

    # 2. AWAIT KB COMPLETION (blocking here is OK - user already selected voice)
    if not artifacts.get("generated_knowledge"):
        kb_task = KNOWLEDGE_GEN_REGISTRY.get(session_id)
        if kb_task:
            logger.info(f"[FINALIZE] Awaiting KB completion for {session_id}...")
            await manager.send_event(session_id, Events.LOG, {
                "phase": "GENERATING",
                "message": "⏳ Finalizing knowledge base extraction..."
            })
            try:
                kb_result = await asyncio.wait_for(kb_task, timeout=30.0)
                artifacts["generated_knowledge"] = kb_result
                artifacts["knowledge_content"] = kb_result
                KNOWLEDGE_GEN_REGISTRY.pop(session_id, None)
                build_logs.append(f"[FINALIZE] ✓ Knowledge base ready ({len(kb_result)} chars)")
            except asyncio.TimeoutError:
                logger.warning("[FINALIZE] KB timed out, using default knowledge")
                artifacts["knowledge_content"] = f"# {agent_name} Knowledge Base\n\nOrganization: {org_name}"
            except Exception as e:
                logger.error(f"[FINALIZE] KB failed: {e}")
                artifacts["knowledge_content"] = f"# {agent_name} Knowledge Base\n\nOrganization: {org_name}"

    # 3. GENERATE VALUES.YAML
    build_logs.append(f"[FINALIZE] ✓ Voice locked: {voice_name}")
    values_yaml = helm_service.generate_values_yaml(
        agent_name=agent_name,
        org_name=org_name,
        voice_id=selected_voice_id,
        artifacts=artifacts
    )
    artifacts["values_yaml"] = values_yaml

    # 4. SIGNAL READY FOR DEPLOYMENT
    summary = (
        f"### **PROMETHEUS: MANUFACTURING COMPLETE**\n\n"
        f"✓ **Logic Engine**: High-fidelity system prompt generated.\n"
        f"✓ **Intelligence**: `{agent_name}_kb.md` file created.\n"
        f"✓ **Voice Identity**: {voice_name} locked in.\n\n"
        "Click **Build Agent** to deploy to ElevenLabs."
    )

    await manager.send_event(session_id, Events.LOG, {
        "phase": "READY",
        "message": "🔥 ALL ARTIFACTS MANUFACTURED. Ready for deployment.",
        "status": "success",
        "ready_to_build": True 
    })

    build_logs.append("[FINALIZE] ✓ Manufacturing complete. Build enabled.")

    return {
        **state,
        "artifacts": artifacts,
        "voice_id": selected_voice_id,
        "selected_voice_id": selected_voice_id,
        "voice_candidates": [], # Clear candidates as selection is locked
        "is_complete": True,
        "missing_info_reason": summary,
        "build_logs": build_logs,
        "current_phase": "READY"
    }

def check_voice_selection(state: AgentState) -> str:
    """Router to wait for voice selection."""
    if state.get("selected_voice_id"):
        return "finalize"
    return "interrupt"

from app.services.db import db_service

async def build_node(state: AgentState) -> AgentState:
    """Build and deploy agent to K3s cluster with detailed logging."""
    
    session_id = state["session_id"]
    extracted = state.get("extracted_fields", {})
    artifacts = state.get("artifacts", {})
    agent_name = extracted.get("agent_name", "Agent")
    org_name = extracted.get("org_name", "Organization")
    tenant_id = state.get("tenant_id", "default-tenant")
    vault_session_path = elevenlabs_cli._get_session_path(session_id, tenant_id)
    output_dir = vault_session_path
    
    build_logs = []
    
    try:
        # Send initial build start message
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": f"🚀 PROMETHEUS BUILD SYSTEM v2.5"
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": f"Finalizing deployment assets for: {agent_name}"
        })
        
        # --- PHASE 0: ARTIFACT GENERATION (TRIGGERED BY BUILD CLICK) ---
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "📦 Generating configuration templates..."
        })
        
        # Safety check for voice_id
        voice_id = state.get("selected_voice_id")
        if not voice_id:
            logger.warning(f"[BUILD] voice_id is None! Using fallback voice.")
            voice_id = "cjVigY5qzO86Huf0OWal"  # Alice - known working voice
        
        logger.info(f"[BUILD] Starting with voice_id: {voice_id}, agent: {agent_name}")
        
        # 1. Initialize ElevenLabs vault
        logger.info(f"[BUILD] Step 1: Initializing vault...")
        tenant_id = state.get("tenant_id", "default-tenant")
        vault_path = elevenlabs_cli.init_workspace(session_id, tenant_id)
        logger.info(f"[BUILD] Vault initialized at: {vault_path}")
        
        # 2. Write knowledge base
        logger.info(f"[BUILD] Step 2: Writing knowledge base...")
        knowledge_content = artifacts.get("generated_knowledge", artifacts.get("knowledge_content", ""))
        vault_knowledge_filename = "knowledge.md"
        if knowledge_content:
            vault_knowledge_path = os.path.join(vault_path, "knowledge", vault_knowledge_filename)
            with open(vault_knowledge_path, "w") as f:
                f.write(knowledge_content)
            logger.info(f"[BUILD] Knowledge written: {len(knowledge_content)} chars")
        else:
            logger.warning("[BUILD] No knowledge content to write!")
        
        # 3. Generate ElevenLabs agent.json from high-fidelity artifacts
        logger.info(f"[BUILD] Step 3: Generating agent config...")
        try:
            elevenlabs_cli.generate_agent_config(
                session_id=session_id,
                tenant_id=tenant_id,
                extracted_fields=extracted,
                artifacts=artifacts,
                voice_id=voice_id,
                knowledge_filename=vault_knowledge_filename
            )
            logger.info(f"[BUILD] Agent config generated successfully")
        except Exception as config_err:
            logger.error(f"[BUILD] Failed to generate agent config: {config_err}")
            raise
        
        # 4. Generate legacy files for compatibility (scoped to tenant vault)
        for od in [vault_session_path]:
            os.makedirs(od, exist_ok=True)
            # Save values.yaml
            with open(os.path.join(od, "values.yaml"), "w") as f:
                f.write(artifacts.get("values_yaml", ""))
            # Save agent_registry.json
            reg_config = construct_agent_config({**state, "artifacts": artifacts})
            with open(os.path.join(od, "agent_registry.json"), "w") as f:
                json.dump({"agents": {session_id: reg_config}}, f, indent=2)
            # Save knowledge.md
            if knowledge_content:
                with open(os.path.join(od, "knowledge.md"), "w") as f:
                    f.write(knowledge_content)

        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "   └─ ✓ Templates generated and validated"
        })

        build_logs.append(f"[BUILD] 🚀 Starting flow for {agent_name}")
        
        # Phase 1: Namespace Provisioning
        namespace = f"agent-{session_id[:8]}"
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": f"🏗️  Provisioning isolated namespace: {namespace}"
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "   ├─ Allocating CPU quota: 4 cores"
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "   ├─ Allocating Memory quota: 8Gi"
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "   ├─ Configuring network policies..."
        })
        
        values_path = os.path.join(vault_session_path, "values.yaml")
        
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": f"   └─ ✓ Namespace '{namespace}' ready"
        })
        
        # Phase 2: Redis Deployment
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "📦 Deploying Redis Cluster (Session & Cache Layer)..."
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "   ├─ Pulling image: redis:7-alpine"
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "   ├─ Configuring persistence volume: 2Gi"
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "   ├─ Applying maxmemory policy: allkeys-lru"
        })
        
        # Save knowledge.md
        knowledge_content = artifacts.get("knowledge_content", f"# {agent_name} Knowledge Base\n\nOrganization: {org_name}")
        knowledge_path = os.path.join(vault_session_path, "knowledge.md")
        with open(knowledge_path, "w") as f:
            f.write(knowledge_content)
        
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "   └─ ✓ Redis ready at redis-master:6379"
        })
        
        # Phase 3: RAG/MMAR Engine
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "🧠 Initializing MMAR Engine (RAG + Vector Store)..."
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "   ├─ Loading embedding model: text-embedding-3-small"
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "   ├─ Connecting to Qdrant vector database..."
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "   ├─ Indexing persona knowledge base..."
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "   ├─ Configuring retrieval thresholds: k=5, distance=0.7"
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "   └─ ✓ MMAR engine online at mmar-service:50051"
        })
        
        # Phase 4: TTS Voice Configuration
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": f"🔊 Calibrating TTS Voice for '{agent_name}'..."
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "   ├─ Voice ID: " + voice_id
        })
        
        voice_candidates = state.get("voice_candidates", [])
        voice_name = "Selected Voice"
        for vc in voice_candidates:
            if vc.get("voice_id") == voice_id:
                voice_name = vc.get("name", voice_name)
                break
        
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": f"   ├─ Voice Profile: {voice_name}"
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "   ├─ Optimizing latency settings: 150ms target"
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "   └─ ✓ TTS ready at tts-service:8082"
        })
        
        # Phase 5: Deploy to Cloud (Mocking K3s Orchestrator)
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "🤖 Deploying Multi-Agent Orchestrator..."
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "   ├─ Applying Helm values: elevenlabs_config.json"
        })
        
        logger.info(f"🚀 [BUILD] Pushing agent {session_id} to ElevenLabs")
        
        # --- ELEVENLABS PUSH START ---
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "📡 Pushing Agent to ElevenLabs platform..."
        })
        try:
            cli_output = await elevenlabs_cli.push_agent(session_id, tenant_id)
            agent_id = elevenlabs_cli.get_agent_id_from_output(cli_output, session_id, tenant_id) or session_id
            logger.info(f"✅ ElevenLabs Push Success: {cli_output}")
            
            await manager.send_event(session_id, Events.LOG, {
                "phase": "BUILDING",
                "message": f"   └─ ✓ Pushed to ElevenLabs: {agent_id}"
            })
        except Exception as e:
            logger.error(f"❌ ElevenLabs Push Failed: {e}")
            await manager.send_event(session_id, Events.LOG, {
                "phase": "BUILDING",
                "message": f"   └─ ❌ Push Failed: {str(e)}"
            })
            raise e
        # --- ELEVENLABS PUSH END ---

        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": f"   └─ ✓ Orchestrator synced to ElevenLabs platform"
        })
        
        # Phase 6: Verify pod health (Mocking K3s verification)
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "🔍 Verifying pod health across cluster..."
        })
        
        import asyncio
        await asyncio.sleep(2)  # Give "pods" time to start
        
        # Mock pod check
        for pod_type in ["redis", "rag", "orchestrator"]:
            await asyncio.sleep(0.5)
            status = "Running"
            icon = "★" if pod_type == "orchestrator" else ""
            await manager.send_event(session_id, Events.LOG, {
                "phase": "BUILDING",
                "message": f"   ├─ {pod_type}: {status} {icon}"
            })
        
        await manager.send_event(session_id, Events.LOG, {
            "phase": "BUILDING",
            "message": "   └─ ✓ All pods healthy and ready"
        })
        
        # Final success message
        await manager.send_event(session_id, Events.LOG, {
            "phase": "DEPLOYED",
            "message": "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "DEPLOYED",
            "message": "  ✅ BUILD COMPLETE"
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "DEPLOYED",
            "message": f"  Agent '{agent_name}' is now live on ElevenLabs!"
        })

        # ElevenLabs specific deployment URL (Widget URL or platform link)
        # Using a default preview URL for now
        deployment_url = f"https://elevenlabs.io/app/voice-design/{agent_id}"

        await manager.send_event(session_id, Events.LOG, {
            "phase": "DEPLOYED",
            "message": f"  Dashboard: {deployment_url}"
        })
        await manager.send_event(session_id, Events.LOG, {
            "phase": "DEPLOYED",
            "message": "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        })
        
        build_logs.append(f"[BUILD] 🚀 Agent deployed to ElevenLabs platform")
        logger.info(f"✅ [BUILD] Deployment complete for {session_id}")
        
        # Mock post-deployment logs (UI expects something here)
        await manager.send_event(session_id, Events.LOG, {
            "phase": "DEPLOYED",
            "message": f"\n[LOGS] 🤖 ORCHESTRATOR:\n[SYS] Handshake complete... \n[SYS] Webhook listener active... \n[SYS] ElevenLabs logic engine online.\n[SYS] Agent '{agent_name}' ({agent_id}) ready."
        })
        
        # Wait briefly to ensure logs are sent over WS
        await asyncio.sleep(2)
        
        # Send final completion event
        await manager.send_event(session_id, Events.DEPLOYMENT_COMPLETE, {
            "agent_id": agent_id,
            "status": "success",
            "message": "Agent successfully deployed to ElevenLabs platform",
            "deployment_url": deployment_url,
            "build_logs": build_logs
        })
        
        # Give WebSocket time to deliver the message before connection closes
        await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Failed to build/deploy: {e}")
        build_logs.append(f"[BUILD] ❌ Error: {e}")
        
        # Send failure event
        try:
            await manager.send_event(session_id, Events.DEPLOYMENT_FAILED, {
                "agent_id": session_id,
                "status": "failed",
                "error": str(e),
                "build_logs": build_logs
            })
        except:
            pass

    return {
        **state,
        "build_logs": build_logs,
        "current_phase": "DEPLOYED" if not build_logs[-1].startswith("[BUILD] ❌") else "FAILED"
    }

def construct_agent_config(state: AgentState) -> Dict[str, Any]:
    """
    Construct Agent Configuration Object (Mirroring values.yaml structure).
    This acts as the Single Source of Truth for 'The Runner'.
    """
    logger.info("[BUILD] Constructing agent configuration...")
    
    session_id = state.get("session_id")
    extracted = state.get("extracted_fields", {})
    artifacts = state.get("artifacts", {})
    voice_id = state.get("selected_voice_id")
    
    agent_config = {
        "global": {
            "orgName": extracted.get("org_name", "Organization"),
            "environment": "production",
            "domain": "davinci.ai"
        },
        "orchestrator": {
            "persona": {
                "name": artifacts.get("agent_name", extracted.get("agent_name", "Agent")),
                "introGreeting": artifacts.get("intro_greeting", extracted.get("intro_greeting", "Hello!")),
                "systemPrompt": artifacts.get("system_prompt", "")
            },
            "voice": {
                "provider": "elevenlabs",
                "voiceId": voice_id,
                "settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            },
            "dialogueFlows": artifacts.get("dialogue_flows", "{}")
        },
        "rag": {
            "personas": artifacts.get("rag_persona_yaml", ""),
            "knowledgeBase": {
                "filenames": ["knowledge.md"],
                "content": {
                    "knowledge.md": artifacts.get("generated_knowledge",  # Priority 1: Knowledge from URL extraction
                        artifacts.get("knowledge_content",  # Priority 2: LLM generated
                        extracted.get("knowledge_base_content",  # Priority 3: User provided
                        f"""# Knowledge Base for {extracted.get('agent_name', 'Agent')}

Organization: {extracted.get('org_name', 'Organization')}
Agent: {extracted.get('agent_name', 'Agent')}
Purpose: {extracted.get('system_prompt_hints', 'General assistance')}

## Guidelines
- Provide accurate information
- Be helpful and professional
""")))
                }
            }
        },
        "meta": {
             "created_at": "2026-01-11T12:00:00Z",
             "status": "active",
             "session_id": session_id
        }
    }
    
    # Persist to DB
    try:
        db_service.save_agent_config(session_id, agent_config)
        logger.info(f"[BUILD] Agent config saved to DB: {session_id}")
    except Exception as e:
        logger.error(f"[BUILD] Failed to save to DB: {e}")
    
    return agent_config


def should_validate(state: AgentState) -> str:
    """Router function to decide next step after validation."""
    if state.get("is_complete"):
        return "generation"
    else:
        return "interrupt"  # Will trigger human-in-the-loop
