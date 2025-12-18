from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
