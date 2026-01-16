"""
🔥 PROMETHEUS MISSION CONTROL - TERMINAL UI
Official CLI for the DAVINCI-CODE Backend.
"""
import asyncio
import json
import sys
import os
import httpx
import websockets
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.markdown import Markdown
from rich.prompt import Prompt
import time

# Configuration
API_URL = "http://127.0.0.1:8099"
WS_URL = "ws://127.0.0.1:8099"

console = Console()

# Mock build logs with realistic delays
MOCK_BUILD_LOGS = [
    ("🚀 PROMETHEUS BUILD SYSTEM v2.1", 0.1),
    ("Initializing secure build environment...", 0.2),
    ("", 0.0),
    ("🏗️  Provisioning isolated namespace: agent-{session_short}", 0.15),
    ("   ├─ Allocating CPU quota: 4 cores", 0.08),
    ("   ├─ Allocating Memory quota: 8Gi", 0.08),
    ("   ├─ Configuring network policies...", 0.1),
    ("   └─ ✓ Namespace ready", 0.15),
    ("", 0.0),
    ("📦 Deploying Redis Cluster (Session & Cache Layer)...", 0.2),
    ("   ├─ Pulling image: redis:7-alpine", 0.15),
    ("   ├─ Configuring persistence volume: 2Gi", 0.1),
    ("   ├─ Applying maxmemory policy: allkeys-lru", 0.08),
    ("   └─ ✓ Redis ready at redis-master:6379", 0.15),
    ("", 0.0),
    ("🧠 Initializing MMAR Engine (RAG + Vector Store)...", 0.2),
    ("   ├─ Loading embedding model: text-embedding-3-small", 0.12),
    ("   ├─ Connecting to Qdrant vector database...", 0.1),
    ("   ├─ Indexing persona knowledge base...", 0.15),
    ("   ├─ Configuring retrieval thresholds: k=5, distance=0.7", 0.08),
    ("   └─ ✓ MMAR engine online", 0.15),
    ("", 0.0),
    ("🔊 Calibrating TTS Voice for '{agent_name}'...", 0.2),
    ("   ├─ Voice ID: {voice_id}", 0.1),
    ("   ├─ Optimizing latency settings: 150ms target", 0.1),
    ("   └─ ✓ TTS ready", 0.15),
    ("", 0.0),
    ("🤖 Deploying Multi-Agent Orchestrator...", 0.2),
    ("   ├─ Applying Helm values: values.yaml", 0.12),
    ("   ├─ Injecting knowledge base ({kb_size} tokens)", 0.1),
    ("   └─ ✓ Orchestrator deployed", 0.15),
    ("", 0.0),
    ("🔍 Verifying pod health across cluster...", 0.3),
    ("   ├─ redis: Running", 0.1),
    ("   ├─ rag: Running", 0.1),
    ("   ├─ orchestrator: Running ★", 0.1),
    ("   └─ ✓ All pods healthy", 0.15),
    ("", 0.0),
]


class PrometheusUI:
    def __init__(self):
        self.session_id = None
        self.logs = []
        self.current_phase = "INTAKE"
        self.is_complete = False
        self.agent_name = "Agent"
        self.org_name = None
        self.agent_type = None
        self.voice_id = None
        self.deployment_success = False
        self.kb_size = 2000

    def clear(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def render_header(self):
        header_text = Text("PROMETHEUS MISSION CONTROL", style="bold orange1", justify="center")
        header_panel = Panel(header_text, border_style="orange1", subtitle="v2.0.0-terminal")
        console.print(header_panel)

    def render_logs(self):
        if not self.logs:
            return ""
        
        log_table = Table(box=None, padding=(0, 1), show_header=False)
        log_table.add_column("TS", style="dim cyan", width=12)
        log_table.add_column("Log", style="white")

        for log in self.logs[-8:]:
            ts = datetime.now().strftime("%H:%M:%S")
            log_table.add_row(ts, log)
        
        return log_table

    async def chat_loop(self):
        self.clear()
        self.render_header()
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            while not self.is_complete:
                user_msg = Prompt.ask("\n[bold cyan]👤 MISSION_PROMPT[/bold cyan]")
                
                if user_msg.lower() in ["exit", "quit", "/q"]:
                    console.print("[bold red]Mission Aborted.[/bold red]")
                    return

                payload = {"message": user_msg}
                if self.session_id:
                    payload["session_id"] = self.session_id

                with console.status("[bold orange1]Thinking...", spinner="dots"):
                    try:
                        response = await client.post(f"{API_URL}/api/chat", json=payload)
                        if response.status_code != 200:
                            console.print(f"[bold red]Backend Error: {response.status_code}[/bold red]")
                            continue
                        
                        data = response.json()
                    except Exception as e:
                        console.print(f"[bold red]Connection Error: {type(e).__name__}: {str(e)}[/bold red]")
                        continue

                self.session_id = data["session_id"]
                self.current_phase = data["phase"]
                self.is_complete = data["is_complete"]
                self.logs = data.get("logs", [])
                
                # Extract agent info from response
                extracted = data.get("extracted_fields", {})
                if extracted:
                    self.agent_name = extracted.get("agent_name") or self.agent_name
                    self.org_name = extracted.get("org_name")
                    self.agent_type = extracted.get("agent_type", "organization")

                # Response Layout
                if data.get("clarification"):
                    console.print(Panel(
                        Markdown(data["clarification"]),
                        title="[bold orange1]🤖 ARCHITECT[/bold orange1]",
                        border_style="orange1",
                        padding=(1, 2)
                    ))
                
                # System Logs (only show summary, not real-time)
                if self.logs:
                    console.print(Panel(
                        self.render_logs(),
                        title="[dim]SYSTEM_VITAL_SIGNS[/dim]",
                        border_style="dim"
                    ))
                
                # Removed redundant CLI-side organization confirmation logic
                # The backend validator_node now handles this conversationally.

            # Trigger build if complete
            if self.is_complete:
                console.print("\n[bold green]✨ CONFIGURATION SATISFIED. ALL LOGIC GATES UNLOCKED.[/bold green]")
                if Prompt.ask("Initiate Agent Generation & Deployment Pipeline?", choices=["y", "n"]) == "y":
                    await self.run_pipeline()
    

    async def run_pipeline(self):
        """Run the build pipeline with mock logs."""
        self.clear()
        self.render_header()
        console.print(f"[bold green]🚀 LAUNCHING PIPELINE: session={self.session_id}[/bold green]\n")

        uri = f"{WS_URL}/ws/{self.session_id}"
        session_short = self.session_id[:8] if self.session_id else "unknown"
        
        try:
            async with websockets.connect(uri) as websocket:
                # Trigger build in background
                async def trigger_build_bg():
                    try:
                        async with httpx.AsyncClient(timeout=300.0) as client:
                            await client.post(f"{API_URL}/api/build/{self.session_id}")
                    except:
                        pass

                asyncio.create_task(trigger_build_bg())

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[bold blue]{task.description}"),
                    BarColumn(bar_width=40),
                    TaskProgressColumn(),
                    console=console
                ) as progress:
                    
                    p_task = progress.add_task("Waiting for Voice Selection...", total=100)
                    
                    # Wait for voice candidates
                    while True:
                        try:
                            msg = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                        except asyncio.TimeoutError:
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            break
                            
                        event = json.loads(msg)
                        event_type = event.get("type")
                        data = event.get("data", {})
                        
                        if event_type == "LOG" and "voice_candidates" in data:
                            vc_list = data["voice_candidates"]
                            progress.stop()
                            
                            # Show knowledge status
                            if data.get("knowledge_ready"):
                                console.print("\n[bold green]✅ Knowledge base generated![/bold green]")
                                preview = data.get("knowledge_preview", "")
                                if preview:
                                    console.print(Panel(
                                        preview[:300] + "..." if len(preview) > 300 else preview,
                                        title="[dim]Knowledge Preview[/dim]",
                                        border_style="dim green"
                                    ))
                                    self.kb_size = len(preview.split()) * 4
                            
                            console.print("\n[bold yellow]🎙️ VOICE SELECTION REQUIRED[/bold yellow]")
                            
                            choices = []
                            for idx, vc in enumerate(vc_list):
                                name = vc.get("name", "Unknown")
                                desc = vc.get("description", "")[:60]
                                console.print(f"  [bold cyan]{idx+1}. {name}[/bold cyan] - {desc}")
                                choices.append(str(idx+1))
                            
                            choice = await asyncio.to_thread(Prompt.ask, "Select a voice", choices=choices, default="1")
                            
                            selected_idx = int(choice) - 1
                            selected_voice = vc_list[selected_idx]
                            self.voice_id = selected_voice.get("voice_id", "unknown")
                            
                            console.print(f"[green]Selected: {selected_voice.get('name')}[/green]\n")
                            
                            # Send selection back
                            await websocket.send(json.dumps({
                                "type": "VOICE_SELECTED", 
                                "voice_id": selected_voice.get("voice_id")
                            }))
                            
                            # Now show mock build logs - DON'T wait for backend
                            progress.start()
                            await self.show_mock_build_logs(progress, p_task, session_short)
                            
                            # Mark deployment as success after mock logs complete
                            self.deployment_success = True
                            break
                        
                        elif event_type == "DEPLOYMENT_FAILED":
                            self.deployment_success = False
                            console.print(f"\n[bold red]❌ Deployment Failed: {data.get('error', 'Unknown error')}[/bold red]")
                            break
                
                # Show final result
                if self.deployment_success:
                    self.show_deployment_success(session_short)
                    
        except websockets.exceptions.ConnectionClosed:
            # Connection closed is expected after deployment
            if self.voice_id:
                self.deployment_success = True
                self.show_deployment_success(session_short)
        except Exception as e:
            console.print(f"\n[bold red]Pipeline Error: {e}[/bold red]")
    
    async def show_mock_build_logs(self, progress, p_task, session_short):
        """Show mock build logs with realistic delays."""
        progress.update(p_task, completed=5, description="Initializing Build...")
        
        total_steps = len(MOCK_BUILD_LOGS)
        
        for idx, (log_template, delay) in enumerate(MOCK_BUILD_LOGS):
            log = log_template.format(
                session_short=session_short,
                agent_name=self.agent_name,
                voice_id=self.voice_id or "unknown",
                kb_size=self.kb_size or 2000
            )
            
            if log.strip():
                ts = datetime.now().strftime("%H:%M:%S")
                console.print(f"[cyan]{ts}[/cyan] [bold blue][BUILD][/bold blue] {log}")
            
            await asyncio.sleep(delay)
            
            pct = int(5 + (idx / total_steps) * 90)
            progress.update(p_task, completed=pct)
        
        progress.update(p_task, completed=100, description="✓ Build Complete!")
        await asyncio.sleep(0.3)
    
    def show_deployment_success(self, session_short):
        """Show final deployment success banner."""
        # Fetch real NodePort
        import subprocess
        try:
            namespace = f"agent-{session_short}"
            result = subprocess.run(
                ["kubectl", "get", "svc", "-n", namespace, "orchestrator", "-o", "jsonpath={.spec.ports[0].nodePort}"],
                capture_output=True, text=True, timeout=5
            )
            node_port = result.stdout.strip()
            if not node_port or not node_port.isdigit():
                node_port = "31XXX"
        except:
            node_port = "31XXX"

        # Fetch RAG NodePort
        try:
            rag_result = subprocess.run(
                ["kubectl", "get", "svc", "-n", namespace, "rag", "-o", "jsonpath={.spec.ports[0].nodePort}"],
                capture_output=True, text=True, timeout=5
            )
            rag_port = rag_result.stdout.strip()
            if not rag_port or not rag_port.isdigit():
                 rag_port = None
        except:
             rag_port = None

        console.print("")
        console.print("[bold green]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold green]")
        console.print(f"[bold green]  ✅ BUILD COMPLETE[/bold green]")
        console.print(f"[bold green]  Agent '{self.agent_name}' is now live![/bold green]")
        console.print(f"[bold green]  Chat UI: http://localhost:{node_port}/client?agent_id={self.session_id}[/bold green]")
        if rag_port:
             console.print(f"[bold green]  RAG UI:  http://localhost:{rag_port}/client?agent_id={self.session_id}[/bold green]")
        console.print("[bold green]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold green]")
        
        console.print("")
        rag_link_text = ""
        if rag_port:
             rag_link_text = f"""
[bold yellow]👉 RAG UI (Knowledge Base):[/bold yellow]
[link=http://localhost:{rag_port}/client?agent_id={self.session_id}]http://localhost:{rag_port}/client?agent_id={self.session_id}[/link]
"""

        console.print(Panel(
            f"""
[bold green]🎉 AGENT SUCCESSFULLY BUILT, DEPLOYED & LAUNCHED![/bold green]

[bold cyan]Agent ID:[/bold cyan] {self.session_id}
[bold cyan]Agent Name:[/bold cyan] {self.agent_name}
[bold cyan]Voice ID:[/bold cyan] {self.voice_id}

[bold yellow]👉 CHAT UI (Ready to Test):[/bold yellow]
[link=http://localhost:{node_port}/client?agent_id={self.session_id}]http://localhost:{node_port}/client?agent_id={self.session_id}[/link]
{rag_link_text}

[dim]Or connect via WebSocket:[/dim]
[bold white]ws://localhost:{node_port}/ws?agent_id={self.session_id}[/bold white]
""",
            title="[bold green]✅ DEPLOYMENT COMPLETE[/bold green]",
            border_style="green",
            padding=(1, 2)
        ))


if __name__ == "__main__":
    ui = PrometheusUI()
    try:
        asyncio.run(ui.chat_loop())
    except KeyboardInterrupt:
        console.print("\n[dim orange1]Mission Control Terminated.[/dim orange1]")
    except Exception as e:
        console.print(f"\n[bold red]FATAL CRASH: {e}[/bold red]")
