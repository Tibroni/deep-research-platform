import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.services.search import web_search, scrape_page

async def test_search_and_scrape():
    print("=== Running Search & Scraper Unit Tests ===")
    
    # 1. Test Search
    query = "LangGraph orchestrator Python"
    print(f"Test 1: Running web_search for query: '{query}'")
    try:
        results = await web_search(query, max_results=3)
        assert isinstance(results, list), "Search results should be a list"
        print(f"✓ Search returned {len(results)} results.")
        
        for idx, result in enumerate(results):
            assert "title" in result, f"Result {idx} missing 'title'"
            assert "url" in result, f"Result {idx} missing 'url'"
            assert "snippet" in result, f"Result {idx} missing 'snippet'"
            print(f"  [{idx + 1}] Title: {result['title'][:50]}... | URL: {result['url']}")
            
        if results:
            # 2. Test Scraper with one of the search result URLs
            target_url = results[0]["url"]
            print(f"\nTest 2: Scraping page content from: {target_url}")
            content = await scrape_page(target_url)
            assert isinstance(content, str), "Scraped content should be a string"
            print(f"✓ Scraper returned {len(content)} characters of text.")
            print(f"  Snippet Preview:\n{content[:300]}...\n")
        else:
            print("⚠ No search results found to test scraping, trying Wikipedia...")
            wiki_url = "https://en.wikipedia.org/wiki/Software_agent"
            content = await scrape_page(wiki_url)
            assert isinstance(content, str), "Scraped content should be a string"
            assert len(content) > 0, "Wikipedia page content should not be empty"
            print(f"✓ Scraped Wikipedia. Content length: {len(content)} characters.")
            
        print("✓ ALL TESTS PASSED SUCCESSFULLY!")
        return True
    except Exception as e:
        print(f"✗ TEST FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_search_and_scrape())
    sys.exit(0 if success else 1)
