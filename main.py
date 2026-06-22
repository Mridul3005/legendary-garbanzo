from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()

# Store active connections
active_connections = []

# Serve the frontend
@app.get("/")
async def get():
    with open("index.html", "r") as f:
        return HTMLResponse(f.read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Broadcast message to everyone
            for connection in active_connections:
                await connection.send_text(data)
    except:
        active_connections.remove(websocket)
