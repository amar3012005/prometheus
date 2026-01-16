"""Voice Service - ElevenLabs Voice Matching"""
import logging
from typing import Optional, List, Dict, Any
from elevenlabs.client import AsyncElevenLabs
from app.config import settings

logger = logging.getLogger(__name__)

# Keyword-based voice matching database (Fallback)
VOICE_KEYWORDS = {
    "21m00Tcm4TlvDq8ikWAM": {
        "name": "Rachel",
        "keywords": ["female", "warm", "friendly", "american", "conversational"],
        "gender": "female",
        "accent": "american",
        "preview_url": "https://storage.googleapis.com/eleven-public-prod/premade/voices/21m00Tcm4TlvDq8ikWAM/df678b13-9d0e-4208-8f7a-9ca8613e45ed.mp3"
    },
    "pNInz6obpgDQGcFmaJgB": {
        "name": "Adam", 
        "keywords": ["male", "deep", "authoritative", "british"],
        "gender": "male",
        "accent": "british",
        "preview_url": "https://storage.googleapis.com/eleven-public-prod/premade/voices/pNInz6obpgDQGcFmaJgB/8e5cfc31-7af8-4fec-8bc3-71bc47c19127.mp3"
    },
    "EXAVITQu4vr4xnSDxMaL": {
        "name": "Bella",
        "keywords": ["female", "soft", "young", "american"],
        "gender": "female",
        "accent": "american",
        "preview_url": "https://storage.googleapis.com/eleven-public-prod/premade/voices/EXAVITQu4vr4xnSDxMaL/01dca174-8bc8-4f40-9aa8-6920251147e4.mp3"
    },
    "TxGEqnHWrfWFTfGW9XjX": {
        "name": "Josh",
        "keywords": ["male", "young", "energetic", "american"],
        "gender": "male",
        "accent": "american",
        "preview_url": "https://storage.googleapis.com/eleven-public-prod/premade/voices/TxGEqnHWrfWFTfGW9XjX/3e680456-0683-4a11-8938-16e64ee9c986.mp3"
    },
    "VR6AewLTigWG4xSOukaG": {
        "name": "Arnold",
        "keywords": ["male", "deep", "mature", "narrative"],
        "gender": "male",
        "accent": "american",
        "preview_url": "https://storage.googleapis.com/eleven-public-prod/premade/voices/VR6AewLTigWG4xSOukaG/66938363-2256-4b6e-bc35-0c7f201e74bf.mp3"
    },
    "onwK4e9ZLuTAKqWW03F9": {
        "name": "Charlotte",
        "keywords": ["female", "british", "professional", "clear"],
        "gender": "female",
        "accent": "british",
        "preview_url": "https://storage.googleapis.com/eleven-public-prod/premade/voices/onwK4e9ZLuTAKqWW03F9/73b37a44-6338-426c-82e7-080c92135069.mp3"
    }
}

def keyword_match_voice(description: str) -> str:
    """Match voice description to voice ID using keyword matching."""
    description_lower = description.lower()
    
    best_match = None
    best_score = 0
    
    for voice_id, voice_data in VOICE_KEYWORDS.items():
        score = 0
        for keyword in voice_data["keywords"]:
            if keyword in description_lower:
                score += 1
        
        # Boost for gender match
        if voice_data["gender"] in description_lower:
            score += 2
            
        # Boost for accent match
        if voice_data["accent"] in description_lower:
            score += 1
            
        if score > best_score:
            best_score = score
            best_match = voice_id
    
    # Default to Rachel if no match
    result = best_match or "21m00Tcm4TlvDq8ikWAM"
    logger.info(f"[Fallback] Voice match: '{description}' -> {VOICE_KEYWORDS.get(result, {}).get('name', 'Unknown')} ({result})")
    return result

async def search_elevenlabs_voices(voice_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Search ElevenLabs Voice Library using categorical filters + semantic search.
    
    Args:
        voice_params: Structured dict with keys:
            - search_query: Full descriptive sentence
            - gender: male/female/non_binary or None
            - age: young/middle_aged/old or None
            - accent: american/british/australian/african/indian or None
            - use_cases: List of use case tags or None
    
    Returns:
        List of up to 10 voice candidates (for re-ranking)
    """
    if not settings.elevenlabs_api_key:
        logger.warning("No ElevenLabs API key - skipping API search")
        return []
    
    try:
        client = AsyncElevenLabs(api_key=settings.elevenlabs_api_key)
        
        # USE GET_ALL to ensure we only suggest voices the user HAS ACCESS TO.
        # This prevents the "voice_not_found" error during agent deployment.
        logger.info("[ElevenLabs API] Fetching account-accessible voices (including premade)...")
        response = await client.voices.get_all()
        all_voices = response.voices if hasattr(response, "voices") else response
        
        if not all_voices:
            logger.info("[ElevenLabs API] No voices returned from account.")
            return []

        matches = []
        target_gender = voice_params.get("gender")
        target_accent = voice_params.get("accent")
        target_age = voice_params.get("age")
        target_lang = voice_params.get("primary_language")

        for voice in all_voices:
            # We prioritize "premade" category to be safe, but allow "cloned" or "generated" if they exist
            # because those are already in the user's account.
            
            labels = getattr(voice, "labels", {}) or {}
            
            # Local Filtering Logic (Mirroring ElevenLabs Library filters)
            if target_gender and labels.get("gender", "").lower() != target_gender.lower():
                continue
            
            if target_accent and target_accent.lower() not in str(labels.get("accent", "")).lower():
                continue

            if target_age and labels.get("age", "").lower() != target_age.lower():
                continue
            
            # Add to candidates
            matches.append({
                "voice_id": voice.voice_id,
                "name": voice.name,
                "preview_url": voice.preview_url,
                "category": voice.category,
                "description": getattr(voice, "description", "") or f"{labels.get('gender', '')} {labels.get('accent', '')} voice",
                "labels": labels
            })

        # If zero matches after strict filtering, relax filters but keep premade
        if not matches:
            logger.info("[ElevenLabs API] Strict local filtering returned zero. Relaxing filters...")
            for voice in all_voices:
                if voice.category == "premade":
                    labels = getattr(voice, "labels", {}) or {}
                    matches.append({
                        "voice_id": voice.voice_id,
                        "name": voice.name,
                        "preview_url": voice.preview_url,
                        "category": voice.category,
                        "description": getattr(voice, "description", "") or "Premade Voice",
                        "labels": labels
                    })

        # Limit to 15 for re-ranking
        limited_matches = matches[:15]
        logger.info(f"[ElevenLabs API] Local filtering identified {len(limited_matches)} compatible candidates.")
        return limited_matches
        
    except Exception as e:
        logger.error(f"ElevenLabs SDK search failed: {e}")
        return []

async def match_voice(
    voice_params: Dict[str, Any], 
    agent_context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Match voice using categorical filtering + Gemini re-ranking.
    
    Args:
        voice_params: Structured voice parameters from extraction
        agent_context: Full agent context for re-ranking
    
    Returns:
        List of top 3 voice candidates, re-ranked by Gemini
    """
    logger.info(f"[VOICE MATCH] Starting intelligent search with params: {voice_params.get('search_query')}")
    
    # Step 1: Get 10 candidates from ElevenLabs using categorical filters
    candidates = await search_elevenlabs_voices(voice_params)
    
    if not candidates:
        # Fallback to keyword matching
        logger.info("[VOICE MATCH] Falling back to internal keyword matching...")
        fallback_id = keyword_match_voice(voice_params.get("search_query", "warm"))
        return [{
            "voice_id": fallback_id,
            "name": VOICE_KEYWORDS.get(fallback_id, {}).get("name", "Unknown"),
            "preview_url": VOICE_KEYWORDS.get(fallback_id, {}).get("preview_url"),
            "category": "premade",
            "description": "",
            "labels": {}
        }]
    
    # Step 2: If we have 3 or fewer, return them directly
    if len(candidates) <= 3:
        logger.info(f"[VOICE MATCH] Returning all {len(candidates)} candidates (no re-ranking needed)")
        return candidates
    
    # Step 3: Use Gemini to re-rank top 10 to top 3
    from app.services.llm import rerank_voices
    
    logger.info(f"[VOICE MATCH] Re-ranking {len(candidates)} candidates with Gemini...")
    ranked_voice_ids = await rerank_voices(candidates, agent_context)
    
    # Step 4: Map ranked IDs back to full voice objects
    id_to_voice = {v["voice_id"]: v for v in candidates}
    final_top_3 = [id_to_voice[vid] for vid in ranked_voice_ids if vid in id_to_voice]
    
    logger.info(f"[VOICE MATCH] Final top 3: {[v['name'] for v in final_top_3]}")
    return final_top_3
