"""
Web Research Tools for CrewAI Integration

Provides tools for agents to search the web and crawl pages using
the Hydra cluster's SearXNG and Firecrawl services.
"""

import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    source: str
    score: float = 0.0


@dataclass
class CrawlResult:
    """Result of crawling a webpage."""
    url: str
    title: str
    content: str
    markdown: Optional[str]
    links: List[str]
    metadata: Dict[str, Any]
    crawled_at: datetime


class SearXNGTool:
    """
    Tool for searching the web using SearXNG.

    SearXNG is a privacy-respecting metasearch engine that aggregates
    results from multiple search engines.
    """

    def __init__(self, base_url: str = "http://192.168.1.244:8888"):
        self.base_url = base_url

    async def search(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        engines: Optional[List[str]] = None,
        language: str = "en",
        time_range: Optional[str] = None,
        max_results: int = 10
    ) -> List[SearchResult]:
        """
        Search the web using SearXNG.

        Args:
            query: Search query
            categories: Categories to search (general, images, news, etc.)
            engines: Specific engines to use (google, bing, duckduckgo, etc.)
            language: Result language
            time_range: Time range filter (day, week, month, year)
            max_results: Maximum number of results

        Returns:
            List of search results
        """
        results = []

        params = {
            "q": query,
            "format": "json",
            "language": language,
        }

        if categories:
            params["categories"] = ",".join(categories)
        if engines:
            params["engines"] = ",".join(engines)
        if time_range:
            params["time_range"] = time_range

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{self.base_url}/search", params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    for r in data.get("results", [])[:max_results]:
                        results.append(SearchResult(
                            title=r.get("title", ""),
                            url=r.get("url", ""),
                            snippet=r.get("content", ""),
                            source=r.get("engine", "unknown"),
                            score=r.get("score", 0.0)
                        ))
        except Exception as e:
            print(f"SearXNG search error: {e}")

        return results

    async def search_news(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Search for news articles."""
        return await self.search(
            query,
            categories=["news"],
            max_results=max_results
        )

    async def search_academic(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Search for academic/scientific content."""
        return await self.search(
            query,
            categories=["science"],
            engines=["google_scholar", "semantic_scholar", "arxiv"],
            max_results=max_results
        )

    async def search_code(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Search for code/technical content."""
        return await self.search(
            query,
            categories=["it"],
            engines=["github", "stackoverflow", "gitlab"],
            max_results=max_results
        )


class FirecrawlTool:
    """
    Tool for crawling and extracting content from web pages.

    Firecrawl converts web pages to clean markdown, extracts
    structured data, and handles JavaScript rendering.
    """

    def __init__(self, base_url: str = "http://192.168.1.244:3005"):
        self.base_url = base_url

    async def crawl(
        self,
        url: str,
        extract_links: bool = True,
        include_html: bool = False,
        wait_for_selector: Optional[str] = None
    ) -> Optional[CrawlResult]:
        """
        Crawl a single webpage and extract its content.

        Args:
            url: URL to crawl
            extract_links: Whether to extract links from the page
            include_html: Whether to include raw HTML in result
            wait_for_selector: CSS selector to wait for (for JS-heavy pages)

        Returns:
            CrawlResult with page content, or None if failed
        """
        try:
            payload = {
                "url": url,
                "formats": ["markdown"],
            }

            if wait_for_selector:
                payload["waitFor"] = wait_for_selector

            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.base_url}/v0/scrape",
                    json=payload
                )

                if resp.status_code == 200:
                    data = resp.json()
                    content_data = data.get("data", {})

                    # Extract links from content
                    links = []
                    if extract_links:
                        links = content_data.get("links", [])

                    return CrawlResult(
                        url=url,
                        title=content_data.get("metadata", {}).get("title", ""),
                        content=content_data.get("content", ""),
                        markdown=content_data.get("markdown", ""),
                        links=links,
                        metadata=content_data.get("metadata", {}),
                        crawled_at=datetime.now()
                    )

        except Exception as e:
            print(f"Firecrawl error: {e}")

        return None

    async def crawl_multiple(
        self,
        urls: List[str],
        max_concurrent: int = 5
    ) -> List[CrawlResult]:
        """
        Crawl multiple URLs concurrently.

        Args:
            urls: List of URLs to crawl
            max_concurrent: Maximum concurrent requests

        Returns:
            List of CrawlResults (may be fewer than input if some fail)
        """
        import asyncio

        results = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def crawl_with_semaphore(url: str) -> Optional[CrawlResult]:
            async with semaphore:
                return await self.crawl(url)

        tasks = [crawl_with_semaphore(url) for url in urls]
        crawl_results = await asyncio.gather(*tasks)

        for result in crawl_results:
            if result:
                results.append(result)

        return results

    async def extract_structured(
        self,
        url: str,
        schema: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from a page based on a schema.

        Args:
            url: URL to crawl
            schema: JSON schema describing the data to extract

        Returns:
            Extracted data matching the schema
        """
        try:
            payload = {
                "url": url,
                "formats": ["extract"],
                "extract": {
                    "schema": schema
                }
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.base_url}/v0/scrape",
                    json=payload
                )

                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("data", {}).get("extract", {})

        except Exception as e:
            print(f"Firecrawl extract error: {e}")

        return None


class WebResearchTool:
    """
    Combined tool for web research that uses both SearXNG and Firecrawl.

    Provides high-level research capabilities for CrewAI agents.
    """

    def __init__(
        self,
        searxng_url: str = "http://192.168.1.244:8888",
        firecrawl_url: str = "http://192.168.1.244:3005"
    ):
        self.searxng = SearXNGTool(searxng_url)
        self.firecrawl = FirecrawlTool(firecrawl_url)

    async def research_topic(
        self,
        topic: str,
        max_sources: int = 5,
        include_content: bool = True
    ) -> Dict[str, Any]:
        """
        Research a topic by searching and crawling top results.

        Args:
            topic: Topic to research
            max_sources: Maximum number of sources to crawl
            include_content: Whether to include full page content

        Returns:
            Research results with sources and content
        """
        # Search for the topic
        search_results = await self.searxng.search(topic, max_results=max_sources * 2)

        # Crawl top results
        sources = []
        urls_to_crawl = [r.url for r in search_results[:max_sources]]

        if include_content:
            crawl_results = await self.firecrawl.crawl_multiple(urls_to_crawl)
            for crawl in crawl_results:
                sources.append({
                    "url": crawl.url,
                    "title": crawl.title,
                    "content": crawl.markdown or crawl.content,
                    "crawled_at": crawl.crawled_at.isoformat()
                })
        else:
            for result in search_results[:max_sources]:
                sources.append({
                    "url": result.url,
                    "title": result.title,
                    "snippet": result.snippet,
                    "source": result.source
                })

        return {
            "topic": topic,
            "sources_searched": len(search_results),
            "sources_crawled": len(sources),
            "sources": sources,
            "timestamp": datetime.now().isoformat()
        }

    async def fact_check(
        self,
        claim: str,
        max_sources: int = 3
    ) -> Dict[str, Any]:
        """
        Fact-check a claim by searching multiple sources.

        Args:
            claim: The claim to fact-check
            max_sources: Number of sources to check

        Returns:
            Fact-check results with supporting/contradicting evidence
        """
        # Search for the claim
        search_results = await self.searxng.search(
            f'"{claim}" fact check',
            categories=["news", "general"],
            max_results=max_sources * 2
        )

        # Crawl and analyze
        evidence = []
        urls = [r.url for r in search_results[:max_sources]]
        crawl_results = await self.firecrawl.crawl_multiple(urls)

        for crawl in crawl_results:
            evidence.append({
                "url": crawl.url,
                "title": crawl.title,
                "content_preview": (crawl.markdown or crawl.content)[:500],
            })

        return {
            "claim": claim,
            "evidence_sources": len(evidence),
            "evidence": evidence,
            "timestamp": datetime.now().isoformat()
        }

    async def compare_products(
        self,
        product1: str,
        product2: str
    ) -> Dict[str, Any]:
        """
        Compare two products by searching for comparison articles.

        Args:
            product1: First product name
            product2: Second product name

        Returns:
            Comparison data from multiple sources
        """
        query = f"{product1} vs {product2} comparison review"
        search_results = await self.searxng.search(query, max_results=5)

        comparisons = []
        urls = [r.url for r in search_results[:3]]
        crawl_results = await self.firecrawl.crawl_multiple(urls)

        for crawl in crawl_results:
            comparisons.append({
                "url": crawl.url,
                "title": crawl.title,
                "content": crawl.markdown or crawl.content
            })

        return {
            "products": [product1, product2],
            "comparison_sources": len(comparisons),
            "comparisons": comparisons,
            "timestamp": datetime.now().isoformat()
        }
