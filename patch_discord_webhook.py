#!/usr/bin/env python3
"""Patch script to add Discord webhook support to MCP server.

This adds a /webhooks/discord endpoint that receives Alertmanager alerts
and forwards them to Discord with proper formatting.
"""

import re

# Discord webhook endpoint code
DISCORD_WEBHOOK_CODE = '''
# =============================================================================
# Discord Webhook (for Alertmanager alerts)
# =============================================================================

# Discord webhook URL - configure via environment variable
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

@app.post("/webhooks/discord")
async def discord_webhook(payload: AlertmanagerPayload, request: Request):
    """Forward Alertmanager alerts to Discord"""
    ip = request.client.host if request and request.client else "unknown"

    if not DISCORD_WEBHOOK_URL:
        add_audit_entry("discord_webhook", {"error": "DISCORD_WEBHOOK_URL not configured"}, "error", "webhooks")
        return {"status": "error", "message": "Discord webhook URL not configured"}

    # Build Discord embeds from alerts
    embeds = []
    for alert in payload.alerts or []:
        alert_status = alert.get("status", "unknown")
        alertname = alert.get("labels", {}).get("alertname", "Unknown Alert")
        severity = alert.get("labels", {}).get("severity", "info")
        instance = alert.get("labels", {}).get("instance", "unknown")
        description = alert.get("annotations", {}).get("description",
                      alert.get("annotations", {}).get("summary", "No description"))

        # Color based on status/severity
        if alert_status == "resolved":
            color = 0x00FF00  # Green
            title = f"✅ RESOLVED: {alertname}"
        elif severity == "critical":
            color = 0xFF0000  # Red
            title = f"🚨 CRITICAL: {alertname}"
        elif severity == "warning":
            color = 0xFFA500  # Orange
            title = f"⚠️ WARNING: {alertname}"
        else:
            color = 0x0000FF  # Blue
            title = f"ℹ️ INFO: {alertname}"

        embed = {
            "title": title,
            "description": description,
            "color": color,
            "fields": [
                {"name": "Instance", "value": instance, "inline": True},
                {"name": "Severity", "value": severity.upper(), "inline": True},
                {"name": "Status", "value": alert_status.upper(), "inline": True},
            ],
            "footer": {"text": "Hydra Alertmanager"},
            "timestamp": alert.get("startsAt", "")
        }
        embeds.append(embed)

    # Send to Discord (max 10 embeds per message)
    try:
        for i in range(0, len(embeds), 10):
            batch = embeds[i:i+10]
            discord_payload = {
                "username": "Hydra Alerts",
                "avatar_url": "https://raw.githubusercontent.com/prometheus/prometheus/main/web/ui/react-app/public/favicon.ico",
                "embeds": batch
            }

            r = await client.post(DISCORD_WEBHOOK_URL, json=discord_payload)
            if r.status_code not in (200, 204):
                add_audit_entry("discord_webhook", {"error": f"Discord returned {r.status_code}"}, "error", "webhooks")
                return {"status": "error", "message": f"Discord returned {r.status_code}"}

        add_audit_entry("discord_webhook", {"alerts_sent": len(embeds)}, "success", "webhooks")
        return {"status": "success", "alerts_forwarded": len(embeds)}

    except Exception as e:
        add_audit_entry("discord_webhook", {"error": str(e)}, "error", "webhooks")
        return {"status": "error", "message": str(e)}
'''

# Read the current server file
with open("/app/mcp_server.py", "r") as f:
    content = f.read()

# Check if already patched
if "/webhooks/discord" in content:
    print("Discord webhook endpoint already exists - no patch needed")
    exit(0)

# Find a good insertion point - after the alertmanager webhook
alertmanager_pattern = r'(@app\.post\("/webhooks/alertmanager"\).*?return \{[^}]+\})'
match = re.search(alertmanager_pattern, content, re.DOTALL)

if match:
    # Insert after alertmanager webhook
    insert_pos = match.end()
    content = content[:insert_pos] + "\n\n" + DISCORD_WEBHOOK_CODE + "\n" + content[insert_pos:]
    print("Inserted Discord webhook after alertmanager webhook")
else:
    # Try to insert before WebSocket section or main
    insert_markers = [
        "# =============================================================================\n# WebSocket",
        'if __name__ == "__main__":'
    ]

    inserted = False
    for marker in insert_markers:
        pos = content.find(marker)
        if pos > 0:
            content = content[:pos] + DISCORD_WEBHOOK_CODE + "\n\n" + content[pos:]
            print(f"Inserted Discord webhook before: {marker[:40]}...")
            inserted = True
            break

    if not inserted:
        print("Could not find insertion point for Discord webhook")
        exit(1)

# Write the updated file
with open("/app/mcp_server.py", "w") as f:
    f.write(content)

print("Discord webhook patch applied successfully")
print(f"File size: {len(content)} bytes")
