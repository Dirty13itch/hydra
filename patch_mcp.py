import re

# Read the file
with open("C:/Users/shaun/projects/hydra/mcp_server_original.py", "r") as f:
    content = f.read()

# 1. Update imports - add WebSocket
old_import = "from fastapi import FastAPI, HTTPException, Request"
new_import = "from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect"
content = content.replace(old_import, new_import)

# 2. Add WebSocket manager class after "from collections import defaultdict"
ws_manager_code = '''
# =============================================================================
# WebSocket Support for Real-Time Updates
# =============================================================================

class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    @property
    def client_count(self):
        return len(self.active_connections)

ws_manager = ConnectionManager()

# Background task state
ws_broadcast_task = None
'''

# Find the right place to insert (after defaultdict import)
insert_after = "from collections import defaultdict"
content = content.replace(insert_after, insert_after + "\n" + ws_manager_code)

# 3. Add WebSocket endpoint before the "if __name__" block
ws_endpoint_code = '''
# =============================================================================
# WebSocket Endpoint for Real-Time Updates
# =============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates"""
    await ws_manager.connect(websocket)
    add_audit_entry("websocket_connect", {"total_clients": ws_manager.client_count}, "success", "websocket")

    try:
        while True:
            # Keep connection alive and handle incoming messages
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                # Handle ping/pong
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
                # Handle subscription requests
                elif data.get("type") == "subscribe":
                    await websocket.send_json({
                        "type": "subscribed",
                        "timestamp": datetime.now().isoformat(),
                        "data": {"message": "Subscribed to real-time updates"}
                    })
            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_json({"type": "keepalive", "timestamp": datetime.now().isoformat()})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        ws_manager.disconnect(websocket)
        add_audit_entry("websocket_disconnect", {"total_clients": ws_manager.client_count}, "success", "websocket")


async def broadcast_metrics():
    """Background task to broadcast metrics to all WebSocket clients"""
    while True:
        try:
            if ws_manager.client_count > 0:
                # Gather metrics data
                metrics_data = {}

                # Get GPU metrics
                try:
                    r = await client.get(f"{PROMETHEUS_URL}/api/v1/query",
                                        params={"query": "nvidia_gpu_utilization"})
                    if r.status_code == 200:
                        gpus = []
                        for item in r.json().get("data", {}).get("result", []):
                            gpu = {
                                "index": item.get("metric", {}).get("gpu", ""),
                                "name": item.get("metric", {}).get("name", ""),
                                "node": item.get("metric", {}).get("instance", "").split(":")[0],
                                "utilization": safe_float(item.get("value", [0, 0])[1])
                            }
                            gpus.append(gpu)
                        metrics_data["gpus"] = gpus
                except:
                    pass

                # Get recent alerts count
                metrics_data["alert_count"] = len([a for a in recent_alerts if a.get("status") == "firing"])

                # Broadcast to all clients
                await ws_manager.broadcast({
                    "type": "update",
                    "timestamp": datetime.now().isoformat(),
                    "data": metrics_data
                })

            await asyncio.sleep(5)  # Broadcast every 5 seconds
        except Exception as e:
            print(f"Broadcast error: {e}")
            await asyncio.sleep(5)


@app.on_event("startup")
async def start_websocket_broadcast():
    """Start the WebSocket broadcast background task"""
    global ws_broadcast_task
    ws_broadcast_task = asyncio.create_task(broadcast_metrics())


@app.on_event("shutdown")
async def stop_websocket_broadcast():
    """Stop the WebSocket broadcast background task"""
    global ws_broadcast_task
    if ws_broadcast_task:
        ws_broadcast_task.cancel()
        try:
            await ws_broadcast_task
        except asyncio.CancelledError:
            pass


@app.get("/ws/status")
async def websocket_status():
    """Get WebSocket connection status"""
    return {
        "connected_clients": ws_manager.client_count,
        "broadcast_active": ws_broadcast_task is not None and not ws_broadcast_task.done()
    }

'''

# Find the main block and insert before it
content = content.replace(
    'if __name__ == "__main__":',
    ws_endpoint_code + '\nif __name__ == "__main__":'
)

# Write the modified file
with open("C:/Users/shaun/projects/hydra/mcp_server_websocket.py", "w") as f:
    f.write(content)

print("WebSocket support added successfully!")
print(f"File size: {len(content)} bytes")
