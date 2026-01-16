from typing import TypedDict, Dict, List, Any, Literal, Optional
from pydantic import BaseModel

class ExtractedContext(BaseModel):
    """Schema for extracted agent configuration fields."""
    org_name: Optional[str] = None
    agent_name: Optional[str] = None
    persona_vibe: Optional[str] = None
    voice_parameters: Optional[Dict[str, Any]] = None
    knowledge_sources: Optional[List[str]] = None
    intro_greeting: Optional[str] = None
    system_prompt_hints: Optional[str] = None
    supported_languages: Optional[List[str]] = None  # e.g., ["en", "de", "es"]
    
    def get_missing_fields(self) -> List[str]:
        """Returns list of fields that are still None."""
        missing = []
        if not self.org_name:
            missing.append("org_name")
        if not self.agent_name:
            missing.append("agent_name")
        if not self.persona_vibe:
            missing.append("persona_vibe")
        if not self.voice_parameters:
            missing.append("voice_parameters")
        return missing
    
    def is_complete(self) -> bool:
        """Check if all required fields are filled."""
        return len(self.get_missing_fields()) == 0

class AgentState(TypedDict):
    """LangGraph state for the agent building pipeline."""
    session_id: str
    tenant_id: str
    user_request: str
    conversation_history: List[Dict[str, str]]
    extracted_fields: Dict[str, Any]
    is_complete: bool
    missing_info_reason: str
    artifacts: Dict[str, str]
    build_logs: List[str]
    current_phase: Literal["INTAKE", "GENERATING", "BUILDING", "DEPLOYED", "ERROR"]
    voice_id: Optional[str]
    voice_candidates: Optional[List[Dict[str, Any]]]
    selected_voice_id: Optional[str]
    latest_updates: Optional[List[str]]
