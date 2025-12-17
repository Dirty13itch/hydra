# Hydra Tools - External Service Clients
"""
Clients for integrating with external services:
- Unraid GraphQL API
- Home Assistant API
- Other service integrations
"""

from .unraid_client import UnraidClient, get_unraid_client

__all__ = ['UnraidClient', 'get_unraid_client']
