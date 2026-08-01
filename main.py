import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import Dict

app = FastAPI()

connected_users: Dict[str, WebSocket] = {}

@app.get("/")
async def get():
    with open("index.html", "r") as f:
        return HTMLResponse(f.read())

async def broadcast_user_list():
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
            data = await websocket.receive_text()
            parsed_data = json.loads(data)

            msg_type = parsed_data.get("type")

            if msg_type == "join":
                username = parsed_data["username"]
                original_name = username
                counter = 1
                while username in connected_users:
                    username = f"{original_name}{counter}"
                    counter += 1
                
                connected_users[username] = websocket
                await broadcast_user_list()
                
                system_msg = json.dumps({"type": "system", "text": f"{username} joined."})
                for ws in connected_users.values():
                    await ws.send_text(system_msg)

            elif msg_type == "message":
                target = parsed_data.get("target", "Group")
                text = parsed_data["text"]
                
                msg_payload = json.dumps({
                    "type": "message",
                    "sender": username,
                    "target": target,
                    "text": text
                })

                if target == "Group":
                    for ws in connected_users.values():
                        await ws.send_text(msg_payload)
                else:
                    if target in connected_users:
                        await connected_users[target].send_text(msg_payload)
                    
                    # Send copy back to sender
                    await websocket.send_text(msg_payload)

            elif msg_type == "typing":
                target = parsed_data.get("target", "Group")
                is_typing = parsed_data.get("isTyping", False)

                typing_payload = json.dumps({
                    "type": "typing",
                    "sender": username,
                    "target": target,
                    "isTyping": is_typing
                })

                if target == "Group":
                    # Broadcast typing status to everyone except the sender
                    for user, ws in connected_users.items():
                        if user != username:
                            await ws.send_text(typing_payload)
                else:
                    # Forward typing status directly to target user
                    if target in connected_users:
                        await connected_users[target].send_text(typing_payload)

    except WebSocketDisconnect:
        if username and username in connected_users:
            del connected_users[username]
            await broadcast_user_list()
            system_msg = json.dumps({"type": "system", "text": f"{username} left."})
            for ws in connected_users.values():
                await ws.send_text(system_msg)
