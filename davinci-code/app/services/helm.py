"""Helm Service - Values.yaml Generator"""
import yaml
import json
from typing import Dict, Any
from pathlib import Path
import logging

from app.config import settings

logger = logging.getLogger(__name__)

def generate_values_yaml(
    agent_name: str,
    org_name: str,
    voice_id: str,
    artifacts: Dict[str, Any],
    voice_stability: float = 0.5,
    voice_similarity: float = 0.75
) -> str:
    """Generate production-ready Helm values.yaml content."""
    
    values = {
        "global": {
            "orgName": org_name,
            "environment": "production",
            "domain": "davinci.ai"
        },
        "orchestrator": {
            "image": "amar3012005/davinci-orchestrator:v2",
            "pullPolicy": "IfNotPresent",
            "replicaCount": 1,
            "service": {
                "type": "ClusterIP",
                "port": 8004
            },
            "persona": {
                "name": agent_name,
                "introGreeting": artifacts.get("intro_greeting", f"Hello! I'm {agent_name}."),
                "systemPrompt": artifacts.get("system_prompt", f"You are {agent_name}, a helpful assistant.")
            },
            "voice": {
                "provider": "elevenlabs",
                "voiceId": voice_id,
                "settings": {
                    "stability": voice_stability,
                    "similarity_boost": voice_similarity
                }
            },
            "dialogueFlows": json.dumps(artifacts.get("dialogue_flows", {
                "intents": [],
                "filler_latency": []
            }), indent=2),
            "resources": {
                "limits": {"cpu": "500m", "memory": "512Mi"},
                "requests": {"cpu": "100m", "memory": "128Mi"}
            }
        },
        "rag": {
            "image": "amar3012005/davinci-rag:v2",
            "pullPolicy": "IfNotPresent",
            "service": {
                "type": "ClusterIP",
                "port": 8000
            },
            "personas": yaml.dump({
                "personas": {
                    "default": artifacts.get("rag_persona", {
                        "name": agent_name.lower(),
                        "display_name": agent_name,
                        "language": "english",
                        "personality_traits": ["helpful"],
                        "response_style": "friendly_casual",
                        "restrictions": []
                    })
                }
            }, default_flow_style=False),
            "knowledgeBase": {
                "filenames": ["knowledge.md"],
                "content": {
                    # Priority: Use LLM-generated deep knowledge if available
                    "knowledge.md": artifacts.get("knowledge_content", 
                        f"# Knowledge Base for {agent_name}\n\nOrganization: {org_name}\nAgent: {agent_name}\n\n## About\n{org_name} provides professional services.\n\n## Agent Role\n{agent_name} assists with inquiries and provides information.")
                }
            },
            "resources": {
                "limits": {"cpu": "1", "memory": "2Gi"},
                "requests": {"cpu": "500m", "memory": "1Gi"}
            }
        },
        "redis": {
            "enabled": True,
            "image": "redis:7-alpine",
            "pullPolicy": "IfNotPresent",
            "resources": {
                "limits": {"cpu": "250m", "memory": "256Mi"},
                "requests": {"cpu": "100m", "memory": "128Mi"}
            }
        },
        "secrets": {
            "openaiApiKey": "",
            "elevenlabsApiKey": "",
            "geminiApiKey": settings.gemini_api_key,
            "qdrantApiKey": ""
        },
        "ingress": {
            "enabled": False,
            "className": "",
            "annotations": {},
            "hosts": [],
            "tls": []
        }
    }
    
    return yaml.dump(values, default_flow_style=False, sort_keys=False, allow_unicode=True)

import subprocess
import os

def deploy_agent(session_id: str, values_path: str) -> bool:
    """
    Deploy the agent to K3s using kubectl apply.
    """
    logger.info(f"🚀 Real-time deployment for agent session: {session_id}")
    
    # Use environment-aware configuration for deployment script
    deployment_script = os.getenv("DEPLOYMENT_SCRIPT_PATH", "/app/scripts/deploy_agent_to_k3s.sh")
    project_root = os.getenv("PROJECT_ROOT", "/app")
    
    if settings.deployment_mode == "mock":
        logger.info(f"MOCK DEPLOY: Would run {deployment_script} {session_id}")
        return True
    
    try:
        # Run the deployment script
        result = subprocess.run(
            [deployment_script, session_id],
            capture_output=True,
            text=True,
            check=True,
            cwd=project_root
        )
        
        logger.info(f"Deployment Output:\n{result.stdout}")
        logger.info(f"✅ Real-time deployment successful for {session_id}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Real-time deployment failed: {e.stderr}")
        return False

def save_values_yaml(content: str, output_dir: str, filename: str = "values.yaml") -> str:
    """Save values.yaml to file system."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    file_path = output_path / filename
    file_path.write_text(content)
    
    logger.info(f"Saved values.yaml to {file_path}")
    return str(file_path)
