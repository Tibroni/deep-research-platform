import logging
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

# Standard Headers to avoid being blocked on scraping
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

async def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Perform a search query using Tavily Search API. 
    If Tavily is not configured or fails, automatically fallback to DuckDuckGo.
    
    Returns:
        List[Dict[str, str]]: A list of results with keys 'title', 'url', and 'snippet'.
    """
    results = []
    
    # Try Tavily Search first if key is present
    if settings.TAVILY_API_KEY:
        try:
            logger.info("Performing Tavily Search...")
            from tavily import TavilyClient
            client = TavilyClient(api_key=settings.TAVILY_API_KEY)
            
            # Synchronous call executed in a thread pool could be done, but Tavily client is simple
            # Let's run it directly or async if supported. We'll do a synchronous wrapper
            # since tavily client runs synchronously.
            response = client.search(query=query, max_results=max_results)
            for res in response.get("results", []):
                results.append({
                    "title": res.get("title", ""),
                    "url": res.get("url", ""),
                    "snippet": res.get("content", "")
                })
            if results:
                logger.info(f"Tavily search successful. Found {len(results)} results.")
                return results
        except Exception as e:
            logger.warning(f"Tavily Search failed: {e}. Falling back to DuckDuckGo.")

    # Fallback to DuckDuckGo Search
    try:
        logger.info("Performing DuckDuckGo Search Fallback...")
        from duckduckgo_search import DDGS
        
        # DDGS can be run inside a sync block.
        with DDGS() as ddgs:
            ddg_results = list(ddgs.text(query, max_results=max_results))
            for res in ddg_results:
                results.append({
                    "title": res.get("title", ""),
                    "url": res.get("href", ""),
                    "snippet": res.get("body", "")
                })
        logger.info(f"DuckDuckGo search completed. Found {len(results)} results.")
        return results
    except Exception as e:
        logger.error(f"DuckDuckGo Search fallback failed: {e}")
        return []

async def scrape_page(url: str, timeout_seconds: int = 10) -> str:
    """
    Fetch the content of a web page and extract clean body text.
    
    Args:
        url: The web URL to scrape.
        timeout_seconds: Timeout for the HTTP request.
        
    Returns:
        str: A clean, text-only representation of the page content.
    """
    if not url or not url.startswith("http"):
        return ""
        
    try:
        logger.info(f"Scraping content from URL: {url}")
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=timeout_seconds) as client:
            response = await client.get(url)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {url}. Status code: {response.status_code}")
                return ""
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style", "header", "footer", "nav", "aside"]):
                script.extract()
                
            # Get text and clean it up
            text = soup.get_text()
            
            # Break into lines and remove leading and trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            clean_text = "\n".join(chunk for chunk in chunks if chunk)
            
            # Limit payload size to avoid overwhelming context window (e.g. 6000 chars)
            if len(clean_text) > 6000:
                clean_text = clean_text[:6000] + "... [Content Truncated]"
                
            return clean_text
            
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return ""
