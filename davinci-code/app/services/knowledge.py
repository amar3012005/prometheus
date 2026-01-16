"""
Knowledge Base Service - Context-Rich Knowledge Extraction

Uses web scraping and OpenRouter LLM to generate comprehensive knowledge bases
for organizations and personal use cases.
"""

import os
import re
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, quote_plus

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class KnowledgeService:
    """
    Service for extracting and generating knowledge bases.
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
    
    async def _call_llm(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4000,
        temperature: float = 0.5
    ) -> Optional[str]:
        """Call Groq LLM (Llama 3.1 8B)."""
        from app.services.llm import client as groq_client
        from app.config import settings
        
        try:
            logger.info(f"[KNOWLEDGE] 🛰️ Calling Groq for KB generation...")
            response = groq_client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"[KNOWLEDGE] Groq call failed: {e}")
            return None
    
    def fetch_url(self, url: str, timeout: int = 15) -> Dict[str, Any]:
        """Fetch and extract content from a URL."""
        result = {
            "url": url,
            "title": "",
            "meta_description": "",
            "content": "",
            "headings": [],
            "success": False,
            "error": None
        }
        
        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                url = f"https://{url}"
            
            logger.info(f"🌐 Fetching: {url}")
            response = requests.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title_tag = soup.find('title')
            result["title"] = title_tag.get_text().strip() if title_tag else ""
            
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                result["meta_description"] = meta_desc.get('content', '').strip()
            
            headings = []
            for h_level in ['h1', 'h2', 'h3']:
                for h in soup.find_all(h_level):
                    text = h.get_text().strip()
                    if text and len(text) > 3:
                        headings.append({"level": h_level, "text": text[:200]})
            result["headings"] = headings[:20]
            
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript']):
                tag.decompose()
            
            main = soup.find('main') or soup.find('article') or soup.find('div', {'class': re.compile(r'content|article|post')})
            if main:
                content = main.get_text(separator='\n', strip=True)
            else:
                body = soup.find('body')
                content = body.get_text(separator='\n', strip=True) if body else ""
            
            content = self._clean_text(content)
            result["content"] = content[:15000]
            result["success"] = True
            
            logger.info(f"✅ Fetched: {result['title'][:50]}... ({len(content.split())} words)")
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"❌ Fetch failed: {e}")
        
        return result
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        lines = [line.strip() for line in text.split('\n')]
        return '\n'.join(line for line in lines if line and len(line) > 2)
    
    async def generate_organization_knowledge(
        self,
        org_name: str,
        url: Optional[str] = None,
        additional_context: str = ""
    ) -> str:
        """
        Generate knowledge base for an organization.
        
        Args:
            org_name: Organization name
            url: Optional URL to scrape
            additional_context: Any additional context
            
        Returns:
            Markdown-formatted knowledge base
        """
        scraped_content = []
        
        # Fetch URL if provided
        if url:
            scraped = self.fetch_url(url)
            if scraped.get("success"):
                scraped_content.append(scraped)
        
        # Build context
        content_sections = []
        for page in scraped_content:
            section = f"""
### Source: {page.get('title', 'Unknown')}
URL: {page.get('url', 'N/A')}

**Description:** {page.get('meta_description', 'N/A')}

**Key Sections:**
{chr(10).join([f"- {h['text']}" for h in page.get('headings', [])[:10]])}

**Content:**
{page.get('content', '')[:8000]}
"""
            content_sections.append(section)
        
        combined_content = "\n\n---\n\n".join(content_sections) if content_sections else f"Organization: {org_name}\n{additional_context}"
        
        # System prompt for organization knowledge
        system_prompt = """You are an EXPERT KNOWLEDGE BASE ARCHITECT creating RAG-optimized documentation.

OUTPUT FORMAT (Markdown):
# {Organization Name} - Knowledge Base

## Overview
[2-3 paragraphs about what they do, mission, value proposition]

## Products & Services  
[Detailed breakdown with bullet points]

## Key Features
[Technical details, capabilities]

## Target Audience
[Who uses it, use cases]

## Pricing (if available)
[Plans, pricing info]

## Common Questions
[5-10 Q&A pairs users might ask]

## Contact & Resources
[Website, docs, support]

REQUIREMENTS:
- Minimum 1500 words
- Use bullet points for scanability
- Include specific facts and details
- Each section should be self-contained for RAG retrieval"""

        user_prompt = f"""Generate knowledge base for: **{org_name}**

{f"Additional Context: {additional_context}" if additional_context else ""}

SOURCE MATERIAL:
{combined_content[:12000]}

Generate COMPLETE, RAG-optimized knowledge base."""

        logger.info(f"🧠 Generating knowledge base for organization: {org_name}")
        
        knowledge_base = await self._call_llm([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        
        if not knowledge_base:
            # Fallback
            knowledge_base = f"""# {org_name} - Knowledge Base

## Overview
{org_name} is an organization. Additional information was not available.

## Source Information
{combined_content[:5000] if combined_content else "No source material available."}
"""
        
        return knowledge_base
    
    async def generate_personal_knowledge(
        self,
        agent_type_description: str,
        persona_vibe: str = "friendly",
        additional_context: str = ""
    ) -> str:
        """
        Generate knowledge base for personal use agents (tutors, companions, translators).
        
        Args:
            agent_type_description: Description like "AI Girlfriend", "Spanish Tutor"
            persona_vibe: Personality style
            additional_context: Any additional context
            
        Returns:
            Markdown-formatted behavioral knowledge base
        """
        system_prompt = """You are an EXPERT BEHAVIORAL KNOWLEDGE ARCHITECT creating personality documentation for AI companions.

OUTPUT FORMAT (Markdown):
# {Agent Type} - Behavioral Guide

## Identity
[Who this agent is, their role, purpose]

## Personality Traits
[5-10 core personality traits with descriptions]

## Communication Style
[How they speak, tone, vocabulary, patterns]

## Behaviors
[How they respond in different situations]

## Topics of Expertise
[What they know about, can help with]

## Emotional Intelligence
[How they handle emotions, empathy patterns]

## Boundaries
[What they should/shouldn't discuss]

## Example Interactions
[3-5 sample conversation exchanges]

## Conversation Starters
[5-10 ways to start a conversation]

REQUIREMENTS:
- Minimum 1000 words
- Be specific about personality traits
- Include example phrases they would use
- Make it feel authentic and human"""

        user_prompt = f"""Create behavioral knowledge base for: **{agent_type_description}**

Personality Style: {persona_vibe}
{f"Additional Context: {additional_context}" if additional_context else ""}

Generate COMPLETE behavioral guide that makes this agent feel authentic and engaging."""

        logger.info(f"🧠 Generating personal knowledge base: {agent_type_description}")
        
        knowledge_base = await self._call_llm([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        
        if not knowledge_base:
            knowledge_base = f"""# {agent_type_description} - Behavioral Guide

## Identity
A {persona_vibe} AI assistant designed for personal interaction.

## Personality Traits
- Friendly and approachable
- {persona_vibe.capitalize()} in nature
- Attentive to user needs
- Helpful and supportive

## Communication Style
Speaks in a {persona_vibe} manner, using conversational language.
"""
        
        return knowledge_base


# Singleton instance
knowledge_service = KnowledgeService()
