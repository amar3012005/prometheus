# Agent Registry to K3s Pod Injection Flow

## Current State (Simulation)
The `davinci-code` backend currently **simulates** deployment. No actual K8s resources are created.

## Proposed Production Flow

### Step 1: Registry Generation
```
User Input → LangGraph State Machine → values.yaml + agent_registry.json
```
- Files saved to: `generated_agent/{agent_id}/`

### Step 2: ConfigMap Injection (Recommended Approach)
When deploying to K8s, the agent configuration should be injected as a **ConfigMap**:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agent-config-{agent_id}
  namespace: agents
data:
  agent_registry.json: |
    {
      "agents": {
        "{agent_id}": {
          "global": { ... },
          "orchestrator": { ... },
          "rag": { ... }
        }
      }
    }
```

### Step 3: Pod Deployment with Volume Mount
The Orchestrator and RAG pods mount this ConfigMap:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator-{agent_id}
spec:
  template:
    spec:
      containers:
      - name: orchestrator
        image: orchestrator-tier1:latest
        volumeMounts:
        - name: agent-config
          mountPath: /app/agent_builder/davinci-code/agent_registry.json
          subPath: agent_registry.json
          readOnly: true
      volumes:
      - name: agent-config
        configMap:
          name: agent-config-{agent_id}
```

### Step 4: Runtime Configuration Loading
At pod startup:
1. Orchestrator reads `/app/agent_builder/davinci-code/agent_registry.json`
2. When WebSocket connection includes `?agent_id={agent_id}`, the config is loaded
3. ConfigLoader applies dynamic settings (persona, system prompt, knowledge base)

## Implementation Path

### Option A: Helm-Based Deployment (Recommended)
```python
# In app/services/k8s.py (replace simulation)

async def deploy_agent_real(session_id: str, values_path: str):
    """Deploy to actual K3s cluster using Helm"""
    
    # 1. Create namespace
    namespace = f"agent-{session_id[:8]}"
    subprocess.run(["kubectl", "create", "namespace", namespace])
    
    # 2. Create ConfigMap from agent_registry.json
    registry_path = f"generated_agent/{session_id}/agent_registry.json"
    subprocess.run([
        "kubectl", "create", "configmap",
        f"agent-config-{session_id[:8]}",
        f"--from-file=agent_registry.json={registry_path}",
        "-n", namespace
    ])
    
    # 3. Deploy with Helm (uses values.yaml)
    subprocess.run([
        "helm", "install",
        f"agent-{session_id[:8]}",
        "./helm-charts/tara-agent",
        "-f", values_path,
        "-n", namespace,
        "--set", f"agentId={session_id}",
        "--set", f"configMap.name=agent-config-{session_id[:8]}"
    ])
    
    return {"namespace": namespace, "release": f"agent-{session_id[:8]}"}
```

### Option B: Direct kubectl Apply
```python
# Generate K8s manifests from template
def generate_k8s_manifests(agent_id: str, values: dict):
    """Generate K8s YAML from values.yaml"""
    
    manifests = []
    
    # ConfigMap
    manifests.append(f"""
apiVersion: v1
kind: ConfigMap
metadata:
  name: agent-config-{agent_id[:8]}
data:
  agent_registry.json: |
    {json.dumps({"agents": {agent_id: values}}, indent=2)}
---
""")
    
    # Orchestrator Deployment
    manifests.append(f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator-{agent_id[:8]}
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: orchestrator
        image: {values['orchestrator']['image']}
        volumeMounts:
        - name: config
          mountPath: /app/agent_builder/davinci-code/agent_registry.json
          subPath: agent_registry.json
      volumes:
      - name: config
        configMap:
          name: agent-config-{agent_id[:8]}
---
""")
    
    return "\n".join(manifests)

# Apply
subprocess.run(["kubectl", "apply", "-f", "-"], input=manifests, text=True)
```

## Key Points

1. **ConfigMap is the Standard Pattern**
   - Decouples config from container image
   - Allows config updates without rebuilding
   - Native K8s resource

2. **Registry is Injected BEFORE Pod Start**
   - ConfigMap created first
   - Pod deployment references ConfigMap
   - Volume mount makes it available at runtime

3. **No "Hot Injection" After Pod Starts**
   - Config must exist when pod boots
   - For updates: recreate ConfigMap → restart pods

4. **Alternative: Sidecar Pattern**
   - A sidecar container could fetch config from a database
   - Updates config file, signals main container to reload
   - More complex but allows runtime updates without restarts
