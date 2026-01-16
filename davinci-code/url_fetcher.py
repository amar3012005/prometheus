#!/usr/bin/env python3
"""
URL Content Fetcher - Standalone Web Scraping Tool

Extracts and summarizes content from URLs using web scraping and optional 
Google Custom Search API for related information.

Usage:
    python url_fetcher.py https://example.com
    python url_fetcher.py https://example.com --summarize
    python url_fetcher.py --search "query here"
    
Environment Variables (optional):
    GOOGLE_SEARCH_API_KEY: Google Custom Search API key
    GOOGLE_CSE_ID: Google Custom Search Engine ID
    GEMINI_API_KEY: For summarization (optional)
"""

import os
import sys
import argparse
import asyncio
import json
import re
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

# Web scraping
import requests
from bs4 import BeautifulSoup

# Optional: Google Search API
try:
    from googleapiclient.discovery import build as google_build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

# Optional: Gemini for summarization
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    try:
        import google.generativeai as genai
        types = None
        GEMINI_AVAILABLE = True
    except ImportError:
        GEMINI_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


class URLFetcher:
    """
    Fetches and processes content from URLs.
    
    Features:
        - HTML content extraction and cleaning
        - Text summarization via Gemini (optional)
        - Google Custom Search integration (optional)
        - Structured output (JSON, Markdown)
    """
    
    def __init__(
        self,
        google_api_key: Optional[str] = None,
        google_cse_id: Optional[str] = None,
        gemini_api_key: Optional[str] = None
    ):
        """
        Initialize the URL fetcher.
        
        Args:
            google_api_key: Google Custom Search API key
            google_cse_id: Google Custom Search Engine ID  
            gemini_api_key: Gemini API key for summarization
        """
        self.google_api_key = google_api_key or os.getenv("GOOGLE_SEARCH_API_KEY", "")
        self.google_cse_id = google_cse_id or os.getenv("GOOGLE_CSE_ID", "")
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        
        # Initialize Gemini if available
        self.gemini_model = None
        self.use_new_api = False
        if GEMINI_AVAILABLE and self.gemini_api_key:
            try:
                # Try new API first
                if types is not None:
                    self.client = genai.Client(api_key=self.gemini_api_key)
                    self.use_new_api = True
                    self.gemini_model = "gemini-2.0-flash-exp"
                    logger.info("✅ Gemini (new API) initialized for summarization")
                else:
                    # Fall back to old API
                    genai.configure(api_key=self.gemini_api_key)
                    self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
                    logger.info("✅ Gemini (legacy API) initialized for summarization")
            except Exception as e:
                logger.warning(f"⚠️ Gemini initialization failed: {e}")
        
        # Request headers (mimic browser)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def fetch_url(self, url: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Fetch and extract content from a URL.
        
        Args:
            url: The URL to fetch
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary with:
                - url: The fetched URL
                - title: Page title
                - meta_description: Meta description
                - content: Main text content (cleaned)
                - headings: List of headings (h1, h2, h3)
                - links: List of links on the page
                - word_count: Approximate word count
                - success: Boolean success flag
                - error: Error message if failed
        """
        result = {
            "url": url,
            "title": "",
            "meta_description": "",
            "content": "",
            "headings": [],
            "links": [],
            "word_count": 0,
            "success": False,
            "error": None
        }
        
        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme:
                url = f"https://{url}"
            
            logger.info(f"🌐 Fetching: {url}")
            
            # Make request
            response = requests.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            
            # Parse HTML
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
                    if text:
                        headings.append({"level": h_level, "text": text})
            result["headings"] = headings
            
            # Extract links (first 20)
            links = []
            for a in soup.find_all('a', href=True)[:20]:
                href = a['href']
                text = a.get_text().strip()
                if text and href.startswith('http'):
                    links.append({"text": text[:100], "url": href})
            result["links"] = links
            
            # Extract main content (remove scripts, styles, nav, footer)
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript']):
                tag.decompose()
            
            # Try to find main content area
            main_content = soup.find('main') or soup.find('article') or soup.find('div', {'class': re.compile(r'content|article|post')})
            
            if main_content:
                content_text = main_content.get_text(separator='\n', strip=True)
            else:
                # Fallback to body
                body = soup.find('body')
                content_text = body.get_text(separator='\n', strip=True) if body else ""
            
            # Clean up content
            content_text = self._clean_text(content_text)
            result["content"] = content_text
            result["word_count"] = len(content_text.split())
            result["success"] = True
            
            logger.info(f"✅ Fetched: {result['title'][:50]}... ({result['word_count']} words)")
            
        except requests.exceptions.RequestException as e:
            result["error"] = f"Request failed: {str(e)}"
            logger.error(f"❌ {result['error']}")
        except Exception as e:
            result["error"] = f"Parsing failed: {str(e)}"
            logger.error(f"❌ {result['error']}")
        
        return result
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text by removing extra whitespace."""
        # Remove multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove multiple spaces
        text = re.sub(r' {2,}', ' ', text)
        # Remove leading/trailing whitespace per line
        lines = [line.strip() for line in text.split('\n')]
        return '\n'.join(line for line in lines if line)
    
    async def summarize(self, content: str, query: Optional[str] = None) -> str:
        """
        Summarize content using Gemini.
        
        Args:
            content: The content to summarize
            query: Optional query to focus the summary
            
        Returns:
            Summary text
        """
        if not self.gemini_model:
            return "⚠️ Summarization not available (Gemini not configured)"
        
        try:
            prompt = f"""Summarize the following web content in a clear, concise manner.
Focus on the key information and main points.
{f"Specifically focus on: {query}" if query else ""}

CONTENT:
{content[:8000]}

SUMMARY (3-5 paragraphs):"""
            
            if self.use_new_api:
                # New API
                response = self.client.models.generate_content(
                    model=self.gemini_model,
                    contents=prompt
                )
                return response.text.strip()
            else:
                # Legacy API
                response = self.gemini_model.generate_content(prompt)
                return response.text.strip()
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return f"⚠️ Summarization failed: {e}"
    
    async def google_search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Perform a Google Custom Search.
        
        Args:
            query: Search query
            num_results: Number of results (max 10)
            
        Returns:
            List of search results with title, link, snippet
        """
        if not GOOGLE_API_AVAILABLE:
            logger.warning("Google API not available (install google-api-python-client)")
            return []
        
        if not self.google_api_key or not self.google_cse_id:
            logger.warning("Google Search not configured (missing API key or CSE ID)")
            return []
        
        try:
            logger.info(f"🔍 Searching: {query}")
            
            # Build service
            service = google_build("customsearch", "v1", developerKey=self.google_api_key)
            
            # Execute search
            result = service.cse().list(
                q=query,
                cx=self.google_cse_id,
                num=min(num_results, 10)
            ).execute()
            
            if 'items' not in result:
                return []
            
            results = []
            for item in result['items']:
                results.append({
                    "title": item.get('title', 'No Title'),
                    "link": item.get('link', ''),
                    "snippet": item.get('snippet', 'No description')
                })
            
            logger.info(f"✅ Found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"❌ Google search failed: {e}")
            return []
    
    async def fetch_and_summarize(self, url: str) -> Dict[str, Any]:
        """
        Fetch a URL and summarize its content.
        
        Args:
            url: The URL to fetch and summarize
            
        Returns:
            Dictionary with fetched content and summary
        """
        # Fetch content
        result = self.fetch_url(url)
        
        if result["success"] and self.gemini_model:
            # Summarize
            summary = await self.summarize(result["content"])
            result["summary"] = summary
        
        return result


def print_result(result: Dict[str, Any], format: str = "text"):
    """Print result in specified format."""
    if format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    
    if not result.get("success", False):
        print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
        return
    
    print("\n" + "=" * 60)
    print(f"📄 {result.get('title', 'No Title')}")
    print("=" * 60)
    
    if result.get("meta_description"):
        print(f"\n📝 Description: {result['meta_description']}")
    
    if result.get("headings"):
        print("\n📌 Headings:")
        for h in result["headings"][:10]:
            indent = "  " if h["level"] == "h1" else "    " if h["level"] == "h2" else "      "
            print(f"{indent}{h['level'].upper()}: {h['text'][:80]}")
    
    print(f"\n📊 Word Count: {result.get('word_count', 0)}")
    
    if result.get("summary"):
        print("\n" + "-" * 60)
        print("📖 SUMMARY:")
        print("-" * 60)
        print(result["summary"])
    
    if result.get("content"):
        print("\n" + "-" * 60)
        print("📄 CONTENT PREVIEW (first 500 chars):")
        print("-" * 60)
        print(result["content"][:500] + "...")
    
    print("\n" + "=" * 60)


async def main():
    parser = argparse.ArgumentParser(
        description="Fetch and extract information from URLs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python url_fetcher.py https://daytona.io
  python url_fetcher.py https://daytona.io --summarize
  python url_fetcher.py --search "Daytona dev environments"
  python url_fetcher.py https://url1.com https://url2.com --json
        """
    )
    
    parser.add_argument(
        'urls',
        nargs='*',
        help='URLs to fetch (can be multiple)'
    )
    
    parser.add_argument(
        '--search', '-s',
        type=str,
        help='Perform a Google search instead of fetching URLs'
    )
    
    parser.add_argument(
        '--summarize',
        action='store_true',
        help='Summarize the fetched content using Gemini'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    
    parser.add_argument(
        '--num-results', '-n',
        type=int,
        default=5,
        help='Number of search results (default: 5)'
    )
    
    args = parser.parse_args()
    
    # Initialize fetcher
    fetcher = URLFetcher()
    
    # Handle search mode
    if args.search:
        results = await fetcher.google_search(args.search, args.num_results)
        
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print(f"\n🔍 Search Results for: {args.search}\n")
            print("=" * 60)
            for i, r in enumerate(results, 1):
                print(f"\n{i}. {r['title']}")
                print(f"   🔗 {r['link']}")
                print(f"   📝 {r['snippet']}")
            print("\n" + "=" * 60)
        return
    
    # Handle URL fetching
    if not args.urls:
        parser.print_help()
        print("\n⚠️ Please provide at least one URL or use --search")
        return
    
    for url in args.urls:
        if args.summarize:
            result = await fetcher.fetch_and_summarize(url)
        else:
            result = fetcher.fetch_url(url)
        
        print_result(result, format="json" if args.json else "text")


if __name__ == "__main__":
    asyncio.run(main())
