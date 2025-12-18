from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import Response

from opus_computer import run_opus_task_in_container

_BASE_DIR = Path(__file__).resolve().parent
load_dotenv(_BASE_DIR / ".env")


def _get_openai_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Create backend/.env (see backend/.env.example)."
        )
    return api_key


class EphemeralKeyRequest(BaseModel):
    model: str = Field(default="gpt-realtime")
    voice: str = Field(default="verse")
    expires_after_seconds: int = Field(default=600, ge=10, le=3600)
    expires_after_anchor: str = Field(default="created_at")


class EphemeralKeyResponse(BaseModel):
    apiKey: str
    expires_at: int | None = None
    session: dict[str, Any] | None = None


class OpusComputerTaskRequest(BaseModel):
    task: str = Field(min_length=1)
    timeout_seconds: int = Field(default=600, ge=10, le=1800)
    container: str | None = None
    model: str | None = None
    tool_version: str | None = None


class OpusComputerTaskResponse(BaseModel):
    output: str


app = FastAPI(title="Realtime Ephemeral Key Backend")

_cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


def _computer_demo_origin() -> str:
    return os.getenv("COMPUTER_DEMO_ORIGIN", "http://localhost:8080").rstrip("/")


@app.api_route("/computer", methods=["GET", "HEAD"])
@app.api_route("/computer/{path:path}", methods=["GET", "HEAD"])
async def proxy_computer_demo(request: Request, path: str = "") -> Response:
    """
    Best-effort reverse proxy to the computer-use-demo UI (usually running on port 8080).

    This is intentionally minimal (GET/HEAD only) and is meant for local dev and demos.
    """
    upstream = _computer_demo_origin()
    upstream_url = f"{upstream}/{path.lstrip('/')}"

    # Forward a minimal set of headers.
    forward_headers: dict[str, str] = {}
    accept = request.headers.get("accept")
    if accept:
        forward_headers["accept"] = accept
    user_agent = request.headers.get("user-agent")
    if user_agent:
        forward_headers["user-agent"] = user_agent

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        upstream_resp = await client.request(
            method=request.method,
            url=upstream_url,
            params=dict(request.query_params),
            headers=forward_headers,
        )

    # Copy response headers, excluding hop-by-hop headers.
    hop_by_hop = {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
    headers = {
        k: v
        for k, v in upstream_resp.headers.items()
        if k.lower() not in hop_by_hop
    }

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=headers,
        media_type=upstream_resp.headers.get("content-type"),
    )


@app.post("/api/opus-computer/task", response_model=OpusComputerTaskResponse)
async def opus_computer_task(body: OpusComputerTaskRequest) -> OpusComputerTaskResponse:
    try:
        output = await run_opus_task_in_container(
            body.task,
            timeout_seconds=body.timeout_seconds,
            container=body.container,
            model=body.model,
            tool_version=body.tool_version,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail={"message": "Opus task timed out"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"message": str(e)})

    return OpusComputerTaskResponse(output=output)


@app.post("/api/realtime/ephemeral-key", response_model=EphemeralKeyResponse)
async def create_ephemeral_key(body: EphemeralKeyRequest) -> EphemeralKeyResponse:
    api_key = _get_openai_api_key()

    payload = {
        "expires_after": {
            "anchor": body.expires_after_anchor,
            "seconds": body.expires_after_seconds,
        },
        "session": {
            "type": "realtime",
            "model": body.model,
            "audio": {"output": {"voice": body.voice}},
        },
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.openai.com/v1/realtime/client_secrets",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if response.status_code >= 400:
        try:
            detail: Any = response.json()
        except Exception:
            detail = {"message": response.text}
        raise HTTPException(status_code=response.status_code, detail=detail)

    data = response.json()
    value = data.get("value")
    if not value:
        raise HTTPException(
            status_code=500,
            detail={"message": "OpenAI response missing `value`", "raw": data},
        )

    return EphemeralKeyResponse(
        apiKey=value,
        expires_at=data.get("expires_at"),
        session=data.get("session"),
    )
