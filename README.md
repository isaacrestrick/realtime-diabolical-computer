# realtime-diabolical-computer

Realtime Computer Using Agent(s)

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

1. Start the backend and frontend dev servers
2. In the app, click "Connect"
3. Click "Share Screen" to let the assistant see your screen
4. Speak or type to interact with the assistant
