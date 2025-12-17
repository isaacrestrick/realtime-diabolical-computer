from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from websocket_handler import websocket_endpoint

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    """WebSocket endpoint for frontend communication."""
    await websocket_endpoint(websocket)
