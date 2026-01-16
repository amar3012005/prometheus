"""
DAVINCI-CODE Backend - FastAPI Server

Production-grade backend for AI agent building with:
- LangGraph state machine for human-in-the-loop workflows
- WebSocket streaming for real-time progress updates
- Gemini 2.0 Flash Lite for reasoning
- Mock K3s deployment layer
"""
import asyncio
import logging
import uuid
import json
import os
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.state import AgentState
from app.graph.builder import agent_graph
from app.websocket.manager import manager, Events
from app.services.k8s import deploy_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger("davinci-code")
logger.setLevel(logging.DEBUG)

# Session storage
sessions: Dict[str, Dict[str, Any]] = {}
# Test conversation storage
test_sessions: Dict[str, List[Dict[str, str]]] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("🔥 DAVINCI-CODE Backend Starting...")
    logger.info(f"   LLM Model: {settings.llm_model}")
    logger.info(f"   Deployment Mode: {settings.deployment_mode}")
    yield
    logger.info("👋 DAVINCI-CODE Backend Shutting Down...")

app = FastAPI(
    title="DAVINCI-CODE",
    description="Production Backend for AI Agent Building",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.websocket.convai_relay import router as convai_router
app.include_router(convai_router)

# Request models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    phase: str
    is_complete: bool
    clarification: Optional[str] = None
    suggestions: Optional[List[str]] = None
    logs: list
    extracted_fields: Optional[dict] = None
    url_suggestion: Optional[str] = None
    voice_candidates: Optional[List[dict]] = None
    selected_voice_id: Optional[str] = None

from app.graph.nodes import VOICE_SEARCH_REGISTRY, VOICE_RESULTS_REGISTRY

# REST API Routes

def get_vault_path(tenant_id: str = "default-tenant") -> str:
    """Get the tenant-scoped vault path."""
    # Ensure we use an absolute path based on the project root or current directory
    base_path = os.path.abspath(settings.vault_base_path)
    path = os.path.join(base_path, tenant_id)
    os.makedirs(path, exist_ok=True)
    return path

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "model": settings.llm_model}

@app.get("/api/agents")
async def list_agents(x_tenant_id: str = Header("default-tenant")):
    """
    List all built agents from the ElevenLabs vault for the current tenant.
    Returns agent name, ID, and session info for each.
    """
    agents_list = []
    vault_path = get_vault_path(x_tenant_id)
    
    try:
        # Scan all session directories in the vault
        if os.path.exists(vault_path):
            for session_dir in os.listdir(vault_path):
                session_path = os.path.join(vault_path, session_dir)
                agents_json_path = os.path.join(session_path, "agents.json")
                
                if os.path.isdir(session_path) and os.path.exists(agents_json_path):
                    try:
                        with open(agents_json_path, 'r') as f:
                            data = json.load(f)
                            agents = data.get("agents", [])
                            
                            for agent_entry in agents:
                                if isinstance(agent_entry, dict):
                                    config_path = agent_entry.get("config", "")
                                    agent_id = agent_entry.get("id")
                                    
                                    # Only include agents that have been pushed (have an ID)
                                    if agent_id:
                                        # Extract agent name from config filename
                                        agent_name = os.path.basename(config_path).replace(".json", "").replace("_", " ")
                                        
                                        # Get creation time from directory
                                        created_at = os.path.getctime(session_path)
                                        
                                        agents_list.append({
                                            "session_id": session_dir,
                                            "agent_id": agent_id,
                                            "name": agent_name,
                                            "config_path": config_path,
                                            "created_at": created_at
                                        })
                    except Exception as e:
                        logger.warning(f"Failed to read agents.json for {session_dir}: {e}")
        
        # Sort by creation time (newest first)
        agents_list.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        
        return {"agents": agents_list, "count": len(agents_list)}
    
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, x_tenant_id: str = Header("default-tenant")):
    """
    Main chat endpoint for agent building conversation.
    Handles the human-in-the-loop flow.
    """
    session_id = request.session_id or str(uuid.uuid4())
    
    # Initialize or retrieve session state
    if session_id not in sessions:
        sessions[session_id] = {
            "state": {
                "session_id": session_id,
                "tenant_id": x_tenant_id,
                "user_request": request.message,
                "conversation_history": [],
                "extracted_fields": {},
                "is_complete": False,
                "missing_info_reason": "",
                "artifacts": {},
                "build_logs": [],
                "current_phase": "INTAKE",
                "voice_id": None
            },
            "thread_id": session_id
        }
        logger.info(f"[NEW SESSION] {session_id}")
    else:
        # Update user request with new message
        sessions[session_id]["state"]["user_request"] = request.message
        logger.info(f"[CONTINUE SESSION] {session_id}")
    
    session = sessions[session_id]
    state = session["state"]
    
    # Run the graph
    config = {"configurable": {"thread_id": session["thread_id"]}}
    
    try:
        # Execute graph until interrupt or completion
        async for event in agent_graph.astream(state, config):
            logger.info(f"[GRAPH EVENT] {list(event.keys())}")
        
        # Get current state after execution/interrupt
        graph_state = await agent_graph.aget_state(config)
        final_state = graph_state.values
        
        if final_state:
            # Update session
            sessions[session_id]["state"] = final_state
            
            # Fallback: check if background voice search results are ready
            candidates = final_state.get("voice_candidates")
            if not candidates:
                candidates = VOICE_RESULTS_REGISTRY.get(session_id)
            
            return ChatResponse(
                session_id=session_id,
                phase=final_state.get("current_phase", "INTAKE"),
                is_complete=final_state.get("is_complete", False),
                clarification=final_state.get("missing_info_reason") if not final_state.get("is_complete") else None,
                suggestions=final_state.get("suggestions"),
                logs=final_state.get("build_logs", [])[-10:],  # Last 10 logs
                extracted_fields=final_state.get("extracted_fields", {}),
                url_suggestion=final_state.get("url_suggestion"),
                voice_candidates=candidates,
                selected_voice_id=final_state.get("selected_voice_id")
            )
        else:
            raise HTTPException(status_code=500, detail="Graph state retrieval failed")
            
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/build/{session_id}")
async def trigger_build(session_id: str):
    """
    Trigger the full build and deployment pipeline.
    Called after context gathering is complete.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    state = session["state"]
    
    if not state.get("is_complete"):
        raise HTTPException(status_code=400, detail="Context gathering not complete")
    
    # Continue graph execution (run build_node)
    config = {"configurable": {"thread_id": session["thread_id"]}}
    
    try:
        logger.info(f"[BUILD] Resuming graph for session {session_id}...")
        
        # Resume graph execution from interrupt point
        final_state = None
        async for event in agent_graph.astream(None, config):
            logger.info(f"[BUILD] Graph event: {list(event.keys())}")
            if isinstance(event, dict):
                final_state = event
        
        # Update session state
        if final_state:
            sessions[session_id]["state"].update(final_state)
        
        return {
            "session_id": session_id,
            "status": "build_complete",
            "message": "Build pipeline finished successfully"
        }
        
    except Exception as e:
        logger.error(f"Build error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test/{session_id}")
async def test_agent(session_id: str, request: ChatRequest):
    """
    Test the generated agent's persona and knowledge.
    Simulates the agent based on generated artifacts.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    state = sessions[session_id]["state"]
    artifacts = state.get("artifacts", {})
    
    if not artifacts.get("system_prompt"):
        raise HTTPException(status_code=400, detail="Agent artifacts not generated yet")
    
    # Initialize test history if needed
    if session_id not in test_sessions:
        test_sessions[session_id] = []
    
    history = test_sessions[session_id]
    history.append({"role": "user", "content": request.message})
    
    # Use Gemini to simulate the agent
    from app.services.llm import client as genai_client
    from google.genai import types
    
    system_prompt = artifacts.get("system_prompt", "")
    persona_config = json.dumps(artifacts.get("rag_persona", {}), indent=2)
    
    full_prompt = f"""
SYSTEM_DNA:
{system_prompt}

PERSONA_CONFIG:
{persona_config}

CONVERSATION_HISTORY:
{json.dumps(history[-10:], indent=2)}

Respond as the agent defined by the DNA and Persona above.
"""
    
    try:
        response = genai_client.models.generate_content(
            model=settings.llm_model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.7
            )
        )
        agent_msg = response.text.strip()
        
        history.append({"role": "assistant", "content": agent_msg})
        
        return {
            "session_id": session_id,
            "message": agent_msg,
            "agent_name": artifacts.get("rag_persona", {}).get("display_name", "Agent")
        }
    except Exception as e:
        logger.error(f"Test chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get current session state."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    state = sessions[session_id]["state"]
    return {
        "session_id": session_id,
        "phase": state.get("current_phase"),
        "is_complete": state.get("is_complete"),
        "extracted_fields": state.get("extracted_fields"),
        "logs": state.get("build_logs", [])
    }

@app.get("/api/voices")
async def get_voices(query: str):
    """
    Search for voices in the ElevenLabs shared library.
    Returns a list of candidates with preview URLs.
    """
    from app.services import voice as voice_service
    
    result = await voice_service.search_elevenlabs_voices(query)
    return {"voices": result} # result is already a list of dicts

# WebSocket Route

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, x_tenant_id: str = "default-tenant"):
    """
    WebSocket endpoint for real-time build progress streaming.
    """
    from app.graph.builder import agent_graph # Import graph here to avoid circular imports if any
    
    await manager.connect(session_id, websocket)
    
    try:
        from starlette.websockets import WebSocketDisconnect
        while True:
            # Receive messages from client
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session {session_id}")
                break
            except RuntimeError as e:
                if "WebSocket is not connected" in str(e):
                     logger.info(f"WebSocket disconnected cleanly for session {session_id}")
                     break
                raise e
            
            if data.get("type") == "USER_RESPONSE":
                # Handle user response during human-in-the-loop
                if session_id in sessions:
                    # Add response to conversation history
                    sessions[session_id]["state"]["user_request"] = data.get("message", "")
                    sessions[session_id]["state"]["conversation_history"].append({
                        "role": "user",
                        "content": data.get("message", "")
                    })
                    
                    await manager.send_event(session_id, Events.STATUS_UPDATE, {
                        "message": "Processing your response..."
                    })
            
            elif data.get("type") == "VOICE_SELECTED":
                selected_voice_id = data.get("voice_id")
                logger.info(f"[WS] Received voice selection: {selected_voice_id}")
                
                # Resume graph execution
                config = {"configurable": {"thread_id": session_id}}
                
                # Update state with selected voice
                agent_graph.update_state(config, {"selected_voice_id": selected_voice_id})
                
                await manager.send_event(session_id, Events.LOG, {
                    "phase": "GENERATING",
                    "message": f"🎙️ Voice selected: {selected_voice_id}"
                })
                
                # Stream the rest of the graph (finalize node)
                async for event in agent_graph.astream(None, config, stream_mode="values"):
                    if isinstance(event, dict) and event.get("current_phase"):
                        # Just log the phase, graph will interrupt before 'build'
                        logger.info(f"[WS-STREAM] Phase: {event.get('current_phase')}")

            elif data.get("type") == "START_BUILD":
                # Trigger build via WebSocket
                # Resume graph to run build_node
                config = {"configurable": {"thread_id": session_id}}
                async for event in agent_graph.astream(None, config):
                    logger.info(f"[WS-BUILD] event: {event}")
                
    except WebSocketDisconnect:
        manager.disconnect(session_id)

# Main entry
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info"
    )
