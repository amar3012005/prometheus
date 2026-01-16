# 🚀 DaVinci Frontend - Quick Deployment Guide

## Prerequisites

- Backend running locally on port `8099` or tunneled via Cloudflare
- Node.js 18+ installed
- Production hosting (Netlify, Vercel, or static hosting)

---

## Development Deployment

### 1. Start Local Backend
```bash
# Option 1: Direct backend
cd agent_builder/davinci-code
uvicorn app.main:app --host 0.0.0.0 --port 8099

# Option 2: With Cloudflare tunnel
cloudflared tunnel run --url http://localhost:8099 davinci-backend
```

### 2. Start Frontend Dev Server
```bash
cd agent_builder/prometheus/frontend
npm install
npm run dev
```

**Access at**: `http://localhost:5173`

**Configuration**: Automatically uses `http://127.0.0.1:8099` for API

---

## Production Deployment

### Step 1: Build Production Assets

```bash
cd agent_builder/prometheus/frontend
npm run build
```

**Output**: `dist/` directory with optimized files

### Step 2: Deploy to Hosting

#### Option A: Netlify

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Deploy
cd dist
netlify deploy --prod

# Or using existing .netlify config
cd ..
netlify deploy --prod --dir=dist
```

**Set custom domain**: `dashboard.davinciai.eu`

#### Option B: Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod

# Set custom domain in Vercel dashboard
```

#### Option C: Static Hosting (S3, CloudFlare Pages, etc.)

```bash
# Upload the entire dist/ folder to your hosting
# Ensure index.html is the root file
# Configure domain: dashboard.davinciai.eu
```

---

## Backend Configuration

### Ensure CORS is Configured

In `app/main.py`, verify:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dashboard.davinciai.eu", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Cloudflare Tunnel Setup

```bash
# Install cloudflared
# https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/

# Create tunnel (one-time)
cloudflared tunnel create davinci-backend

# Configure tunnel
cloudflared tunnel route dns davinci-backend api.davinciai.eu

# Run tunnel
cloudflared tunnel run --url http://localhost:8099 davinci-backend
```

**Result**: Backend accessible at `https://api.davinciai.eu`

---

## Verification Checklist

### Local Testing
- [ ] Backend running on port 8099
- [ ] Frontend dev server starts successfully
- [ ] Opens at `http://localhost:5173`
- [ ] API calls reach `http://127.0.0.1:8099`
- [ ] WebSocket connects successfully
- [ ] Can build an agent end-to-end

### Production Testing
- [ ] Cloudflare tunnel running
- [ ] Backend accessible at `https://api.davinciai.eu`
- [ ] Frontend deployed to `https://dashboard.davinciai.eu`
- [ ] CORS allows cross-origin requests
- [ ] WebSocket connects via WSS
- [ ] Voice preview plays audio
- [ ] Full agent build completes
- [ ] Clarification modal appears correctly

---

## Troubleshooting

### Issue: CORS Errors in Production

**Solution**: Add production domain to CORS origins:
```python
allow_origins=["https://dashboard.davinciai.eu"]
```

### Issue: WebSocket Connection Failed

**Solution**: 
- Ensure Cloudflare tunnel is running
- Check WSS protocol is used (not WS)
- Verify WebSocket upgrade headers are allowed

### Issue: 404 on Page Reload

**Solution**: Configure hosting for SPA routing:

**Netlify** - Create `public/_redirects`:
```
/*    /index.html   200
```

**Vercel** - Create `vercel.json`:
```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

### Issue: Build Fails

**Solution**: 
```bash
# Clear cache and rebuild
rm -rf node_modules dist
npm install
npm run build
```

---

## Environment Verification

### Check Current Environment

The frontend automatically detects environment based on hostname:

- **localhost** → Development mode (`http://127.0.0.1:8099`)
- **dashboard.davinciai.eu** → Production mode (`https://api.davinciai.eu`)

### Test Configuration

Open browser console and check:
```javascript
// Should log environment and URLs
// "🔥 DaVinci Frontend - DEVELOPMENT MODE"
// or
// "🔥 DaVinci Frontend - PRODUCTION MODE"
```

---

## Quick Reference

| Service | Development | Production |
|---------|-------------|------------|
| **Frontend** | `http://localhost:5173` | `https://dashboard.davinciai.eu` |
| **Backend API** | `http://127.0.0.1:8099` | `https://api.davinciai.eu` |
| **WebSocket** | `ws://127.0.0.1:8099` | `wss://api.davinciai.eu` |

---

## Monitoring

### Backend Logs
```bash
# FastAPI logs
tail -f /path/to/backend/logs

# Or if running directly
# Logs appear in terminal where uvicorn is running
```

### Frontend Logs
- Browser DevTools → Console
- Network tab for API/WS requests
- Application tab for storage

### Cloudflare Tunnel Logs
```bash
# Check tunnel status
cloudflared tunnel info davinci-backend

# View logs
cloudflared tunnel logs davinci-backend
```

---

## Success Criteria

✅ Frontend loads at production URL  
✅ API calls successful (200 responses)  
✅ WebSocket connects (status: OPEN)  
✅ Clarification modal appears on re-questions  
✅ Voice preview plays audio correctly  
✅ Terminal logs display with formatting  
✅ Full agent build completes  
✅ Deployment URLs are generated  

---

## Maintenance

### Update Frontend
```bash
# Make changes
# Test locally
npm run dev

# Build and deploy
npm run build
netlify deploy --prod
# or
vercel --prod
```

### Update Backend
```bash
# Make changes
# Restart backend
# Cloudflare tunnel automatically forwards to new instance
```

---

## Support

For issues, check:
1. Browser DevTools Console
2. Network tab (failed requests)
3. Backend logs (FastAPI)
4. Cloudflare tunnel status

Common fixes:
- Clear browser cache
- Restart Cloudflare tunnel
- Verify CORS configuration
- Check environment detection
