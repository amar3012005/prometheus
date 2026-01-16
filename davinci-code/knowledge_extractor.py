#!/usr/bin/env python3
"""
Knowledge Base Extractor - Robust Context-Rich Knowledge Generator

Extracts comprehensive knowledge about organizations from web sources
and generates RAG-optimized knowledge bases using OpenRouter LLM.

Features:
    - Organization verification before extraction
    - Multi-URL content scraping
    - OpenRouter LLM for intelligent summarization
    - RAG-optimized output format (2000+ tokens)
    - Markdown structured output

Usage:
    python knowledge_extractor.py "Daytona"
    python knowledge_extractor.py https://daytona.io
    python knowledge_extractor.py "Ferrari" --urls https://ferrari.com https://en.wikipedia.org/wiki/Ferrari
    
Environment Variables:
    OPENROUTER_API_KEY: Required for LLM processing
"""

import os
import sys
import argparse
import json
import re
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, quote_plus
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# OpenRouter configuration
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Default model - use a capable free/cheap model
DEFAULT_MODEL = "google/gemini-2.0-flash-001"  # Fast and capable
FALLBACK_MODEL = "meta-llama/llama-3.3-70b-instruct"  # Free fallback


class KnowledgeExtractor:
    """
    Extracts and generates comprehensive knowledge bases for organizations.
    
    Workflow:
        1. Search/verify organization
        2. Scrape content from URLs
        3. Generate RAG-optimized knowledge base via OpenRouter
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        site_url: str = "https://prometheus.ai",
        site_name: str = "Prometheus Agent Builder"
    ):
        self.api_key = api_key or OPENROUTER_API_KEY
        self.model = model
        self.site_url = site_url
        self.site_name = site_name
        
        if not self.api_key:
            logger.warning("⚠️ OPENROUTER_API_KEY not set - LLM features disabled")
        
        # Browser headers for scraping
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    
    def _call_openrouter(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4000,
        temperature: float = 0.7
    ) -> Optional[str]:
        """
        Call OpenRouter API with the given messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            
        Returns:
            Response text or None if failed
        """
        if not self.api_key:
            return None
        
        try:
            response = requests.post(
                url=OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.site_name,
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"OpenRouter API call failed: {e}")
            return None
    
    def fetch_url(self, url: str, timeout: int = 15) -> Dict[str, Any]:
        """
        Fetch and extract content from a URL.
        
        Returns dict with title, meta_description, content, headings, success, error
        """
        result = {
            "url": url,
            "title": "",
            "meta_description": "",
            "content": "",
            "headings": [],
            "word_count": 0,
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
            
            # Extract title
            title_tag = soup.find('title')
            result["title"] = title_tag.get_text().strip() if title_tag else ""
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                result["meta_description"] = meta_desc.get('content', '').strip()
            
            # Extract headings
            headings = []
            for h_level in ['h1', 'h2', 'h3']:
                for h in soup.find_all(h_level):
                    text = h.get_text().strip()
                    if text and len(text) > 3:
                        headings.append({"level": h_level, "text": text[:200]})
            result["headings"] = headings[:20]
            
            # Remove unwanted elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript', 'form', 'button']):
                tag.decompose()
            
            # Find main content
            main = soup.find('main') or soup.find('article') or soup.find('div', {'class': re.compile(r'content|article|post|main')})
            if main:
                content = main.get_text(separator='\n', strip=True)
            else:
                body = soup.find('body')
                content = body.get_text(separator='\n', strip=True) if body else ""
            
            # Clean content
            content = self._clean_text(content)
            result["content"] = content[:15000]  # Limit to avoid token overflow
            result["word_count"] = len(content.split())
            result["success"] = True
            
            logger.info(f"✅ Fetched: {result['title'][:50]}... ({result['word_count']} words)")
            
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
    
    def search_organization(self, org_name: str) -> Dict[str, Any]:
        """
        Search for organization info using DuckDuckGo HTML (no API key needed).
        
        Returns basic info for verification.
        """
        try:
            search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(org_name)}"
            response = requests.get(search_url, headers=self.headers, timeout=10)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            for result in soup.find_all('div', class_='result')[:5]:
                title_tag = result.find('a', class_='result__a')
                snippet_tag = result.find('a', class_='result__snippet')
                
                if title_tag:
                    results.append({
                        "title": title_tag.get_text().strip(),
                        "url": title_tag.get('href', ''),
                        "snippet": snippet_tag.get_text().strip() if snippet_tag else ""
                    })
            
            return {"success": True, "results": results}
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"success": False, "results": [], "error": str(e)}
    
    def verify_organization(self, org_name: str) -> Dict[str, Any]:
        """
        Verify organization identity using LLM and web search.
        
        Returns verification info for user confirmation.
        """
        # First, do a quick web search
        search_results = self.search_organization(org_name)
        
        if not search_results.get("results"):
            return {
                "verified": False,
                "message": f"Could not find information about '{org_name}'. Please provide a URL directly."
            }
        
        # Use LLM to generate a brief summary for verification
        top_results = search_results["results"][:3]
        context = "\n".join([
            f"- {r['title']}: {r['snippet']}" for r in top_results
        ])
        
        # Extract likely website URL
        likely_url = None
        for r in top_results:
            url = r.get('url', '')
            if org_name.lower().replace(' ', '') in url.lower().replace(' ', ''):
                likely_url = url
                break
        if not likely_url and top_results:
            likely_url = top_results[0].get('url', '')
        
        prompt = f"""Based on the following search results, provide a ONE PARAGRAPH summary (2-3 sentences) 
to help verify if this is the correct organization the user is looking for.

Organization Query: "{org_name}"

Search Results:
{context}

Provide ONLY the verification summary, nothing else. Be concise."""

        summary = self._call_openrouter([
            {"role": "user", "content": prompt}
        ], max_tokens=200, temperature=0.3)
        
        return {
            "verified": True,
            "org_name": org_name,
            "summary": summary or f"Found: {top_results[0]['title']}. {top_results[0]['snippet'][:200]}",
            "likely_url": likely_url,
            "search_results": top_results
        }
    
    def generate_knowledge_base(
        self,
        org_name: str,
        scraped_content: List[Dict[str, Any]],
        additional_context: str = ""
    ) -> str:
        """
        Generate a comprehensive, RAG-optimized knowledge base.
        
        Uses OpenRouter LLM to create structured, context-rich content (2000+ tokens).
        
        Args:
            org_name: Organization name
            scraped_content: List of scraped page data
            additional_context: Any additional context from user
            
        Returns:
            Markdown-formatted knowledge base
        """
        # Prepare content for LLM
        content_sections = []
        for page in scraped_content:
            if page.get("success"):
                section = f"""
### Source: {page.get('title', 'Unknown')}
URL: {page.get('url', 'N/A')}

**Description:** {page.get('meta_description', 'N/A')}

**Key Sections:**
{chr(10).join([f"- {h['text']}" for h in page.get('headings', [])[:10]])}

**Content:**
{page.get('content', '')[:5000]}
"""
                content_sections.append(section)
        
        combined_content = "\n\n---\n\n".join(content_sections)
        
        # Master System Prompt for Knowledge Base Generation
        system_prompt = """You are an EXPERT KNOWLEDGE BASE ARCHITECT specializing in creating comprehensive, 
RAG-optimized documentation for AI assistants.

Your task is to generate a DETAILED, CONTEXT-RICH knowledge base about an organization that will be used 
by an AI agent to answer user questions accurately and naturally.

## OUTPUT REQUIREMENTS:

### 1. STRUCTURE (Use these exact Markdown headers)
```
# {Organization Name} - Knowledge Base

## Overview
[2-3 paragraphs: What the organization does, its mission, and core value proposition]

## History & Background
[Key milestones, founding story, evolution, notable achievements]

## Products & Services
[Detailed breakdown of offerings, key features, use cases]

## Key People & Leadership
[Founders, executives, notable team members if known]

## Technology & Innovation
[Technical details, stack, methodologies, innovations]

## Target Audience & Use Cases
[Who uses it, primary use cases, industries served]

## Pricing & Plans
[If applicable: pricing tiers, free options, enterprise plans]

## Unique Selling Points
[What differentiates them from competitors]

## Common Questions & Answers
[5-10 FAQ-style Q&A pairs that users might ask]

## Contact & Resources
[Website, documentation, support channels, social media]
```

### 2. CONTENT RULES:
- MINIMUM 2000 tokens of substantive content
- Use bullet points and lists for scanability
- Include specific details, numbers, and facts where available
- Write in a neutral, informative tone
- Avoid marketing fluff - focus on factual information
- Include technical details when relevant
- Make content suitable for an AI to retrieve and respond naturally

### 3. RAG OPTIMIZATION:
- Each section should be self-contained (can be retrieved independently)
- Include relevant keywords naturally throughout
- Use varied phrasing for key concepts (helps semantic search)
- Structure Q&A section with natural language questions

### 4. QUALITY STANDARDS:
- If information is unclear or unavailable, note "Information not available" rather than hallucinating
- Prioritize accuracy over completeness
- Include direct quotes or specifics when available in source material"""

        user_prompt = f"""Generate a comprehensive knowledge base for: **{org_name}**

{f"Additional Context: {additional_context}" if additional_context else ""}

## SOURCE MATERIAL:
{combined_content[:12000]}

---

Generate the COMPLETE knowledge base following all the structure and quality requirements.
Ensure AT LEAST 2000 tokens of substantive, factual content.
Start with "# {org_name} - Knowledge Base" and include ALL required sections."""

        logger.info("🧠 Generating knowledge base via OpenRouter...")
        
        knowledge_base = self._call_openrouter([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ], max_tokens=4000, temperature=0.5)
        
        if not knowledge_base:
            # Fallback: try with different model
            logger.warning(f"Primary model failed, trying fallback: {FALLBACK_MODEL}")
            self.model = FALLBACK_MODEL
            knowledge_base = self._call_openrouter([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], max_tokens=4000, temperature=0.5)
        
        if not knowledge_base:
            # Last resort: generate basic template
            knowledge_base = self._generate_fallback_kb(org_name, scraped_content)
        
        return knowledge_base
    
    def _generate_fallback_kb(self, org_name: str, scraped_content: List[Dict]) -> str:
        """Generate basic knowledge base if LLM fails."""
        kb = f"""# {org_name} - Knowledge Base

## Overview
{org_name} is an organization. Further details require LLM processing.

## Information Sources
"""
        for page in scraped_content:
            if page.get("success"):
                kb += f"""
### {page.get('title', 'Unknown Source')}
- URL: {page.get('url', 'N/A')}
- Description: {page.get('meta_description', 'N/A')}

**Content Preview:**
{page.get('content', '')[:2000]}

---
"""
        return kb
    
    def extract(
        self,
        org_name: Optional[str] = None,
        urls: Optional[List[str]] = None,
        skip_verification: bool = False
    ) -> Dict[str, Any]:
        """
        Main extraction workflow.
        
        Args:
            org_name: Organization name to search for
            urls: Direct URLs to scrape
            skip_verification: Skip user verification step
            
        Returns:
            Dict with verification_info, scraped_content, knowledge_base
        """
        result = {
            "org_name": org_name,
            "verified": False,
            "verification_info": None,
            "urls_scraped": [],
            "scraped_content": [],
            "knowledge_base": None,
            "token_count": 0
        }
        
        # Step 1: Verify organization (if name provided)
        if org_name and not skip_verification:
            verification = self.verify_organization(org_name)
            result["verification_info"] = verification
            
            if verification.get("likely_url"):
                if not urls:
                    urls = []
                if verification["likely_url"] not in urls:
                    urls.insert(0, verification["likely_url"])
        
        # Step 2: Scrape URLs
        if urls:
            for url in urls[:5]:  # Limit to 5 URLs
                scraped = self.fetch_url(url)
                result["scraped_content"].append(scraped)
                if scraped.get("success"):
                    result["urls_scraped"].append(url)
        
        # Step 3: Generate knowledge base
        if result["scraped_content"]:
            kb = self.generate_knowledge_base(
                org_name or "Organization",
                result["scraped_content"]
            )
            result["knowledge_base"] = kb
            result["token_count"] = len(kb.split()) * 1.3  # Rough token estimate
            result["verified"] = True
        
        return result


def interactive_extract():
    """Interactive CLI for knowledge extraction."""
    print("\n" + "=" * 60)
    print("🧠 KNOWLEDGE BASE EXTRACTOR")
    print("   Context-Rich Organization Knowledge Generator")
    print("=" * 60)
    
    extractor = KnowledgeExtractor()
    
    # Get input
    print("\nEnter organization name OR URL(s) to extract knowledge from:")
    user_input = input(">>> ").strip()
    
    if not user_input:
        print("❌ No input provided. Exiting.")
        return
    
    # Determine if URL or org name
    urls = []
    org_name = None
    
    if user_input.startswith("http") or "." in user_input.split()[0]:
        # Likely URL(s)
        urls = user_input.split()
        org_name = input("\nOrganization name (optional): ").strip() or None
    else:
        org_name = user_input
    
    # Step 1: Verify
    if org_name and not urls:
        print(f"\n🔍 Searching for: {org_name}...")
        verification = extractor.verify_organization(org_name)
        
        if verification.get("summary"):
            print("\n" + "-" * 60)
            print("📋 ORGANIZATION SUMMARY:")
            print("-" * 60)
            print(verification["summary"])
            
            if verification.get("likely_url"):
                print(f"\n🔗 Likely Website: {verification['likely_url']}")
            
            print("-" * 60)
            confirm = input("\nIs this the correct organization? [Y/n]: ").strip().lower()
            
            if confirm == 'n':
                print("\n❌ Extraction cancelled. Please provide a direct URL.")
                new_url = input("Enter URL (or press Enter to exit): ").strip()
                if new_url:
                    urls = [new_url]
                else:
                    return
            else:
                urls = [verification.get("likely_url")] if verification.get("likely_url") else []
    
    # Step 2: Additional URLs
    if urls:
        print(f"\n📌 Current URLs: {urls}")
        additional = input("Add more URLs? (comma-separated, or press Enter to skip): ").strip()
        if additional:
            urls.extend([u.strip() for u in additional.split(",") if u.strip()])
    
    # Step 3: Extract
    if not urls:
        print("❌ No URLs to scrape. Exiting.")
        return
    
    print(f"\n🚀 Starting extraction from {len(urls)} URL(s)...")
    
    result = extractor.extract(org_name=org_name, urls=urls, skip_verification=True)
    
    if result.get("knowledge_base"):
        print("\n" + "=" * 60)
        print("✅ KNOWLEDGE BASE GENERATED")
        print(f"   Token Count: ~{int(result['token_count'])}")
        print("=" * 60)
        print(result["knowledge_base"])
        
        # Save to file
        save = input("\n💾 Save to file? [Y/n]: ").strip().lower()
        if save != 'n':
            filename = f"{(org_name or 'knowledge').replace(' ', '_').lower()}_knowledge.md"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(result["knowledge_base"])
            print(f"✅ Saved to: {filename}")
    else:
        print("❌ Failed to generate knowledge base.")


async def main():
    parser = argparse.ArgumentParser(
        description="Extract comprehensive knowledge bases from organizations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python knowledge_extractor.py "Daytona"
  python knowledge_extractor.py https://daytona.io
  python knowledge_extractor.py "OpenAI" --urls https://openai.com
  python knowledge_extractor.py --interactive
        """
    )
    
    parser.add_argument(
        'input',
        nargs='?',
        help='Organization name or URL'
    )
    
    parser.add_argument(
        '--urls', '-u',
        nargs='+',
        help='Additional URLs to scrape'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path (default: {org}_knowledge.md)'
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Run in interactive mode'
    )
    
    parser.add_argument(
        '--skip-verify',
        action='store_true',
        help='Skip organization verification'
    )
    
    parser.add_argument(
        '--model', '-m',
        type=str,
        default=DEFAULT_MODEL,
        help=f'OpenRouter model to use (default: {DEFAULT_MODEL})'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )
    
    args = parser.parse_args()
    
    # Interactive mode
    if args.interactive or not args.input:
        interactive_extract()
        return
    
    # CLI mode
    extractor = KnowledgeExtractor(model=args.model)
    
    # Determine input type
    urls = args.urls or []
    org_name = None
    
    if args.input.startswith("http"):
        urls.insert(0, args.input)
    else:
        org_name = args.input
    
    # Extract
    result = extractor.extract(
        org_name=org_name,
        urls=urls,
        skip_verification=args.skip_verify
    )
    
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result.get("knowledge_base"):
            print(result["knowledge_base"])
            
            # Save if output specified
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(result["knowledge_base"])
                print(f"\n✅ Saved to: {args.output}")
        else:
            print("❌ Failed to generate knowledge base.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
