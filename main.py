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

            if parsed_data["type"] == "join":
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
                
                #print(f"✅ SERVER LOG: {username} connected. Total users: {len(connected_users)}")

            elif parsed_data["type"] == "message":
                target = parsed_data.get("target", "Group")
                text = parsed_data["text"]
                
                #print(f"📩 SERVER LOG: Received message from [{username}] intended for [{target}]")
                
                msg_payload = json.dumps({
                    "type": "message",
                    "sender": username,
                    "target": target,
                    "text": text
                })

                if target == "Group":
                    #print("📢 SERVER LOG: Broadcasting to everyone.")
                    for ws in connected_users.values():
                        await ws.send_text(msg_payload)
                else:
                    #print(f"🔒 SERVER LOG: Attempting private route to {target}.")
                    if target in connected_users:
                        await connected_users[target].send_text(msg_payload)
                        #print(f"     -> Successfully delivered to {target}.")
                    else:
                        pass
                        #print(f"     -> ERROR: {target} is not in the active users list!")
                    
                    # Send copy back to sender
                    await websocket.send_text(msg_payload)

    except WebSocketDisconnect:
        if username and username in connected_users:
            del connected_users[username]
            await broadcast_user_list()
            system_msg = json.dumps({"type": "system", "text": f"{username} left."})
            for ws in connected_users.values():
                await ws.send_text(system_msg)
            #print(f"❌ SERVER LOG: {username} disconnected.")
