# EpicAscii - Multiplayer Battle Roguelike

## What this is

A multiplayer ASCII battle roguelike inspired by Dwarf Fortress adventure mode, pivoted to a military campaign game. Headless WebSocket server with both a curses terminal client and a web browser client.

## Game flow

1. Player clicks "Join the War" (web) or runs `python run_client.py` (terminal)
2. Server auto-generates a random character (name, class, backstory) - player is a weakling grunt
3. Player is dropped straight into a battle on a 120x50 tile battlefield
4. Two armies (blue allies vs red enemies) fight in real-time with AI soldiers
5. Player controls their `@` with WASD/arrows, bump-attacks enemies
6. After battle: loot screen (pick one item), then CYOA story choices
7. Story choices determine the next battle terrain/enemies
8. 3-battle campaign that loops

## Architecture

- `shared/protocol.py` - tile types, colors, game phase constants, soldier classes
- `server/battlefield.py` - procedural battlefield generation, FOV shadow-casting, line-of-sight
- `server/entities.py` - Entity/Player/Soldier/Item classes, AI, random character generation
- `server/story.py` - campaign CYOA story nodes and battle configs
- `server/main.py` - Game state machine, Battle class, WebSocket server, frame generation
- `client/main.py` - curses terminal client with threaded networking
- `web_client.html` - single-file browser client (HTML/JS/CSS)
- `start.sh` - starts game server + HTTP server, opens browser
- `run_server.py` / `run_client.py` - entry points

## How to run

```
./start.sh          # starts server, opens browser
python run_client.py  # terminal client (in separate terminal, with venv active)
```

Requires: Python 3.10+, `websockets` package (installed in `.venv`)

## Current status: BROKEN - known issues

### Web client disconnects on join
The web browser client frequently disconnects immediately when clicking "Join the War". The server log shows "opening handshake failed" errors. Root cause not fully resolved. Attempted fixes:
- Added connection retry logic in the web client (10 retries, 1s apart)
- Added delayed resize sends (setTimeout 100ms and 500ms) to avoid measuring DOM before reflow
- Added fallback dimensions if map container has zero size
- Added better error messages in onclose handler
- Silenced noisy websockets handshake errors in server log
- Added try/except around create_player and process_action in server handler
- None of these fully fixed the issue for the user

### Terminal client timeout
The terminal client initially timed out connecting. Fixed by increasing retry count and wait time, but the 5-second initial timeout was too short for world generation. Extended to 15 seconds with retry logic.

### Previous iteration (open-world roguelike)
The game was originally an open-world roguelike (DF adventure mode clone) with towns, NPCs, dungeons. This was fully scrapped and rewritten as the army battle game. Old `server/world.py` was deleted and replaced with `server/battlefield.py`.

### Controls were bad
Originally used vi keys (hjkl) which confused the user. Changed to WASD + arrow keys as primary.

### start.sh broke multiple times
- First version used `seq` which doesn't work in macOS zsh - replaced with while loop
- Port conflicts from zombie processes - added `lsof -ti:PORT | xargs kill -9` cleanup
- Browser opened before server was ready - added socket polling wait
- The `open` command was initially opening the raw HTML file (`file://`) instead of through HTTP server - changed to serve via `python -m http.server 8080`

### Story screen showed before battle
User wanted to go straight into battle on join, not read a story first. Fixed by adding a 'first_blood' battle node and having create_player() start battle immediately.

### Character creation was manual
User wanted auto-generated characters, not a class picker. Removed all character creation UI. Server now generates random names, classes, and backstories procedurally.

### Map was too small
The ASCII map only filled a small portion of the screen. Reduced UI chrome from 7 lines to 3-4 lines (compact stats bar, single log line, hint bar). Fixed web client CSS for proper flex layout. Changed font from 16px to 14px. Added proper character-size measurement for viewport calculation.

## Design notes

- Server tick rate: 10/sec
- Battlefield: 120x50 tiles, 6 terrain presets
- Player starts very weak: HP 25-40, STR 3-5, DEF 0-2, no weapon
- 5 soldier classes (swordsman, archer, knight, scout, pikeman) assigned randomly
- Spatial grid `_grid[(x,y)]` for O(1) entity lookups during battle
- FOV uses recursive shadow-casting
- Ranged attacks use Bresenham line-of-sight
- AI soldiers chase nearest enemy, attack when adjacent (or at range for archers)
