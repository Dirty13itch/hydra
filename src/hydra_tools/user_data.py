"""
User Data Management for Hydra

Provides endpoints for:
- User profile management
- Credential status (not values - just configured/valid status)
- API key setting/testing
- Feature dependency tracking

Author: Hydra Autonomous System
Phase: 14 - User Data Management
Created: 2025-12-18
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

DATA_DIR = Path(os.getenv("HYDRA_DATA_DIR", "/data"))
PROFILE_FILE = DATA_DIR / "user_profile.json"
CREDENTIALS_FILE = DATA_DIR / "credentials_status.json"

# Service URLs for testing
TABBYAPI_URL = os.getenv("TABBYAPI_URL", "http://192.168.1.250:5000")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.1.203:11434")
HA_URL = os.getenv("HA_URL", "http://192.168.1.244:8123")
MINIFLUX_URL = os.getenv("MINIFLUX_URL", "http://192.168.1.244:8180")

# API keys file
API_KEYS_FILE = DATA_DIR / "api_keys.json"


def load_saved_credentials() -> None:
    """Load saved API keys from file into environment variables."""
    if not API_KEYS_FILE.exists():
        logger.info("No saved API keys file found")
        return

    try:
        creds = json.loads(API_KEYS_FILE.read_text())
        env_var_map = {
            "home_assistant": "HA_TOKEN",
            "miniflux": "MINIFLUX_API_KEY",
            "discord": "DISCORD_WEBHOOK_URL",
            "weather": "WEATHER_API_KEY",
        }

        loaded_count = 0
        for service, data in creds.items():
            env_var = env_var_map.get(service)
            if env_var and data.get("api_key"):
                os.environ[env_var] = data["api_key"]
                loaded_count += 1
                logger.info(f"Loaded saved credential for {service}")

        logger.info(f"Loaded {loaded_count} saved credentials from file")
    except Exception as e:
        logger.error(f"Failed to load saved credentials: {e}")


# Load saved credentials on module import
load_saved_credentials()


# =============================================================================
# Data Models
# =============================================================================

class UserPreferences(BaseModel):
    notifications: Dict[str, Any] = {
        "enabled": True,
        "types": ["alerts", "briefings", "research"],
    }
    dashboard: Dict[str, Any] = {
        "defaultView": "MISSION",
        "refreshInterval": 30,
    }
    ai: Dict[str, Any] = {
        "preferredModel": "auto",
        "temperature": 0.7,
        "maxTokens": 4096,
    }


class UserProfile(BaseModel):
    userId: str = "default"
    displayName: str = "Hydra User"
    timezone: str = "America/Chicago"
    theme: str = "dark"
    preferences: UserPreferences = UserPreferences()
    contacts: List[Dict[str, Any]] = []
    locations: List[Dict[str, Any]] = []
    schedules: List[Dict[str, Any]] = []
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class ServiceCredentialStatus(BaseModel):
    configured: bool = False
    valid: Optional[bool] = None
    lastValidated: Optional[str] = None
    type: str = "api_key"  # oauth, api_key, account
    featuresUnlocked: List[str] = []
    error: Optional[str] = None


class CredentialStatusResponse(BaseModel):
    services: Dict[str, ServiceCredentialStatus]
    summary: Dict[str, Any]


class ApiKeyRequest(BaseModel):
    api_key: str


class ProfileUpdateRequest(BaseModel):
    displayName: Optional[str] = None
    timezone: Optional[str] = None
    theme: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


# =============================================================================
# Service Definitions
# =============================================================================

SERVICE_DEFINITIONS = {
    "google": {
        "name": "Google",
        "type": "oauth",
        "features": ["calendar", "email"],
        "env_vars": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
    },
    "home_assistant": {
        "name": "Home Assistant",
        "type": "api_key",
        "features": ["home_automation", "presence"],
        "env_vars": ["HA_TOKEN"],
    },
    "miniflux": {
        "name": "Miniflux",
        "type": "api_key",
        "features": ["news"],
        "env_vars": ["MINIFLUX_API_KEY"],
    },
    "discord": {
        "name": "Discord",
        "type": "api_key",
        "features": ["discord_alerts"],
        "env_vars": ["DISCORD_WEBHOOK_URL"],
    },
    "weather": {
        "name": "Weather",
        "type": "api_key",
        "features": ["weather"],
        "env_vars": ["WEATHER_API_KEY"],
    },
}


# =============================================================================
# Helper Functions
# =============================================================================

def load_profile() -> UserProfile:
    """Load user profile from file."""
    if PROFILE_FILE.exists():
        try:
            data = json.loads(PROFILE_FILE.read_text())
            return UserProfile(**data)
        except Exception as e:
            logger.error(f"Failed to load profile: {e}")
    return UserProfile(createdAt=datetime.utcnow().isoformat())


def save_profile(profile: UserProfile) -> None:
    """Save user profile to file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    profile.updatedAt = datetime.utcnow().isoformat()
    PROFILE_FILE.write_text(json.dumps(profile.model_dump(), indent=2))


async def check_google_status() -> ServiceCredentialStatus:
    """Check Google OAuth status."""
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    token_file = DATA_DIR / "google_tokens.json"

    configured = bool(client_id and client_secret)
    valid = None

    if configured and token_file.exists():
        try:
            tokens = json.loads(token_file.read_text())
            # Check if we have an access token
            valid = bool(tokens.get("access_token"))
        except Exception:
            valid = False

    return ServiceCredentialStatus(
        configured=configured,
        valid=valid,
        type="oauth",
        featuresUnlocked=["calendar", "email"] if valid else [],
    )


async def check_home_assistant_status() -> ServiceCredentialStatus:
    """Check Home Assistant status."""
    ha_token = os.getenv("HA_TOKEN", "")
    configured = bool(ha_token)
    valid = None
    error = None

    if configured:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{HA_URL}/api/",
                    headers={"Authorization": f"Bearer {ha_token}"}
                )
                valid = response.status_code == 200
                if not valid:
                    error = f"HTTP {response.status_code}"
        except httpx.TimeoutException:
            valid = False
            error = "Connection timeout"
        except Exception as e:
            valid = False
            error = str(e)

    return ServiceCredentialStatus(
        configured=configured,
        valid=valid,
        type="api_key",
        featuresUnlocked=["home_automation", "presence"] if valid else [],
        error=error,
    )


async def check_miniflux_status() -> ServiceCredentialStatus:
    """Check Miniflux status."""
    api_key = os.getenv("MINIFLUX_API_KEY", "")
    username = os.getenv("MINIFLUX_USERNAME", "")
    password = os.getenv("MINIFLUX_PASSWORD", "")

    configured = bool(api_key) or bool(username and password)
    valid = None
    error = None

    if configured:
        try:
            headers = {}
            auth = None
            if api_key:
                headers["X-Auth-Token"] = api_key
            elif username and password:
                auth = (username, password)

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{MINIFLUX_URL}/v1/me",
                    headers=headers,
                    auth=auth
                )
                valid = response.status_code == 200
                if not valid:
                    error = f"HTTP {response.status_code}"
        except httpx.TimeoutException:
            valid = False
            error = "Connection timeout"
        except Exception as e:
            valid = False
            error = str(e)

    return ServiceCredentialStatus(
        configured=configured,
        valid=valid,
        type="api_key",
        featuresUnlocked=["news"] if valid else [],
        error=error,
    )


async def check_discord_status() -> ServiceCredentialStatus:
    """Check Discord webhook status."""
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
    configured = bool(webhook_url)

    # Don't test webhook to avoid spam - just check if configured
    return ServiceCredentialStatus(
        configured=configured,
        valid=True if configured else None,
        type="api_key",
        featuresUnlocked=["discord_alerts"] if configured else [],
    )


async def check_weather_status() -> ServiceCredentialStatus:
    """Check Weather API status."""
    api_key = os.getenv("WEATHER_API_KEY", "")
    configured = bool(api_key)

    return ServiceCredentialStatus(
        configured=configured,
        valid=None,  # Don't auto-test to avoid API calls
        type="api_key",
        featuresUnlocked=["weather"] if configured else [],
    )


# =============================================================================
# Router
# =============================================================================

def create_user_data_router() -> APIRouter:
    """Create the user data router."""
    router = APIRouter(tags=["user-data"])

    # -------------------------------------------------------------------------
    # Profile Endpoints
    # -------------------------------------------------------------------------

    @router.get("/user-data/profile", response_model=UserProfile)
    async def get_profile():
        """Get user profile."""
        return load_profile()

    @router.put("/user-data/profile", response_model=UserProfile)
    async def update_profile_full(profile: UserProfile):
        """Replace entire profile."""
        save_profile(profile)
        return profile

    @router.patch("/user-data/profile", response_model=UserProfile)
    async def update_profile_partial(updates: ProfileUpdateRequest):
        """Partially update profile."""
        profile = load_profile()

        if updates.displayName is not None:
            profile.displayName = updates.displayName
        if updates.timezone is not None:
            profile.timezone = updates.timezone
        if updates.theme is not None:
            profile.theme = updates.theme
        if updates.preferences is not None:
            # Merge preferences
            prefs = profile.preferences.model_dump()
            prefs.update(updates.preferences)
            profile.preferences = UserPreferences(**prefs)

        save_profile(profile)
        return profile

    # -------------------------------------------------------------------------
    # Credential Status Endpoints
    # -------------------------------------------------------------------------

    @router.get("/credentials/status", response_model=CredentialStatusResponse)
    async def get_credential_status():
        """Get status of all credentials (never returns actual values)."""
        services = {}

        # Check each service
        services["google"] = await check_google_status()
        services["home_assistant"] = await check_home_assistant_status()
        services["miniflux"] = await check_miniflux_status()
        services["discord"] = await check_discord_status()
        services["weather"] = await check_weather_status()

        # Calculate summary
        total = len(services)
        configured = sum(1 for s in services.values() if s.configured)
        valid = sum(1 for s in services.values() if s.valid)

        features_enabled = []
        features_disabled = []
        for svc in services.values():
            features_enabled.extend(svc.featuresUnlocked)

        all_features = ["calendar", "email", "home_automation", "presence", "news", "discord_alerts", "weather"]
        features_disabled = [f for f in all_features if f not in features_enabled]

        return CredentialStatusResponse(
            services={k: v.model_dump() for k, v in services.items()},
            summary={
                "configured": configured,
                "total": total,
                "valid": valid,
                "featuresEnabled": features_enabled,
                "featuresDisabled": features_disabled,
            }
        )

    @router.get("/credentials/status/{service}")
    async def get_service_status(service: str):
        """Get status of a specific service."""
        if service not in SERVICE_DEFINITIONS:
            raise HTTPException(status_code=404, detail=f"Unknown service: {service}")

        if service == "google":
            return await check_google_status()
        elif service == "home_assistant":
            return await check_home_assistant_status()
        elif service == "miniflux":
            return await check_miniflux_status()
        elif service == "discord":
            return await check_discord_status()
        elif service == "weather":
            return await check_weather_status()

        raise HTTPException(status_code=404, detail=f"Service not implemented: {service}")

    @router.post("/credentials/test/{service}")
    async def test_credential(service: str):
        """Test if a credential is working."""
        if service not in SERVICE_DEFINITIONS:
            raise HTTPException(status_code=404, detail=f"Unknown service: {service}")

        if service == "google":
            status = await check_google_status()
        elif service == "home_assistant":
            status = await check_home_assistant_status()
        elif service == "miniflux":
            status = await check_miniflux_status()
        elif service == "discord":
            status = await check_discord_status()
        elif service == "weather":
            status = await check_weather_status()
        else:
            raise HTTPException(status_code=404, detail=f"Service not implemented: {service}")

        # Update lastValidated
        status.lastValidated = datetime.utcnow().isoformat()

        return {
            "valid": status.valid,
            "message": "Connection successful" if status.valid else (status.error or "Connection failed"),
            "service": service,
        }

    @router.post("/credentials/api-key/{service}")
    async def set_api_key(service: str, request: ApiKeyRequest):
        """
        Set an API key for a service.

        Note: In production, this should write to an encrypted vault.
        For now, we store in environment and a status file.
        """
        if service not in SERVICE_DEFINITIONS:
            raise HTTPException(status_code=404, detail=f"Unknown service: {service}")

        svc_def = SERVICE_DEFINITIONS[service]
        if svc_def["type"] == "oauth":
            raise HTTPException(
                status_code=400,
                detail=f"{service} uses OAuth, not API keys. Use the OAuth flow instead."
            )

        # Store the key in a credentials file (in production, use encrypted vault)
        creds_file = DATA_DIR / "api_keys.json"
        creds = {}
        if creds_file.exists():
            try:
                creds = json.loads(creds_file.read_text())
            except Exception:
                pass

        creds[service] = {
            "api_key": request.api_key,
            "set_at": datetime.utcnow().isoformat(),
        }

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        creds_file.write_text(json.dumps(creds, indent=2))

        # Also set as environment variable for this process
        env_var = svc_def["env_vars"][0] if svc_def["env_vars"] else None
        if env_var:
            os.environ[env_var] = request.api_key

        return {
            "success": True,
            "message": f"API key saved for {service}",
            "service": service,
        }

    @router.delete("/credentials/api-key/{service}")
    async def remove_api_key(service: str):
        """Remove an API key for a service."""
        if service not in SERVICE_DEFINITIONS:
            raise HTTPException(status_code=404, detail=f"Unknown service: {service}")

        creds_file = DATA_DIR / "api_keys.json"
        if creds_file.exists():
            try:
                creds = json.loads(creds_file.read_text())
                if service in creds:
                    del creds[service]
                    creds_file.write_text(json.dumps(creds, indent=2))
            except Exception:
                pass

        # Clear environment variable
        svc_def = SERVICE_DEFINITIONS[service]
        env_var = svc_def["env_vars"][0] if svc_def["env_vars"] else None
        if env_var and env_var in os.environ:
            del os.environ[env_var]

        return {
            "success": True,
            "message": f"Credentials removed for {service}",
            "service": service,
        }

    @router.get("/credentials/features")
    async def get_feature_dependencies():
        """Get the mapping of features to required credentials."""
        return {
            "features": {
                "calendar": {"requires": ["google"], "description": "Calendar events and scheduling"},
                "email": {"requires": ["google"], "description": "Email summaries and priority contacts"},
                "home_automation": {"requires": ["home_assistant"], "description": "Smart home device control"},
                "presence": {"requires": ["home_assistant"], "description": "Location-based automation"},
                "news": {"requires": ["miniflux"], "description": "News and RSS monitoring"},
                "discord_alerts": {"requires": ["discord"], "description": "Discord notifications"},
                "weather": {"requires": ["weather"], "description": "Weather forecasts"},
                "voice": {"requires": [], "description": "Voice synthesis (local)"},
                "inference": {"requires": [], "description": "LLM inference (internal)"},
                "image_generation": {"requires": [], "description": "Image generation (internal)"},
            }
        }

    @router.post("/credentials/reload")
    async def reload_credentials():
        """Reload credentials from saved file into environment."""
        load_saved_credentials()
        return {
            "success": True,
            "message": "Credentials reloaded from file",
        }

    return router
