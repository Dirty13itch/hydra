#!/usr/bin/env python3
"""Letta Memory Tools for Hydra Agent Integration.

Provides helper functions for agents to read/write to Letta archival memory.
"""

import requests
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

LETTA_URL = "http://192.168.1.244:8283"
AGENT_ID = "agent-b3fb1747-1a5b-4c94-b713-11d6403350bf"

class LettaMemory:
    """Interface to Letta archival memory for hydra-steward agent."""

    def __init__(self, base_url: str = LETTA_URL, agent_id: str = AGENT_ID):
        self.base_url = base_url.rstrip('/')
        self.agent_id = agent_id
        self.archival_endpoint = f"{self.base_url}/v1/agents/{self.agent_id}/archival-memory/"

    def add_memory(self, text: str, metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Add a new memory to archival storage.

        Args:
            text: The text content to store
            metadata: Optional metadata dict (will be prepended to text)

        Returns:
            API response dict
        """
        if metadata:
            meta_str = " | ".join(f"{k}={v}" for k, v in metadata.items())
            text = f"[{meta_str}]\n{text}"

        response = requests.post(
            self.archival_endpoint,
            json={"text": text},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        return {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "data": response.json() if response.status_code == 200 else response.text
        }

    def query_memory(self, query: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Query archival memory.

        Args:
            query: Optional search query
            limit: Maximum number of results

        Returns:
            List of memory entries
        """
        params = {"limit": limit}
        if query:
            params["query"] = query

        response = requests.get(
            self.archival_endpoint,
            params=params,
            timeout=30
        )

        if response.status_code == 200:
            return response.json()
        return []

    def log_event(self, event_type: str, details: Dict[str, Any], severity: str = "info") -> Dict[str, Any]:
        """Log an event to agent memory.

        Args:
            event_type: Type of event (e.g., "alert", "action", "observation")
            details: Event details dict
            severity: Event severity (info, warning, error, critical)

        Returns:
            API response dict
        """
        timestamp = datetime.utcnow().isoformat()
        text = f"""[HYDRA EVENT]
Type: {event_type}
Severity: {severity}
Timestamp: {timestamp}
Details: {json.dumps(details, indent=2)}
"""
        return self.add_memory(text, {"type": "event", "severity": severity})

    def log_alert(self, alertname: str, status: str, instance: str, summary: str) -> Dict[str, Any]:
        """Log an alert from Alertmanager.

        Args:
            alertname: Name of the alert
            status: Alert status (firing, resolved)
            instance: Affected instance
            summary: Alert summary

        Returns:
            API response dict
        """
        timestamp = datetime.utcnow().isoformat()
        text = f"""[ALERT {status.upper()}]
Alert: {alertname}
Instance: {instance}
Summary: {summary}
Time: {timestamp}
"""
        severity = "critical" if status == "firing" else "info"
        return self.add_memory(text, {"type": "alert", "alertname": alertname, "severity": severity})

    def log_action(self, action: str, target: str, result: str, details: Optional[str] = None) -> Dict[str, Any]:
        """Log an agent action.

        Args:
            action: Action taken (e.g., "restart_container", "acknowledge_alert")
            target: Target of the action
            result: Result of the action (success, failure)
            details: Optional additional details

        Returns:
            API response dict
        """
        timestamp = datetime.utcnow().isoformat()
        text = f"""[AGENT ACTION]
Action: {action}
Target: {target}
Result: {result}
Time: {timestamp}
"""
        if details:
            text += f"Details: {details}\n"

        return self.add_memory(text, {"type": "action", "action": action, "result": result})

    def get_recent_memories(self, count: int = 5) -> List[str]:
        """Get recent memory entries.

        Args:
            count: Number of entries to retrieve

        Returns:
            List of memory text strings
        """
        memories = self.query_memory(limit=count)
        return [m.get("text", "") for m in memories if isinstance(m, dict)]

    def search_knowledge(self, topic: str) -> List[Dict[str, Any]]:
        """Search for knowledge on a specific topic.

        Args:
            topic: Topic to search for

        Returns:
            List of relevant memory entries
        """
        return self.query_memory(query=topic, limit=20)


def main():
    """Test memory tools."""
    memory = LettaMemory()

    print("Testing Letta Memory Tools")
    print("=" * 50)

    # Test query
    print("\n1. Querying recent memories...")
    recent = memory.get_recent_memories(3)
    for i, m in enumerate(recent, 1):
        print(f"  [{i}] {m[:100]}..." if len(m) > 100 else f"  [{i}] {m}")

    # Test event logging
    print("\n2. Logging test event...")
    result = memory.log_event(
        event_type="test",
        details={"message": "Memory tools test", "component": "letta_memory_tools.py"},
        severity="info"
    )
    print(f"  Result: {result['success']} (status: {result['status_code']})")

    # Test search
    print("\n3. Searching for 'infrastructure'...")
    results = memory.search_knowledge("infrastructure")
    print(f"  Found {len(results)} entries")

    print("\n" + "=" * 50)
    print("Tests complete!")


if __name__ == "__main__":
    main()
