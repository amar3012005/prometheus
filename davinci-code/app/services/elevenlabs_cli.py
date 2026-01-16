import os
import json
import logging
import asyncio
import subprocess
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

from app.config import settings

def get_vault_path(tenant_id: str = "default-tenant") -> str:
    """Get the tenant-scoped vault path from settings."""
    # Ensure we use an absolute path based on the project root or current directory
    base_path = os.path.abspath(settings.vault_base_path)
    path = os.path.join(base_path, tenant_id)
    os.makedirs(path, exist_ok=True)
    return path

class ElevenLabsCLIService:
    def __init__(self):
        # Base path ensured by get_vault_path or startup
        pass

    def _get_session_path(self, session_id: str, tenant_id: str) -> str:
        """Helper to get full session path for a tenant."""
        return os.path.join(get_vault_path(tenant_id), session_id)

    def _run_command(self, cmd: list, cwd: str) -> str:
        """Run a shell command and return output."""
        try:
            import shutil
            # Ensure the primary command is in the path
            bin_path = shutil.which(cmd[0])
            if not bin_path:
                raise Exception(f"Command '{cmd[0]}' not found in PATH.")
            
            # Use the full path to the binary
            actual_cmd = [bin_path] + cmd[1:]
            
            result = subprocess.run(
                actual_cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"CLI Command failed: {e.stderr}")
            raise Exception(f"ElevenLabs CLI Error: {e.stderr}")

    def init_workspace(self, session_id: str, tenant_id: str = "default-tenant"):
        """Initialize a new ElevenLabs project structure for a session."""
        session_path = self._get_session_path(session_id, tenant_id)
        agents_json_path = os.path.join(session_path, "agents.json")
        
        # Create directory
        os.makedirs(session_path, exist_ok=True)
        
        # Only init if agents.json doesn't exist at all
        if not os.path.exists(agents_json_path):
            logger.info(f"[ELEVENLABS] Initializing new workspace for {session_id} (Tenant: {tenant_id})")
            try:
                self._run_command(["elevenlabs", "agents", "init"], cwd=session_path)
                logger.info(f"[ELEVENLABS] CLI init complete")
            except Exception as e:
                logger.warning(f"[ELEVENLABS] CLI init failed: {e}, creating manually")
                # Create minimal agents.json manually
                with open(agents_json_path, 'w') as f:
                    json.dump({"agents": []}, f, indent=4)
        else:
            logger.info(f"[ELEVENLABS] Workspace already exists for {session_id}")
        
        # Ensure subdirectories exist
        os.makedirs(os.path.join(session_path, "agent_configs"), exist_ok=True)
        os.makedirs(os.path.join(session_path, "knowledge"), exist_ok=True)
        
        return session_path


    def generate_agent_config(self, session_id: str, tenant_id: str, extracted_fields: dict, artifacts: dict, voice_id: str, knowledge_filename: str):
        """Populate the agent.json with the structure verified in clean_test."""
        session_path = self._get_session_path(session_id, tenant_id)
        logger.info(f"[ELEVENLABS] Generating config for session: {session_id} (Tenant: {tenant_id})")
        # ... rest of the logic uses session_path ...
        # (I'll keep the logic same but using the local session_path)
        
        # High-Fidelity Prompt from Logic Engine - MUST BE A STRING
        raw_prompt = artifacts.get("system_prompt", f"You are {artifacts.get('agent_name', 'Romero')}, a helpful AI assistant.")
        
        # Handle case where LLM returns prompt as an object
        if isinstance(raw_prompt, dict):
            # Convert structured prompt to a single string
            parts = []
            if raw_prompt.get("personality"):
                parts.append(f"PERSONALITY: {raw_prompt['personality']}")
            if raw_prompt.get("behavior"):
                parts.append(f"BEHAVIOR: {raw_prompt['behavior']}")
            if raw_prompt.get("instructions"):
                parts.append(f"INSTRUCTIONS: {raw_prompt['instructions']}")
            if raw_prompt.get("language_protocol"):
                parts.append(f"LANGUAGE PROTOCOL: {raw_prompt['language_protocol']}")
            system_prompt = "\n\n".join(parts) if parts else str(raw_prompt)
        else:
            system_prompt = str(raw_prompt)
        
        agent_name = artifacts.get("agent_name", extracted_fields.get("agent_name", "Agent"))
        
        # Build configuration
        config = {
            "name": agent_name,
            "conversation_config": {
                "agent": {
                    "prompt": {
                        "prompt": system_prompt,
                        "llm": "gemini-2.0-flash",
                        "temperature": 0.5
                    },
                    "language": extracted_fields.get("supported_languages", ["en"])[0] if extracted_fields.get("supported_languages") else "en"
                },
                "conversation": {
                    "text_only": False
                },
                "tts": {
                    "model_id": "eleven_turbo_v2",
                    "voice_id": voice_id or "cjVigY5qzO86Huf0OWal"
                }
            },
            "platform_settings": {},
            "tags": ["environment:dev"]
        }
        
        # Save to agent_configs/agent.json
        agent_filename = f"{config['name']}.json".replace(" ", "_")
        config_path = os.path.join(session_path, "agent_configs", agent_filename)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
            
        # Update agents.json registry
        registry_path = os.path.join(session_path, "agents.json")
        registry = {"agents": []}
        
        if os.path.exists(registry_path):
            try:
                with open(registry_path, 'r') as f:
                    content = json.load(f)
                    if isinstance(content.get("agents"), list):
                        registry = content
            except:
                pass

        config_rel_path = f"agent_configs/{agent_filename}"
        
        # Update or Add entry
        found = False
        for entry in registry["agents"]:
            if isinstance(entry, dict) and entry.get("config") == config_rel_path:
                found = True
                break
        
        if not found:
            registry["agents"].append({"config": config_rel_path})
            
        with open(registry_path, 'w') as f:
            json.dump(registry, f, indent=4)
        
        return config_path

    async def push_agent(self, session_id: str, tenant_id: str):
        """Execute elevenlabs agents push in background."""
        session_path = self._get_session_path(session_id, tenant_id)
        agents_json_path = os.path.join(session_path, "agents.json")
        
        # ... logic as before but using session_path ...
        if not os.path.exists(agents_json_path):
            raise Exception("agents.json does not exist!")
            
        # Ensure API Key is in env
        env = os.environ.copy()
        if settings.elevenlabs_api_key:
            env["ELEVEN_API_KEY"] = settings.elevenlabs_api_key
            env["ELEVENLABS_API_KEY"] = settings.elevenlabs_api_key

        try:
            import shutil
            eleven_path = shutil.which("elevenlabs")
            if not eleven_path:
                logger.error("[ELEVENLABS] elevenlabs CLI not found. Please install with 'npm install -g elevenlabs'")
                raise FileNotFoundError("elevenlabs CLI not found in PATH")

            process = await asyncio.create_subprocess_exec(
                eleven_path, "agents", "push",
                cwd=session_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            stdout, stderr = await process.communicate()
            output = stdout.decode().strip()
            
            if process.returncode != 0:
                raise Exception(f"Push failed: {stderr.decode()}")
            
            if "failed to push" in output.lower():
                raise Exception(f"ElevenLabs push failed: {output}")
                
            return output
        except Exception as e:
            logger.error(f"[ELEVENLABS] Push error: {e}")
            raise

    def get_agent_id_from_output(self, output: str, session_id: str, tenant_id: str) -> Optional[str]:
        """Extract Agent ID from CLI output or agents.json file."""
        import re
        match = re.search(r"ID: ([a-zA-Z0-9_]+)", output)
        if match:
            return match.group(1)
        
        # Check agents.json
        session_path = self._get_session_path(session_id, tenant_id)
        agents_json_path = os.path.join(session_path, "agents.json")
        if os.path.exists(agents_json_path):
            try:
                with open(agents_json_path, 'r') as f:
                    data = json.load(f)
                    agents = data.get("agents", [])
                    if agents and isinstance(agents[0], dict):
                        agent_id = agents[0].get("id")
                        if agent_id:
                            return agent_id
            except Exception as e:
                logger.warning(f"Failed to read agent_id from agents.json: {e}")
        
        match = re.search(r"(agent_[a-zA-Z0-9]+)", output)
        if match:
            return match.group(1)
        
        return None

elevenlabs_cli = ElevenLabsCLIService()
