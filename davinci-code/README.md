# DaVinci Code Backend

Production-ready backend for AI agent building, featuring LangGraph orchestration and ElevenLabs integration.

## Docker Deployment

### Prerequisites
- Docker & Docker Compose
- API Keys: `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`

### Quick Start
```bash
# Set your API keys in .env
docker compose up -d
```

### Multi-tenancy
The backend supports multi-tenancy via the `X-Tenant-ID` header (REST) or `x_tenant_id` query parameter (WebSocket).
Isolated storage is created automatically at `/app/vault/{tenant_id}/`.

### API Endpoints
- `GET /health`: Health check
- `GET /api/agents`: List built agents for a tenant
- `POST /api/chat`: Main building conversation endpoint
- `WS /ws/{session_id}`: Real-time build progress
