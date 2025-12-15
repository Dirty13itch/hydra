"""
Search Tools for Hydra Agents

Provides web search and web scraping capabilities using SearXNG and Firecrawl.
"""

import requests
from typing import List, Dict, Optional, Any
from langchain.tools import tool

from .config import get_config


@tool
def web_search(query: str, num_results: int = 5, categories: str = "general") -> str:
    """
    Search the web using SearXNG metasearch engine.

    Args:
        query: The search query
        num_results: Number of results to return (default: 5)
        categories: Search categories - general, images, news, science, files (default: general)

    Returns:
        Formatted search results with titles, URLs, and snippets
    """
    config = get_config()

    try:
        response = requests.get(
            f"{config.searxng_url}/search",
            params={
                "q": query,
                "format": "json",
                "categories": categories,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])[:num_results]

        if not results:
            return f"No results found for: {query}"

        formatted = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            url = r.get("url", "")
            content = r.get("content", "")[:200]
            formatted.append(f"{i}. **{title}**\n   URL: {url}\n   {content}")

        return "\n\n".join(formatted)

    except requests.exceptions.RequestException as e:
        return f"Search failed: {str(e)}"


@tool
def crawl_url(url: str, output_format: str = "markdown") -> str:
    """
    Scrape a web page and convert it to LLM-ready format using Firecrawl.

    Args:
        url: The URL to scrape
        output_format: Output format - markdown, html, text (default: markdown)

    Returns:
        The page content in the specified format
    """
    config = get_config()

    try:
        response = requests.post(
            f"{config.firecrawl_url}/v1/scrape",
            json={"url": url, "output_format": output_format},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        content = data.get("data", {}).get("content", "")
        if not content:
            content = data.get("data", {}).get("markdown", "")
        if not content:
            return f"No content extracted from: {url}"

        # Truncate very long content
        if len(content) > 10000:
            content = content[:10000] + "\n\n... [content truncated]"

        return content

    except requests.exceptions.RequestException as e:
        return f"Failed to crawl {url}: {str(e)}"


def search_images(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Search for images using SearXNG.

    Args:
        query: The search query
        num_results: Number of results to return

    Returns:
        List of image results with URLs and metadata
    """
    config = get_config()

    try:
        response = requests.get(
            f"{config.searxng_url}/search",
            params={
                "q": query,
                "format": "json",
                "categories": "images",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])[:num_results]
        return [
            {
                "url": r.get("img_src", r.get("url", "")),
                "title": r.get("title", ""),
                "source": r.get("source", ""),
                "thumbnail": r.get("thumbnail_src", ""),
            }
            for r in results
        ]

    except requests.exceptions.RequestException as e:
        return [{"error": str(e)}]


def crawl_site(base_url: str, max_pages: int = 10) -> List[Dict[str, Any]]:
    """
    Crawl multiple pages from a website.

    Args:
        base_url: The starting URL
        max_pages: Maximum number of pages to crawl

    Returns:
        List of page contents with URLs
    """
    config = get_config()

    try:
        response = requests.post(
            f"{config.firecrawl_url}/v1/crawl",
            json={"url": base_url, "limit": max_pages},
            timeout=300,
        )
        response.raise_for_status()
        data = response.json()

        return data.get("data", [])

    except requests.exceptions.RequestException as e:
        return [{"error": str(e), "url": base_url}]
