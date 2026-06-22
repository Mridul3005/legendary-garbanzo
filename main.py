import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import Dict

app = FastAPI()

# Store connected users as { "username": websocket_object }
connected_users: Dict[str, WebSocket] = {}

@app.get("/")
async def get():
    with open("index.html", "r") as f:
        return HTMLResponse(f.read())

async def broadcast_user_list():
    """Sends the current list of online users to everyone."""
    user_list = list(connected_users.keys())
    message = json.dumps({"type": "user_list", "users": user_list})
    for ws in connected_users.values():
        await ws.send_text(message)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    username = None
    
    try:
        while True:
            # Wait for a message and parse it as JSON
            data = await websocket.receive_text()
            parsed_data = json.loads(data)

            # --- HANDLER: USER JOINS ---
            if parsed_data["type"] == "join":
                username = parsed_data["username"]
                
                # Prevent duplicate names
                original_name = username
                counter = 1
                while username in connected_users:
                    username = f"{original_name}{counter}"
                    counter += 1
                
                connected_users[username] = websocket
                await broadcast_user_list()
                
                # Announce to group
                system_msg = json.dumps({"type": "system", "text": f"{username} joined the chat."})
                for ws in connected_users.values():
                    await ws.send_text(system_msg)

            # --- HANDLER: CHAT MESSAGE ---
            elif parsed_data["type"] == "message":
                target = parsed_data.get("target", "Group")
                text = parsed_data["text"]
                
                msg_payload = json.dumps({
                    "type": "message",
                    "sender": username,
                    "target": target,
                    "text": text
                })

                if target == "Group":
                    # Broadcast to everyone
                    for ws in connected_users.values():
                        await ws.send_text(msg_payload)
                else:
                    # Private message: Send only to the target and the sender
                    if target in connected_users:
                        await connected_users[target].send_text(msg_payload)
                    await websocket.send_text(msg_payload)

    except WebSocketDisconnect:
        # --- HANDLER: USER DISCONNECTS ---
        if username and username in connected_users:
            del connected_users[username]
            await broadcast_user_list()
            system_msg = json.dumps({"type": "system", "text": f"{username} left."})
            for ws in connected_users.values():
                await ws.send_text(system_msg)
