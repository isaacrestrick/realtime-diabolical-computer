# Voice-Controlled Claude Code Assistant

## Concept
A voice-first desktop application where users speak naturally to an OpenAI Realtime Agent, which orchestrates Claude Code to perform coding tasks on their machine.

## Research Summary

### OpenAI Realtime Agents
- Voice-enabled AI with sub-second latency (~200-300ms) using `gpt-realtime` model
- Supports WebRTC (browser), WebSocket (server), and SIP (telephony)
- Function calling, interruption handling, and streaming audio I/O
- Agents SDK available for TypeScript and Python

### Claude Computer Use
- Claude can view screens, move cursor, click, type via screenshot analysis
- Tools: `computer_20250124`, `text_editor_20250124`, `bash_20250124`
- Runs in sandboxed environments (Docker containers/VMs)
- Works with Claude Sonnet 4.5, Opus 4.5, etc.

### Browser Base
- Cloud headless browser infrastructure for AI agents
- Stagehand framework for AI-powered browser automation
- MCP server integration for LLM control
- Scales to thousands of concurrent browsers

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Electron Frontend                         │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ Voice UI    │  │ Code Viewer  │  │ Terminal Output    │  │
│  │ (WebRTC)    │  │ (Monaco)     │  │                    │  │
│  └─────────────┘  └──────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌─────────────────────┐  ┌──────────────────────────────┐  │
│  │ OpenAI Realtime     │  │ Claude Code Orchestrator     │  │
│  │ Agent (Voice)       │──│ (subprocess management)      │  │
│  │ - Speech-to-speech  │  │ - Executes code tasks        │  │
│  │ - Function calling  │  │ - Returns results            │  │
│  └─────────────────────┘  └──────────────────────────────┘  │
│                                     │                        │
│  ┌──────────────────────────────────┼──────────────────────┐│
│  │ Optional: Browser Base           │                      ││
│  │ - Web testing                    ▼                      ││
│  │ - Research tasks        ┌───────────────┐               ││
│  └─────────────────────────│ Claude Code   │───────────────┘│
│                            │ CLI Process   │                 │
│                            └───────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Electron Frontend
- WebRTC connection to OpenAI Realtime API for voice
- Monaco editor for code display
- Terminal emulator for output
- Visual feedback (waveforms, status indicators)

### 2. FastAPI Backend
- WebSocket server for frontend communication
- OpenAI Realtime Agent with function calling
- Claude Code process manager (spawn/monitor `claude` CLI)
- Task queue for sequential code operations

### 3. Voice Agent Functions
```python
tools = [
    {"name": "ask_claude_code", "description": "Ask Claude Code to perform a coding task"},
    {"name": "read_file", "description": "Read a file from the project"},
    {"name": "run_command", "description": "Run a shell command"},
    {"name": "search_codebase", "description": "Search for code patterns"},
    {"name": "browse_web", "description": "Use Browser Base for web research"},
]
```

## User Flow

1. User opens Electron app and speaks: *"Hey, add a login endpoint to my FastAPI server"*
2. OpenAI Realtime Agent processes speech, calls `ask_claude_code` function
3. Backend spawns Claude Code CLI with the task
4. Claude Code edits files, runs tests
5. Results stream back to Realtime Agent
6. Agent speaks response: *"Done. I added a /login POST endpoint with JWT authentication. Want me to explain the implementation?"*

## Implementation Steps

1. **Backend Setup**
   - Add OpenAI Realtime SDK (`openai-agents`)
   - Create Claude Code subprocess manager
   - Implement WebSocket communication layer
   - Add function definitions for code tasks

2. **Frontend Updates**
   - Add WebRTC audio handling
   - Create voice activity indicator UI
   - Add Monaco editor integration
   - Build terminal output component

3. **Integration**
   - Wire voice commands to Claude Code actions
   - Stream Claude Code output to UI
   - Handle interruptions and cancellations
   - Add Browser Base for web-based tasks (optional)

## Tech Stack
- **Frontend**: Electron + TypeScript + React
- **Backend**: FastAPI + Python + uv
- **Voice**: OpenAI Realtime API (WebRTC/WebSocket)
- **Code Agent**: Claude Code CLI
- **Browser Automation**: Browser Base + Stagehand (optional)
