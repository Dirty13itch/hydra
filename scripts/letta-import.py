#!/usr/bin/env python3
"""
Letta Knowledge Import Tool

Imports documents into Letta memory layer for RAG and agent memory.
Supports various file formats: markdown, text, PDF, code files.

Usage:
    python letta-import.py import ./docs/
    python letta-import.py import ./file.md --agent hydra-steward
    python letta-import.py list
    python letta-import.py query "How does TabbyAPI work?"
"""

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

# Configuration
LETTA_URL = os.environ.get("LETTA_URL", "http://192.168.1.244:8283")
DEFAULT_AGENT = "hydra-steward"

# File types to process
SUPPORTED_EXTENSIONS = {
    ".md": "markdown",
    ".txt": "text",
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".nix": "nix",
    ".sh": "shell",
    ".sql": "sql",
}

# Skip patterns
SKIP_PATTERNS = [
    r"node_modules",
    r"\.git",
    r"__pycache__",
    r"\.venv",
    r"venv",
    r"dist",
    r"build",
    r"\.next",
]


@dataclass
class Document:
    """Document to import into Letta."""
    content: str
    source: str
    title: str
    doc_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class LettaClient:
    """Client for Letta API."""

    def __init__(self, base_url: str = LETTA_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> requests.Response:
        """Make HTTP request to Letta API."""
        url = urljoin(self.base_url + "/", endpoint.lstrip("/"))
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def health_check(self) -> bool:
        """Check if Letta is reachable."""
        try:
            resp = self._request("GET", "/v1/health")
            return resp.status_code == 200
        except Exception:
            return False

    def list_agents(self) -> List[Dict]:
        """List all Letta agents."""
        resp = self._request("GET", "/v1/agents")
        return resp.json()

    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """Get agent details."""
        try:
            resp = self._request("GET", f"/v1/agents/{agent_id}")
            return resp.json()
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def get_agent_by_name(self, name: str) -> Optional[Dict]:
        """Find agent by name."""
        agents = self.list_agents()
        for agent in agents:
            if agent.get("name") == name:
                return agent
        return None

    def create_agent(
        self,
        name: str,
        system_prompt: Optional[str] = None,
        memory_blocks: Optional[List[Dict]] = None,
    ) -> Dict:
        """Create a new Letta agent."""
        payload = {
            "name": name,
            "description": f"Hydra agent: {name}",
        }

        if system_prompt:
            payload["system"] = system_prompt

        if memory_blocks:
            payload["memory"] = {"memory_blocks": memory_blocks}

        resp = self._request("POST", "/v1/agents", json=payload)
        return resp.json()

    def add_memory_block(
        self,
        agent_id: str,
        label: str,
        value: str,
    ) -> Dict:
        """Add or update a memory block for an agent."""
        payload = {
            "label": label,
            "value": value,
            "limit": 5000,  # Character limit
        }

        resp = self._request(
            "POST",
            f"/v1/agents/{agent_id}/memory/block",
            json=payload
        )
        return resp.json()

    def update_memory_block(
        self,
        agent_id: str,
        block_id: str,
        value: str,
    ) -> Dict:
        """Update an existing memory block."""
        payload = {"value": value}

        resp = self._request(
            "PATCH",
            f"/v1/agents/{agent_id}/memory/block/{block_id}",
            json=payload
        )
        return resp.json()

    def get_memory_blocks(self, agent_id: str) -> List[Dict]:
        """Get all memory blocks for an agent."""
        resp = self._request("GET", f"/v1/agents/{agent_id}/memory")
        return resp.json().get("memory", {}).get("memory_blocks", [])

    def add_archival_memory(
        self,
        agent_id: str,
        text: str,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Add text to agent's archival (long-term) memory."""
        payload = {
            "text": text,
        }

        if metadata:
            payload["metadata"] = metadata

        resp = self._request(
            "POST",
            f"/v1/agents/{agent_id}/archival",
            json=payload
        )
        return resp.json()

    def search_archival_memory(
        self,
        agent_id: str,
        query: str,
        count: int = 10,
    ) -> List[Dict]:
        """Search agent's archival memory."""
        resp = self._request(
            "GET",
            f"/v1/agents/{agent_id}/archival",
            params={"query": query, "count": count}
        )
        return resp.json()

    def send_message(
        self,
        agent_id: str,
        message: str,
        role: str = "user",
    ) -> Dict:
        """Send a message to an agent."""
        payload = {
            "messages": [
                {"role": role, "content": message}
            ],
            "stream_steps": False,
            "stream_tokens": False,
        }

        resp = self._request(
            "POST",
            f"/v1/agents/{agent_id}/messages",
            json=payload
        )
        return resp.json()


class DocumentProcessor:
    """Processes files for import into Letta."""

    def __init__(self, chunk_size: int = 2000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        path_str = str(path)
        for pattern in SKIP_PATTERNS:
            if re.search(pattern, path_str):
                return True
        return False

    def get_doc_type(self, path: Path) -> Optional[str]:
        """Get document type from extension."""
        return SUPPORTED_EXTENSIONS.get(path.suffix.lower())

    def read_file(self, path: Path) -> Optional[str]:
        """Read file contents."""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {path}: {e}")
            return None

    def extract_title(self, content: str, path: Path) -> str:
        """Extract title from content or filename."""
        # Try to find markdown header
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()

        # Use filename without extension
        return path.stem.replace("-", " ").replace("_", " ").title()

    def chunk_content(self, content: str) -> List[str]:
        """Split content into chunks with overlap."""
        if len(content) <= self.chunk_size:
            return [content]

        chunks = []
        start = 0

        while start < len(content):
            end = start + self.chunk_size

            # Try to break at paragraph boundary
            if end < len(content):
                # Look for paragraph break near end
                para_break = content.rfind("\n\n", start, end)
                if para_break > start + self.chunk_size // 2:
                    end = para_break + 2

            chunks.append(content[start:end].strip())

            # Move start with overlap
            start = end - self.chunk_overlap

        return chunks

    def process_file(self, path: Path) -> List[Document]:
        """Process a single file into documents."""
        if self.should_skip(path):
            return []

        doc_type = self.get_doc_type(path)
        if not doc_type:
            return []

        content = self.read_file(path)
        if not content or len(content.strip()) < 50:
            return []

        title = self.extract_title(content, path)
        chunks = self.chunk_content(content)

        documents = []
        for i, chunk in enumerate(chunks):
            doc = Document(
                content=chunk,
                source=str(path),
                title=f"{title} (part {i + 1})" if len(chunks) > 1 else title,
                doc_type=doc_type,
                metadata={
                    "file_path": str(path),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "file_type": doc_type,
                    "imported_at": datetime.utcnow().isoformat(),
                },
            )
            documents.append(doc)

        return documents

    def process_directory(self, directory: Path) -> List[Document]:
        """Process all files in a directory."""
        documents = []

        for path in directory.rglob("*"):
            if path.is_file():
                docs = self.process_file(path)
                documents.extend(docs)

        return documents


def cmd_import(args):
    """Import documents into Letta."""
    client = LettaClient()
    processor = DocumentProcessor()

    # Check Letta is reachable
    if not client.health_check():
        print(f"Error: Cannot connect to Letta at {LETTA_URL}")
        sys.exit(1)

    # Get or create agent
    agent_name = args.agent or DEFAULT_AGENT
    agent = client.get_agent_by_name(agent_name)

    if not agent:
        print(f"Creating agent: {agent_name}")
        agent = client.create_agent(
            name=agent_name,
            system_prompt="You are the Hydra Steward, an AI assistant managing the Hydra cluster infrastructure.",
        )

    agent_id = agent["id"]
    print(f"Using agent: {agent_name} ({agent_id})")

    # Process input path
    input_path = Path(args.path)

    if input_path.is_file():
        documents = processor.process_file(input_path)
    elif input_path.is_dir():
        documents = processor.process_directory(input_path)
    else:
        print(f"Error: Path not found: {input_path}")
        sys.exit(1)

    print(f"Found {len(documents)} document chunks to import")

    # Import documents
    success = 0
    failed = 0

    for doc in documents:
        try:
            # Format content with metadata
            text = f"""
# {doc.title}

Source: {doc.source}
Type: {doc.doc_type}

{doc.content}
""".strip()

            client.add_archival_memory(
                agent_id,
                text,
                metadata=doc.metadata,
            )
            success += 1
            print(f"  ✓ Imported: {doc.title}")

        except Exception as e:
            failed += 1
            print(f"  ✗ Failed: {doc.title} - {e}")

    print(f"\nImport complete: {success} succeeded, {failed} failed")


def cmd_list(args):
    """List Letta agents and their memory."""
    client = LettaClient()

    if not client.health_check():
        print(f"Error: Cannot connect to Letta at {LETTA_URL}")
        sys.exit(1)

    agents = client.list_agents()

    print(f"=== Letta Agents ({len(agents)}) ===\n")

    for agent in agents:
        print(f"Agent: {agent.get('name', 'unnamed')}")
        print(f"  ID: {agent.get('id')}")
        print(f"  Created: {agent.get('created_at', 'unknown')}")

        # Get memory blocks
        try:
            blocks = client.get_memory_blocks(agent["id"])
            print(f"  Memory blocks: {len(blocks)}")
            for block in blocks:
                label = block.get("label", "unknown")
                size = len(block.get("value", ""))
                print(f"    - {label}: {size} chars")
        except Exception:
            pass

        print()


def cmd_query(args):
    """Query Letta agent's knowledge."""
    client = LettaClient()

    if not client.health_check():
        print(f"Error: Cannot connect to Letta at {LETTA_URL}")
        sys.exit(1)

    agent_name = args.agent or DEFAULT_AGENT
    agent = client.get_agent_by_name(agent_name)

    if not agent:
        print(f"Agent not found: {agent_name}")
        sys.exit(1)

    agent_id = agent["id"]

    # Search archival memory
    results = client.search_archival_memory(
        agent_id,
        args.query,
        count=args.count,
    )

    print(f"=== Search Results for: {args.query} ===\n")

    for i, result in enumerate(results, 1):
        text = result.get("text", "")[:500]
        print(f"{i}. {text}...")
        print()


def cmd_chat(args):
    """Chat with Letta agent."""
    client = LettaClient()

    if not client.health_check():
        print(f"Error: Cannot connect to Letta at {LETTA_URL}")
        sys.exit(1)

    agent_name = args.agent or DEFAULT_AGENT
    agent = client.get_agent_by_name(agent_name)

    if not agent:
        print(f"Agent not found: {agent_name}")
        sys.exit(1)

    agent_id = agent["id"]

    print(f"Chatting with {agent_name}. Type 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ["quit", "exit", "q"]:
                break

            response = client.send_message(agent_id, user_input)

            # Extract assistant response
            messages = response.get("messages", [])
            for msg in messages:
                if msg.get("message_type") == "assistant_message":
                    print(f"\nAgent: {msg.get('content', '')}\n")
                    break

        except KeyboardInterrupt:
            print("\n")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Letta Knowledge Import Tool")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Import command
    import_parser = subparsers.add_parser("import", help="Import documents")
    import_parser.add_argument("path", help="File or directory to import")
    import_parser.add_argument("--agent", "-a", help="Target agent name")

    # List command
    list_parser = subparsers.add_parser("list", help="List agents")

    # Query command
    query_parser = subparsers.add_parser("query", help="Query agent knowledge")
    query_parser.add_argument("query", help="Search query")
    query_parser.add_argument("--agent", "-a", help="Agent name")
    query_parser.add_argument("--count", "-n", type=int, default=5, help="Number of results")

    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Chat with agent")
    chat_parser.add_argument("--agent", "-a", help="Agent name")

    args = parser.parse_args()

    if args.command == "import":
        cmd_import(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "query":
        cmd_query(args)
    elif args.command == "chat":
        cmd_chat(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
