import json
import logging
from typing import Dict, Set
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types for frontend-backend communication."""

    VOICE_START = "voice_start"
    VOICE_STOP = "voice_stop"
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    OUTPUT_STREAM = "output_stream"
    ERROR = "error"
    CONNECTION_ACK = "connection_ack"


class WebSocketMessage(BaseModel):
    """Base model for WebSocket messages."""

    type: MessageType
    payload: Dict = {}


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

        # Send connection acknowledgment
        await self.send_message(
            websocket,
            MessageType.CONNECTION_ACK,
            {"status": "connected", "message": "WebSocket connection established"}
        )

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection from the active set."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_message(self, websocket: WebSocket, message_type: MessageType, payload: Dict):
        """Send a JSON message to a specific WebSocket connection."""
        message = WebSocketMessage(type=message_type, payload=payload)
        try:
            await websocket.send_text(message.model_dump_json())
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            await self.disconnect(websocket)

    async def broadcast(self, message_type: MessageType, payload: Dict):
        """Broadcast a message to all active connections."""
        message = WebSocketMessage(type=message_type, payload=payload)
        message_json = message.model_dump_json()

        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            await self.disconnect(connection)


# Global connection manager instance
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint handler for frontend communication.

    Handles:
    - voice_start: Start voice recording/processing
    - voice_stop: Stop voice recording/processing
    - task_request: Request Claude Code to perform a task
    - task_response: Response from Claude Code task
    - output_stream: Stream output from Claude Code execution
    """
    await manager.connect(websocket)

    try:
        while True:
            # Receive and parse message
            data = await websocket.receive_text()

            try:
                message = WebSocketMessage.model_validate_json(data)
                logger.info(f"Received message: {message.type}")

                # Handle different message types
                await handle_message(websocket, message)

            except ValidationError as e:
                logger.error(f"Invalid message format: {e}")
                await manager.send_message(
                    websocket,
                    MessageType.ERROR,
                    {"error": "Invalid message format", "details": str(e)}
                )
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                await manager.send_message(
                    websocket,
                    MessageType.ERROR,
                    {"error": "Invalid JSON", "details": str(e)}
                )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client")
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


async def handle_message(websocket: WebSocket, message: WebSocketMessage):
    """
    Handle incoming WebSocket messages based on type.

    Args:
        websocket: The WebSocket connection
        message: Parsed WebSocket message
    """
    if message.type == MessageType.VOICE_START:
        await handle_voice_start(websocket, message.payload)

    elif message.type == MessageType.VOICE_STOP:
        await handle_voice_stop(websocket, message.payload)

    elif message.type == MessageType.TASK_REQUEST:
        await handle_task_request(websocket, message.payload)

    else:
        logger.warning(f"Unhandled message type: {message.type}")
        await manager.send_message(
            websocket,
            MessageType.ERROR,
            {"error": "Unhandled message type", "type": message.type}
        )


async def handle_voice_start(websocket: WebSocket, payload: Dict):
    """
    Handle voice_start message.

    Payload expected:
        - audio_config: Optional audio configuration
    """
    logger.info("Voice recording started")
    # TODO: Initialize voice processing
    await manager.send_message(
        websocket,
        MessageType.VOICE_START,
        {"status": "started", "message": "Voice recording started"}
    )


async def handle_voice_stop(websocket: WebSocket, payload: Dict):
    """
    Handle voice_stop message.

    Payload expected:
        - No specific payload required
    """
    logger.info("Voice recording stopped")
    # TODO: Stop voice processing
    await manager.send_message(
        websocket,
        MessageType.VOICE_STOP,
        {"status": "stopped", "message": "Voice recording stopped"}
    )


async def handle_task_request(websocket: WebSocket, payload: Dict):
    """
    Handle task_request message.

    Payload expected:
        - task: Description of the coding task
        - context: Optional additional context
    """
    task = payload.get("task", "")
    context = payload.get("context", {})

    logger.info(f"Task request received: {task}")

    # TODO: Process task with Claude Code
    # For now, send a mock response
    await manager.send_message(
        websocket,
        MessageType.TASK_RESPONSE,
        {
            "status": "received",
            "task": task,
            "message": "Task received and queued for processing"
        }
    )
