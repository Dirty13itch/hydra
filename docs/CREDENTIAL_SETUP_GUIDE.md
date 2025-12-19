# Hydra External Credentials Setup Guide

This guide walks through setting up all external credentials needed for Phase 14 features.

## Overview

| Credential | Unlocks | Difficulty |
|------------|---------|------------|
| GOOGLE_CLIENT_ID/SECRET | Calendar, Gmail, Briefings | Medium |
| HA_TOKEN | Real-time Home Automation | Easy |
| MINIFLUX_API_KEY | News Intelligence | Easy |
| PLAID_CLIENT_ID/SECRET | Financial Awareness | Medium |

---

## 1. Google OAuth2 (Calendar + Gmail)

### Step 1: Create Google Cloud Project
```
1. Go to https://console.cloud.google.com
2. Create new project: "Hydra AI Assistant"
3. Enable these APIs:
   - Google Calendar API
   - Gmail API
```

### Step 2: Configure OAuth Consent Screen
```
1. Go to APIs & Services → OAuth consent screen
2. User Type: External
3. App name: "Hydra AI Assistant"
4. Support email: your email
5. Scopes: Add these:
   - https://www.googleapis.com/auth/calendar.readonly
   - https://www.googleapis.com/auth/gmail.readonly
   - https://www.googleapis.com/auth/gmail.send
6. Add your email as a test user
```

### Step 3: Create OAuth2 Credentials
```
1. Go to APIs & Services → Credentials
2. Create Credentials → OAuth 2.0 Client IDs
3. Application type: Web application
4. Name: "Hydra API"
5. Authorized redirect URIs:
   - http://192.168.1.244:8700/google/callback
   - http://localhost:8700/google/callback
6. Copy Client ID and Client Secret
```

### Step 4: Configure Hydra
```bash
# Add to /mnt/user/appdata/hydra-stack/.env.secrets
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# Restart the API
cd /mnt/user/appdata/hydra-stack && docker compose --env-file .env.secrets restart hydra-tools-api
```

### Step 5: Authorize
```
1. Visit http://192.168.1.244:8700/google/auth
2. Complete Google OAuth flow
3. Tokens will be stored automatically
```

---

## 2. Home Assistant Token

### Step 1: Generate Long-Lived Access Token
```
1. Open Home Assistant: http://192.168.1.244:8123
2. Click your user profile (bottom left)
3. Scroll to "Long-Lived Access Tokens"
4. Click "Create Token"
5. Name: "Hydra Caretaker"
6. Copy the token (only shown once!)
```

### Step 2: Configure Hydra
```bash
# Add to /mnt/user/appdata/hydra-stack/.env.secrets
HA_URL=http://192.168.1.244:8123
HA_TOKEN=your-long-lived-access-token

# Restart API
cd /mnt/user/appdata/hydra-stack && docker compose --env-file .env.secrets restart hydra-tools-api
```

### Step 3: Verify
```bash
curl -s http://192.168.1.244:8700/home/status | jq .
```

---

## 3. Miniflux API Key

### Step 1: Get API Key from Miniflux
```
1. Open Miniflux: http://192.168.1.244:8180
2. Log in (admin / HydraMiniflux2024!)
3. Go to Settings → API Keys
4. Create new API key: "Hydra News"
5. Copy the API key
```

### Step 2: Configure Hydra
```bash
# Add to /mnt/user/appdata/hydra-stack/.env.secrets
MINIFLUX_URL=http://192.168.1.244:8180
MINIFLUX_API_KEY=your-api-key

# Restart API
cd /mnt/user/appdata/hydra-stack && docker compose --env-file .env.secrets restart hydra-tools-api
```

### Step 3: Verify
```bash
curl -s http://192.168.1.244:8700/news/feeds | jq .
```

---

## 4. Plaid Financial API

### Step 1: Create Plaid Account
```
1. Go to https://dashboard.plaid.com
2. Sign up for a Developer account (free)
3. Request Sandbox access
```

### Step 2: Get API Keys
```
1. In Plaid Dashboard → Keys
2. Copy:
   - Client ID
   - Sandbox Secret (or Development Secret for production)
```

### Step 3: Configure Hydra
```bash
# Add to /mnt/user/appdata/hydra-stack/.env.secrets
PLAID_CLIENT_ID=your-client-id
PLAID_SECRET=your-secret
PLAID_ENV=sandbox  # Change to 'development' for real banks

# Restart API
cd /mnt/user/appdata/hydra-stack && docker compose --env-file .env.secrets restart hydra-tools-api
```

### Step 4: Link Bank Account
```
1. Visit http://192.168.1.244:8700/financial/link
2. Follow Plaid Link flow to connect your bank
3. Access tokens stored securely in database
```

---

## All-In-One Setup Script

Once you have all credentials, run this:

```bash
#!/bin/bash
# Run this on hydra-storage

# Add all credentials to .env.secrets
cat >> /mnt/user/appdata/hydra-stack/.env.secrets << 'EOF'

# Google OAuth2
GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET

# Home Assistant
HA_URL=http://192.168.1.244:8123
HA_TOKEN=YOUR_HA_TOKEN

# Miniflux News
MINIFLUX_URL=http://192.168.1.244:8180
MINIFLUX_API_KEY=YOUR_MINIFLUX_KEY

# Plaid Financial
PLAID_CLIENT_ID=YOUR_PLAID_CLIENT_ID
PLAID_SECRET=YOUR_PLAID_SECRET
PLAID_ENV=sandbox
EOF

# Restart the API
cd /mnt/user/appdata/hydra-stack && docker compose --env-file .env.secrets up -d hydra-tools-api
```

---

## Verification Commands

After setting up, verify each integration:

```bash
# Google Calendar (after OAuth)
curl -s http://192.168.1.244:8700/google/calendar/events | jq '.events[:3]'

# Gmail (after OAuth)
curl -s http://192.168.1.244:8700/gmail/unread | jq '.count'

# Home Assistant
curl -s http://192.168.1.244:8700/home/status | jq '.connected'

# Miniflux
curl -s http://192.168.1.244:8700/news/feeds | jq 'length'

# Plaid (after linking)
curl -s http://192.168.1.244:8700/financial/accounts | jq '.accounts[:2]'
```

---

## Credential Status Dashboard

Check all credential status at once:

```bash
curl -s http://192.168.1.244:8700/credentials/status | jq .
```

Or in Command Center: http://192.168.1.244:3210/settings

---

*Generated by Hydra Autonomous Caretaker*
*Last Updated: 2025-12-19*
