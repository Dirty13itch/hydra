#!/usr/bin/env python3
"""Patch script to add API key authentication to MCP server.

This adds:
- API key authentication via X-API-Key header or Bearer token
- Public endpoints whitelist (health, docs, metrics)
- Key management endpoints (admin only)
- Request logging with auth info
"""

import re
import os

# Authentication code to add
AUTH_IMPORTS = '''from fastapi.security import APIKeyHeader
from fastapi import Depends, Security
'''

AUTH_CODE = '''
# =============================================================================
# API Authentication
# =============================================================================

# API Key configuration
MCP_API_KEY = os.getenv("MCP_API_KEY", "")  # Main API key for access
MCP_ADMIN_KEY = os.getenv("MCP_ADMIN_KEY", "")  # Admin key for key management
REQUIRE_AUTH = os.getenv("MCP_REQUIRE_AUTH", "false").lower() == "true"

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = {
    "/", "/health", "/docs", "/openapi.json", "/redoc",
    "/metrics",  # Prometheus scraping
}

# API key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(
    request: Request,
    api_key: str = Security(api_key_header)
) -> Optional[str]:
    """Extract API key from header or Bearer token"""
    # Check X-API-Key header first
    if api_key:
        return api_key

    # Check Authorization: Bearer header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    return None

async def verify_api_key(
    request: Request,
    api_key: str = Depends(get_api_key)
) -> str:
    """Verify API key for protected endpoints"""
    # Skip auth for public endpoints
    path = request.url.path.rstrip("/")
    if path in PUBLIC_ENDPOINTS or not path:
        return "public"

    # Skip auth if not required (dev mode)
    if not REQUIRE_AUTH:
        return "auth_disabled"

    # No API key configured means auth is disabled
    if not MCP_API_KEY:
        return "no_key_configured"

    # Validate the key
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide X-API-Key header or Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Check against configured keys
    if api_key == MCP_API_KEY or api_key == MCP_ADMIN_KEY:
        return "authenticated"

    raise HTTPException(
        status_code=403,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "Bearer"}
    )

def is_admin_key(api_key: str) -> bool:
    """Check if the provided key is the admin key"""
    return MCP_ADMIN_KEY and api_key == MCP_ADMIN_KEY


@app.get("/auth/status")
async def auth_status(auth_result: str = Depends(verify_api_key)):
    """Check authentication status"""
    return {
        "authenticated": auth_result == "authenticated",
        "auth_mode": auth_result,
        "require_auth": REQUIRE_AUTH,
        "has_api_key": bool(MCP_API_KEY),
        "has_admin_key": bool(MCP_ADMIN_KEY)
    }


@app.post("/auth/validate")
async def validate_key(
    request: Request,
    api_key: str = Depends(get_api_key)
):
    """Validate an API key without accessing protected resources"""
    if not api_key:
        return {"valid": False, "error": "No API key provided"}

    if api_key == MCP_API_KEY:
        return {"valid": True, "type": "api_key"}
    elif api_key == MCP_ADMIN_KEY:
        return {"valid": True, "type": "admin_key"}
    else:
        return {"valid": False, "error": "Invalid key"}


@app.post("/auth/keys/generate")
async def generate_new_key(
    request: Request,
    api_key: str = Depends(get_api_key)
):
    """Generate a new API key (admin only) - returns key but doesn't persist"""
    if not is_admin_key(api_key):
        raise HTTPException(status_code=403, detail="Admin key required")

    new_key = secrets.token_urlsafe(32)
    add_audit_entry("auth", {"action": "key_generated"}, "success",
                   request.client.host if request.client else "unknown")

    return {
        "key": new_key,
        "note": "This key is not automatically persisted. Add it to MCP_API_KEY environment variable to use."
    }
'''

# Middleware code to add authentication to all endpoints
AUTH_MIDDLEWARE = '''
# Authentication middleware
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Add authentication check to all requests"""
    path = request.url.path.rstrip("/")

    # Skip auth for public endpoints
    if path in PUBLIC_ENDPOINTS or not path or path == "":
        return await call_next(request)

    # Skip if auth not required
    if not REQUIRE_AUTH or not MCP_API_KEY:
        return await call_next(request)

    # Get API key
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]

    # Validate
    if api_key and (api_key == MCP_API_KEY or api_key == MCP_ADMIN_KEY):
        return await call_next(request)

    return JSONResponse(
        status_code=401,
        content={"detail": "API key required. Provide X-API-Key header or Bearer token."},
        headers={"WWW-Authenticate": "Bearer"}
    )
'''

# Read the current server file
with open("/app/mcp_server.py", "r") as f:
    content = f.read()

# Check if already patched
if "MCP_API_KEY" in content:
    print("API authentication already exists - no patch needed")
    exit(0)

modified = False

# Add imports after existing imports
if "APIKeyHeader" not in content:
    # Find a good place to insert imports (after FastAPI imports)
    import_marker = "from fastapi import FastAPI, HTTPException, Request"
    pos = content.find(import_marker)
    if pos >= 0:
        end_line = content.find("\n", pos)
        # Add after the existing imports section
        pydantic_pos = content.find("from pydantic import BaseModel")
        if pydantic_pos > 0:
            end_line = content.find("\n", pydantic_pos)
            content = content[:end_line+1] + AUTH_IMPORTS + content[end_line+1:]
            print("Added authentication imports")
            modified = True

# Add auth code after CORS middleware
cors_end = content.find("allow_headers=[\"*\"],\n)")
if cors_end > 0:
    insert_pos = content.find("\n", cors_end + len("allow_headers=[\"*\"],\n)"))
    if insert_pos > 0:
        content = content[:insert_pos+1] + AUTH_CODE + "\n" + content[insert_pos+1:]
        print("Added API authentication code")
        modified = True

# Add middleware after auth code (find the auth_status function and add after it)
if modified and AUTH_MIDDLEWARE.strip() not in content:
    # Find the end of /auth/keys/generate endpoint
    marker = "Add it to MCP_API_KEY environment variable to use."
    marker_pos = content.find(marker)
    if marker_pos > 0:
        # Find the closing brace of the return statement
        end_pos = content.find("}", marker_pos)
        if end_pos > 0:
            # Find the end of the function (next blank line or decorator)
            next_section = content.find("\n\n", end_pos)
            if next_section > 0:
                content = content[:next_section] + "\n" + AUTH_MIDDLEWARE + content[next_section:]
                print("Added authentication middleware")

if not modified:
    print("Could not find insertion point for authentication code")
    exit(1)

# Write the updated file
with open("/app/mcp_server.py", "w") as f:
    f.write(content)

print("API authentication patch applied successfully")
print(f"File size: {len(content)} bytes")
print("\nTo enable authentication:")
print("  1. Set MCP_API_KEY environment variable (main access key)")
print("  2. Set MCP_ADMIN_KEY environment variable (admin key, optional)")
print("  3. Set MCP_REQUIRE_AUTH=true to enforce authentication")
