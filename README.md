# AI Agent Platform & Sandbox — Orchestration & Visualization Platform

A full-stack AI agent platform featuring **real-time reasoning visualization**, a **modular tool adapter system**, **context management**, **execution tracing**, and **blockchain/crypto integration** — built entirely from scratch with Python and vanilla JS.


## Architecture

```
The platform uses a ReAct (Reason + Act) reasoning loop:

User Query → [Thought] → [Action: Tool Call] → [Observation: Result] → [Final Answer]
             ↑                                                            ↓
             └────────────────── Loop if needed ──────────────────────────┘
```

### System Design

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Server** | FastAPI + Uvicorn | REST API + SSE streaming |
| **Agent Engine** | Custom ReAct Loop | Step-by-step reasoning with tool use |
| **Tool Registry** | Registry Pattern | Pluggable tool adapter system |
| **Context Manager** | Sliding Window | Token budgeting + conversation history |
| **Trace System** | Event Logging | Full observability with waterfall timing |
| **Frontend** | Vanilla JS + CSS | Real-time visualization + glassmorphism UI |

## Tool Adapters (9 Built-in)

### Blockchain & Crypto
- **get_crypto_price** — Live prices from Coinpaprika API (BTC, ETH, SOL, etc.)
- **get_market_overview** — Top coins, market cap, trends
- **get_trending_coins** — Trending by search volume
- **explore_block** — Bitcoin block explorer
- **hash_data** — SHA-256, SHA-512, MD5, BLAKE2b hashing
- **mining_stats** — Hashrate, difficulty, top mining pools

### Math & Computation
- **calculate** — Safe math expression evaluator
- **unit_convert** — Units including crypto (BTC↔Satoshi, ETH↔Gwei↔Wei)

### Code Execution
- **execute_code** — Sandboxed Python with security restrictions + 5s timeout

## Key Technical Features

### Server-Sent Events (SSE) Streaming
Real-time streaming of agent reasoning steps to the frontend — each Thought, Action, and Observation appears live as the agent processes.

### Tool Adapter Registry Pattern
```python
registry.register(
    name="my_tool",
    description="What it does",
    category="category",
    parameters=[{"name": "arg", "type": "string", "description": "..."}],
    handler=my_function,
)
```

### Context Window Management
- Token counting and budget tracking
- Sliding window with automatic trimming
- Conversation history persistence

### Execution Trace & Observability
- Waterfall timing visualization
- Step-by-step latency and token tracking
- JSON trace export for analysis

### Security Sandbox
- Restricted Python builtins
- Module allowlisting
- Signal-based timeout (5 seconds)
- Blocked: file I/O, network, system access

## Project Structure

```
agentflow/
├── backend/
│   ├── main.py              # FastAPI server + SSE + REST API
│   ├── agent_engine.py       # ReAct reasoning loop
│   ├── context_manager.py    # Context window management
│   ├── trace.py              # Execution trace system
│   ├── models.py             # Pydantic data models
│   └── tools/
│       ├── __init__.py       # Tool adapter registry
│       ├── crypto.py         # CoinGecko integration
│       ├── calculator.py     # Math + unit conversion
│       ├── code_sandbox.py   # Sandboxed code execution
│       └── blockchain.py     # Block explorer + mining
├── frontend/
│   ├── index.html            # Main page
│   ├── css/styles.css        # Design system
│   └── js/app.js             # SSE client + UI logic
├── run.sh                    # One-command startup
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serve frontend |
| `POST` | `/api/agent/stream` | SSE-streamed agent reasoning |
| `GET` | `/api/tools` | List all tool adapters |
| `GET` | `/api/traces/{id}` | Get execution traces + waterfall |
| `GET` | `/api/traces/{id}/export` | Export traces as JSON |
| `GET` | `/api/context/{id}` | Get context window state |
| `GET` | `/api/conversations` | List conversations |
| `GET` | `/api/health` | Health check |

## Extending: Add Your Own Tool

1. Create `backend/tools/my_tool.py`
2. Import and register with the registry
3. The agent automatically discovers and uses it

```python
from backend.tools import registry

def my_handler(param: str = "") -> str:
    return f"Result for {param}"

registry.register(
    name="my_tool",
    description="Does something useful",
    category="custom",
    parameters=[{"name": "param", "type": "string", "description": "Input"}],
    examples=["Use my tool with X"],
    handler=my_handler,
)
```

## Tech Stack

- **Python 3.12** + FastAPI + Uvicorn
- **Pydantic** for data validation
- **Server-Sent Events** for real-time streaming
- **Vanilla JavaScript** (ES6+) — no framework dependencies
- **CSS3** with glassmorphism, animations, dark mode
- **Coinpaprika API** for live crypto data

## Quick Start

### Method 1: Local Virtual Environment

#### macOS / Linux
Simply run the shell script, which will configure the Python virtual environment (`.venv`), install dependencies, and start the FastAPI server:
```bash
./run.sh
```

#### Windows
Run the batch file in Command Prompt or double-click it. It will set up the virtual environment, install requirements, and run the server:
```cmd
run.bat
```

The application will be available at [http://localhost:8000](http://localhost:8000).

### Method 2: Docker Compose (Cross-Platform)
If you prefer running inside containers (works on Windows, macOS, and Linux), run:
```bash
docker-compose up --build
```
The application will be available at [http://localhost:8000](http://localhost:8000).

