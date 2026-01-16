"""ElevenLabs ConvAI WebSocket Relay"""
import asyncio
import json
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import websockets
from app.config import settings

logger = logging.getLogger("convai-relay")
router = APIRouter()

@router.websocket("/v1/convai/{agent_id}")
async def convai_relay(websocket: WebSocket, agent_id: str):
    """
    Relay WebSocket messages between browser and ElevenLabs ConvAI.
    Hides API Key from frontend.
    """
    await websocket.accept()
    logger.info(f"🎤 ConvAI Relay: Client connected for agent {agent_id}")

    # ElevenLabs URL
    eleven_url = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={agent_id}"
    
    # Extra headers for auth
    headers = {
        "xi-api-key": settings.elevenlabs_api_key
    }

    eleven_ws = None
    client_connected = True

    async def relay_to_eleven():
        """Relay from browser to ElevenLabs"""
        nonlocal client_connected
        try:
            while client_connected and eleven_ws:
                try:
                    message = await asyncio.wait_for(websocket.receive(), timeout=30.0)
                    
                    if message.get("type") == "websocket.disconnect":
                        logger.info("Browser client disconnected")
                        client_connected = False
                        break
                    
                    if "text" in message and eleven_ws:
                        await eleven_ws.send(message["text"])
                    elif "bytes" in message and eleven_ws:
                        await eleven_ws.send(message["bytes"])
                except asyncio.TimeoutError:
                    # Keep alive, no data received
                    continue
        except WebSocketDisconnect:
            logger.info("Browser disconnected during send")
            client_connected = False
        except Exception as e:
            logger.debug(f"Relay to ElevenLabs stopped: {e}")
            client_connected = False

    async def relay_from_eleven():
        """Relay from ElevenLabs to browser"""
        nonlocal client_connected
        try:
            async for message in eleven_ws:
                if not client_connected:
                    break
                try:
                    if isinstance(message, str):
                        await websocket.send_text(message)
                    else:
                        await websocket.send_bytes(message)
                except Exception as send_err:
                    logger.debug(f"Failed to send to browser: {send_err}")
                    client_connected = False
                    break
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"ElevenLabs connection closed: {e.code}")
        except Exception as e:
            logger.debug(f"Relay from ElevenLabs stopped: {e}")

    try:
        async with websockets.connect(eleven_url, additional_headers=headers) as ws:
            eleven_ws = ws
            logger.info(f"✅ Connected to ElevenLabs for agent {agent_id}")

            # Run both relay tasks concurrently
            # Use return_exceptions=True so one failure doesn't kill the other
            results = await asyncio.gather(
                relay_to_eleven(),
                relay_from_eleven(),
                return_exceptions=True
            )
            
            # Log any exceptions
            for r in results:
                if isinstance(r, Exception):
                    logger.debug(f"Task exception: {r}")

    except websockets.exceptions.ConnectionClosed as e:
        if e.code == 3000:
            logger.error(f"❌ ElevenLabs Error 3000: Agent {agent_id} not found. Please REBUILD the agent.")
        else:
            logger.info(f"👋 Relay connection closed: {e.code} - {e.reason}")
    except Exception as e:
        logger.error(f"❌ ConvAI Relay Error: {e}")
    finally:
        client_connected = False
        try:
            await websocket.close()
        except:
            pass
        logger.info(f"🔌 Relay session ended for agent {agent_id}")
