# realtime-diabolical-computer

Realtime Computer Using Agent(s)

## Computer Use Demo (port 8080)

This repo includes Anthropic's `computer-use-demo` (under `computer/`). The backend proxies the demo UI at `/computer/`, and the frontend embeds it.

If you want the OpenAI Realtime model to delegate “do something on the computer” tasks to Claude Opus, you also need:

- the computer-use-demo container running locally, and
- the FastAPI backend running locally (it exposes an HTTP endpoint that the Realtime function tool calls).

Start the demo container:

```bash
export ANTHROPIC_API_KEY="your-anthropic-key"
docker run \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -p 5900:5900 \
  -p 6080:6080 \
  -p 8501:8501 \
  -p 8080:8080 \
  -it ghcr.io/anthropics/anthropic-quickstarts:computer-use-demo-latest
```

## Frontend

A minimal Vite + React + TypeScript frontend for interacting with OpenAI's Realtime API with screen sharing capabilities.

### Features

- Connect to OpenAI Realtime API using ephemeral API keys
- Optional FastAPI backend to mint ephemeral keys automatically
- Screen sharing so the model can see your screen
- Voice and text interaction
- Live conversation transcript

### Setup

Start the backend (recommended):

```bash
cd backend
cp .env.example .env
# edit backend/.env and set OPENAI_API_KEY
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

If your local Node install is broken (or you prefer Bun), you can run:

```bash
cd frontend
bun install
bunx --bun vite
```

### Getting an Ephemeral API Key

You typically don't need to do this manually — the frontend fetches ephemeral keys from the FastAPI backend.

If you want to debug ephemeral key creation, you can mint one using:

```bash
export OPENAI_API_KEY="your-api-key"
./get-ephemeral-key.sh
```

Or manually via curl:

```bash
curl -X POST https://api.openai.com/v1/realtime/client_secrets \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "expires_after": { "anchor": "created_at", "seconds": 600 },
    "session": {
      "type": "realtime",
      "model": "gpt-realtime",
      "audio": { "output": { "voice": "verse" } }
    }
  }'
```

The script prints the ephemeral `value` (starts with `ek_...`). The demo UI mints keys via the backend, so you normally don't need to paste it anywhere.

### Usage

1. Start the computer-use-demo container (port 8080)
2. Start the backend and frontend dev servers
3. In the app, click "Connect"
4. (Optional) Click "Share Screen" to let the assistant see your screen
5. Speak or type to interact with the assistant

### Opus tool call (local function tool)

The UI registers a Realtime function tool named `opus_computer_task`. When the model calls it, your browser makes a local HTTP request to the backend:

- `POST /api/opus-computer/task`

This avoids the “hosted MCP must be publicly reachable” limitation and should work fully locally, as long as the backend + computer-use-demo container are running.
