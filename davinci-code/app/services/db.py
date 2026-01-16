"""
Simple Agent Configuration Database Service.

In a real production environment, this would be Redis or Postgres.
For PROMETHEUS-LOCAL, we use a local JSON file store.
"""
import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DB_FILE = "agent_registry.json"

class AgentDBService:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        """Ensure the JSON DB file exists."""
        if not os.path.exists(self.db_path):
            with open(self.db_path, 'w') as f:
                json.dump({"agents": {}}, f, indent=2)

    def _load_db(self) -> Dict[str, Any]:
        """Load the database from disk."""
        try:
            with open(self.db_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load DB: {e}")
            return {"agents": {}}

    def _save_db(self, data: Dict[str, Any]):
        """Save the database to disk."""
        try:
            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save DB: {e}")

    def save_agent_config(self, session_id: str, config: Dict[str, Any]) -> str:
        """
        Register or update an agent configuration.
        
        Args:
            session_id: Unique session ID (acts as agent_id for this MVP)
            config: The complete agent configuration dictionary
            
        Returns:
            The agent_id (session_id)
        """
        db = self._load_db()
        
        # Add metadata
        config["updated_at"] = datetime.now().isoformat()
        config["status"] = "active"
        
        db["agents"][session_id] = config
        self._save_db(db)
        logger.info(f"✅ Saved agent config for {session_id}")
        return session_id

    def get_agent_config(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an agent configuration by ID."""
        db = self._load_db()
        return db["agents"].get(agent_id)

    def list_agents(self) -> Dict[str, Any]:
        """List all registered agents."""
        db = self._load_db()
        return db["agents"]

# Global instance
db_service = AgentDBService()
