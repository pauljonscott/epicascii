# EpicAscii

A multiplayer ASCII battle roguelike. You are a nameless grunt thrown into the ranks of a vast army. Survive the battle, grab loot from the fallen, make choices that shape the campaign, and fight again.

## Gameplay

- **Auto-generated character** — random name, class, and backstory. You start as a barely-armed weakling.
- **Real-time battles** — two armies clash on a procedural ASCII battlefield. You control one soldier (`@`) while AI controls the rest.
- **Bump-to-attack** — walk into enemies to fight them.
- **Loot and equip** — after each battle, pick gear from the spoils to get stronger.
- **CYOA story** — between battles, make choices that determine the next fight.
- **Multiplayer** — multiple players join the same army and fight together via WebSocket.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/yourusername/epicascii.git
cd epicascii
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Play (starts server + opens browser)
./start.sh
```

## Controls

| Key | Action |
|-----|--------|
| `W/A/S/D` or Arrow keys | Move |
| Walk into enemy | Attack |
| `i` | Inventory |
| `e/d/q` | Equip / Drop / Use (in inventory) |
| `.` | Wait |
| `t` | Chat |
| `?` | Help |
| `1-9` | Choose story/loot options |

## Architecture

Headless WebSocket server with two client options:

```
server (Python, asyncio, websockets)
  ├── web client (HTML/JS, opens in browser)
  └── terminal client (Python, curses)
```

- **Server** (`run_server.py`) — game state, battle simulation, AI, campaign progression
- **Web client** (`web_client.html`) — served via built-in HTTP server, connects over WebSocket
- **Terminal client** (`run_client.py`) — curses-based, for terminal purists

## Running Separately

```bash
# Terminal 1: server
source .venv/bin/activate
python run_server.py

# Terminal 2: web client (open http://localhost:8080/web_client.html)
python -m http.server 8080

# Or terminal client
python run_client.py
```

## Project Structure

```
shared/protocol.py      — tiles, colors, constants
server/battlefield.py   — procedural map generation, FOV
server/entities.py      — soldiers, items, combat, AI, character generation
server/story.py         — CYOA campaign, battle configs
server/main.py          — game loop, battle state, WebSocket server
client/main.py          — curses terminal client
web_client.html         — browser client
start.sh                — one-command launcher
```

## Requirements

- Python 3.10+
- `websockets` (installed via `pip install -r requirements.txt`)
- A browser (for web client) or a terminal (for curses client)
