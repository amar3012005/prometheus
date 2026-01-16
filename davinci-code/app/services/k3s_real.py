"""
K3s Deployment Service - Real Implementation
Replaces the simulation in app/services/k8s.py with actual pod deployment.
"""
import asyncio
import subprocess
import json
import yaml
import logging
from pathlib import Path
from typing import Callable, Dict, Any

logger = logging.getLogger(__name__)

class K3sDeploymentService:
    """Deploy agents to actual K3s cluster."""
    
    def __init__(self, emit_event: Callable[[str, str], None]):
        self.emit = emit_event
    
    async def deploy_agent(
        self,
        agent_id: str,
        values_path: str,
        agent_name: str = "Agent"
    ) -> Dict[str, Any]:
        """
        Deploy agent to K3s cluster.
        
        Steps:
        1. Create namespace
        2. Create ConfigMap from agent_registry.json
        3. Apply deployments (orchestrator, rag, redis)
        4. Verify pod health
        """
        namespace = f"agent-{agent_id[:8]}"
        
        try:
            # Load values.yaml
            with open(values_path, 'r') as f:
                values = yaml.safe_load(f)
            
            # Step 1: Create Namespace
            self.emit("BUILDING", f"📦 Creating namespace: {namespace}")
            await self._create_namespace(namespace)
            
            # Step 2: Create ConfigMap
            self.emit("BUILDING", f"📝 Injecting agent configuration...")
            registry_data = self._generate_registry(agent_id, values)
            await self._create_configmap(namespace, agent_id, registry_data)
            
            # Step 3: Deploy Services
            self.emit("BUILDING", f"🚀 Deploying Redis...")
            await self._deploy_redis(namespace)
            
            self.emit("BUILDING", f"🧠 Deploying RAG service...")
            await self._deploy_rag(namespace, agent_id, values)
            
            self.emit("BUILDING", f"🤖 Deploying Orchestrator...")
            await self._deploy_orchestrator(namespace, agent_id, values)
            
            # Step 4: Wait for pods
            self.emit("BUILDING", f"⏳ Waiting for pods to be ready...")
            await self._wait_for_pods(namespace)
            
            # Step 5: Get access endpoint
            endpoint = await self._get_endpoint(namespace)
            
            self.emit("DEPLOYED", f"✅ Agent '{agent_name}' deployed successfully!")
            self.emit("DEPLOYED", f"📍 Endpoint: {endpoint}")
            
            return {
                "success": True,
                "namespace": namespace,
                "endpoint": endpoint,
                "agent_id": agent_id
            }
            
        except Exception as e:
            logger.error(f"K3s deployment failed: {e}")
            self.emit("ERROR", f"❌ Deployment failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _create_namespace(self, namespace: str):
        """Create K8s namespace."""
        cmd = ["kubectl", "create", "namespace", namespace, "--dry-run=client", "-o", "yaml"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Apply the namespace
            subprocess.run(["kubectl", "apply", "-f", "-"], input=result.stdout, text=True, check=True)
            logger.info(f"Created namespace: {namespace}")
    
    def _generate_registry(self, agent_id: str, values: dict) -> dict:
        """Generate agent_registry.json structure from values.yaml."""
        return {
            "agents": {
                agent_id: values
            }
        }
    
    async def _create_configmap(self, namespace: str, agent_id: str, registry_data: dict):
        """Create ConfigMap with agent_registry.json."""
        configmap_yaml = f"""
apiVersion: v1
kind: ConfigMap
metadata:
  name: agent-config-{agent_id[:8]}
  namespace: {namespace}
data:
  agent_registry.json: |
{self._indent_json(registry_data, 4)}
"""
        subprocess.run(["kubectl", "apply", "-f", "-"], input=configmap_yaml, text=True, check=True)
        logger.info(f"Created ConfigMap in {namespace}")
    
    def _indent_json(self, data: dict, indent: int) -> str:
        """Indent JSON for YAML embedding."""
        lines = json.dumps(data, indent=2).split('\n')
        return '\n'.join(' ' * indent + line for line in lines)
    
    async def _deploy_redis(self, namespace: str):
        """Deploy Redis service."""
        redis_yaml = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: {namespace}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        command: ["redis-server", "--appendonly", "yes"]
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: {namespace}
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
"""
        subprocess.run(["kubectl", "apply", "-f", "-"], input=redis_yaml, text=True, check=True)
    
    async def _deploy_rag(self, namespace: str, agent_id: str, values: dict):
        """Deploy RAG service with ConfigMap mount."""
        rag_config = values.get("rag", {})
        
        rag_yaml = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag
  namespace: {namespace}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: rag
  template:
    metadata:
      labels:
        app: rag
    spec:
      containers:
      - name: rag
        image: tara-microservice-rag-tier1:latest
        imagePullPolicy: Never
        ports:
        - containerPort: 8000
        env:
        - name: ENABLE_RETRIEVAL
          value: "false"
        - name: REDIS_HOST
          value: "redis"
        - name: REDIS_PORT
          value: "6379"
        - name: LLM_PROVIDER
          value: "{rag_config.get('llmProvider', 'gemini')}"
        - name: LLM_MODEL
          value: "{rag_config.get('llmModel', 'gemini-2.0-flash-lite')}"
        - name: GEMINI_API_KEY
          value: "AIzaSyBG9nb_Xe2267oBO9s0g0jJOQtJGh47pNk"
        volumeMounts:
        - name: agent-config
          mountPath: /app/agent_builder/davinci-code/agent_registry.json
          subPath: agent_registry.json
          readOnly: true
      volumes:
      - name: agent-config
        configMap:
          name: agent-config-{agent_id[:8]}
---
apiVersion: v1
kind: Service
metadata:
  name: rag
  namespace: {namespace}
spec:
  selector:
    app: rag
  ports:
  - port: 8000
    targetPort: 8000
"""
        subprocess.run(["kubectl", "apply", "-f", "-"], input=rag_yaml, text=True, check=True)
    
    async def _deploy_orchestrator(self, namespace: str, agent_id: str, values: dict):
        """Deploy Orchestrator service with ConfigMap mount."""
        orch_config = values.get("orchestrator", {})
        
        orch_yaml = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator
  namespace: {namespace}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: orchestrator
  template:
    metadata:
      labels:
        app: orchestrator
    spec:
      containers:
      - name: orchestrator
        image: tara-microservice-orchestrator-tier1:latest
        imagePullPolicy: Never
        ports:
        - containerPort: 8004
        env:
        - name: RAG_SERVICE_URL
          value: "http://rag:8000"
        - name: REDIS_HOST
          value: "redis"
        - name: REDIS_PORT
          value: "6379"
        - name: ORGANIZATION_NAME
          value: "{values.get('global', {}).get('orgName', 'Organization')}"
        volumeMounts:
        - name: agent-config
          mountPath: /app/agent_builder/davinci-code/agent_registry.json
          subPath: agent_registry.json
          readOnly: true
      volumes:
      - name: agent-config
        configMap:
          name: agent-config-{agent_id[:8]}
---
apiVersion: v1
kind: Service
metadata:
  name: orchestrator
  namespace: {namespace}
spec:
  type: NodePort
  selector:
    app: orchestrator
  ports:
  - port: 8004
    targetPort: 8004
    nodePort: 30004
"""
        subprocess.run(["kubectl", "apply", "-f", "-"], input=orch_yaml, text=True, check=True)
    
    async def _wait_for_pods(self, namespace: str, timeout: int = 120):
        """Wait for all pods to be ready."""
        cmd = [
            "kubectl", "wait", "--for=condition=ready", "pod",
            "--all", "-n", namespace, f"--timeout={timeout}s"
        ]
        subprocess.run(cmd, check=True)
    
    async def _get_endpoint(self, namespace: str) -> str:
        """Get the service endpoint."""
        # For K3s, we can use NodePort or port-forward
        # Return the NodePort URL
        return f"http://localhost:30004/ws?agent_id={namespace}"


async def deploy_agent_k3s(
    session_id: str,
    values_path: str,
    emit_event: Callable[[str, str], None],
    agent_name: str = "Agent"
) -> dict:
    """
    Deploy agent to K3s cluster (replaces simulation).
    """
    deployer = K3sDeploymentService(emit_event)
    return await deployer.deploy_agent(
        agent_id=session_id,
        values_path=values_path,
        agent_name=agent_name
    )
