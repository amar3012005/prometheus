"""WebSocket Connection Manager"""
import asyncio
import json
import logging
from typing import Dict, List, Optional
from fastapi import WebSocket
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections and event broadcasting."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, session_id: str, websocket: WebSocket):
        """Accept and store a WebSocket connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"✅ Client connected: {session_id}")
        
    def disconnect(self, session_id: str):
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"❌ Client disconnected: {session_id}")
    
    async def send_event(self, session_id: str, event_type: str, data: dict):
        """Send an event to a specific session."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                message = {
                    "type": event_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": data
                }
                await websocket.send_json(message)
                logger.debug(f"[WS] Sent {event_type} to {session_id}")
            except Exception as e:
                logger.error(f"Failed to send to {session_id}: {e}")
                self.disconnect(session_id)
    
    async def broadcast(self, event_type: str, data: dict):
        """Broadcast an event to all connected clients."""
        disconnected = []
        for session_id, websocket in self.active_connections.items():
            try:
                await self.send_event(session_id, event_type, data)
            except Exception:
                disconnected.append(session_id)
        
        for session_id in disconnected:
            self.disconnect(session_id)

# Event types
class Events:
    # Phase events
    PHASE_INTAKE = "PHASE_INTAKE"
    PHASE_GENERATING = "PHASE_GENERATING"
    PHASE_BUILDING = "PHASE_BUILDING"
    PHASE_DEPLOYED = "PHASE_DEPLOYED"
    PHASE_ERROR = "PHASE_ERROR"
    
    # Status events
    STATUS_UPDATE = "STATUS_UPDATE"
    LOG = "LOG"
    PROGRESS = "PROGRESS"
    
    # Human-in-the-loop events
    CLARIFICATION_NEEDED = "CLARIFICATION_NEEDED"
    USER_RESPONSE = "USER_RESPONSE"
    
    # Completion events
    BUILD_COMPLETE = "BUILD_COMPLETE"
    DEPLOYMENT_COMPLETE = "DEPLOYMENT_COMPLETE"
    DEPLOYMENT_FAILED = "DEPLOYMENT_FAILED"

# Singleton manager
manager = ConnectionManager()
