"""EpicAscii terminal client - curses UI with WebSocket networking."""

import argparse
import asyncio
import curses
import json
import queue
import sys
import textwrap
import threading

import websockets

from shared.protocol import (
    COLOR_BLACK, COLOR_RED, COLOR_GREEN, COLOR_YELLOW, COLOR_BLUE,
    COLOR_MAGENTA, COLOR_CYAN, COLOR_WHITE, COLOR_DIM,
    COLOR_BRIGHT_RED, COLOR_BRIGHT_GREEN, COLOR_BRIGHT_YELLOW,
    COLOR_BRIGHT_BLUE, COLOR_BRIGHT_MAGENTA, COLOR_BRIGHT_CYAN,
    COLOR_BRIGHT_WHITE, DEFAULT_PORT,
    PHASE_CHARACTER_CREATE, PHASE_STORY, PHASE_BATTLE, PHASE_LOOT,
)


# ---------------------------------------------------------------------------
# Key mappings
# ---------------------------------------------------------------------------

MOVE_KEYS = {
    ord('w'): ( 0, -1), ord('a'): (-1,  0),
    ord('s'): ( 0,  1), ord('d'): ( 1,  0),
    ord('y'): (-1, -1), ord('u'): ( 1, -1),
    ord('b'): (-1,  1), ord('n'): ( 1,  1),
}

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class GameClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port

        self.frame_queue = queue.Queue()
        self.send_queue = queue.Queue()
        self.current_frame = None
        self.connected = False
        self.connection_error = None
        self.running = True

        # UI state
        self.ui_state = 'PLAYING'
        self.inv_cursor = 0
        self.chat_input = ''
        self.show_chat = False

    # -- networking --

    def network_thread(self):
        try:
            asyncio.run(self._network_main())
        except Exception as e:
            self.connection_error = str(e)
            self.connected = False

    async def _network_main(self):
        uri = f"ws://{self.host}:{self.port}"
        last_err = None
        for attempt in range(15):
            try:
                async with websockets.connect(uri, max_size=2**20,
                                              open_timeout=5,
                                              ping_interval=20, ping_timeout=60) as ws:
                    self.connected = True
                    while not self.send_queue.empty():
                        try:
                            msg = self.send_queue.get_nowait()
                            await ws.send(json.dumps(msg))
                        except queue.Empty:
                            break
                    await ws.send(json.dumps({'type': 'join'}))
                    recv = asyncio.create_task(self._recv_loop(ws))
                    send = asyncio.create_task(self._send_loop(ws))
                    done, pending = await asyncio.wait(
                        [recv, send], return_when=asyncio.FIRST_COMPLETED)
                    for t in pending:
                        t.cancel()
                    return
            except (OSError, websockets.ConnectionClosed) as e:
                last_err = e
                await asyncio.sleep(1)
            except Exception as e:
                self.connection_error = str(e)
                return
        self.connection_error = str(last_err) if last_err else "Could not connect"

    async def _recv_loop(self, ws):
        try:
            async for raw in ws:
                self.frame_queue.put(json.loads(raw))
        except websockets.ConnectionClosed:
            pass

    async def _send_loop(self, ws):
        while self.running:
            try:
                msg = self.send_queue.get_nowait()
                await ws.send(json.dumps(msg))
            except queue.Empty:
                await asyncio.sleep(0.02)
            except websockets.ConnectionClosed:
                break

    def send(self, msg):
        self.send_queue.put(msg)

    # -- colors --

    def _init_colors(self):
        curses.start_color()
        curses.use_default_colors()
        for i in range(1, 8):
            curses.init_pair(i, i, -1)
        curses.init_pair(8, curses.COLOR_WHITE, -1)
        for i in range(9, 16):
            curses.init_pair(i, (i - 8) % 8 if (i - 8) % 8 != 0 else 7, -1)

    def color_attr(self, idx):
        if idx == COLOR_BLACK: return curses.A_NORMAL
        elif 1 <= idx <= 7: return curses.color_pair(idx)
        elif idx == COLOR_DIM: return curses.color_pair(8) | curses.A_DIM
        elif 9 <= idx <= 15: return curses.color_pair(idx) | curses.A_BOLD
        return curses.A_NORMAL

    # -- rendering --

    def render(self, stdscr):
        frame = self.current_frame
        if not frame:
            return
        phase = frame.get('phase', '')
        if phase == PHASE_STORY:
            self._render_story(stdscr, frame)
        elif phase == PHASE_LOOT:
            self._render_loot(stdscr, frame)
        elif phase == PHASE_BATTLE:
            self._render_battle(stdscr, frame)
        elif phase == PHASE_CHARACTER_CREATE:
            self._render_waiting(stdscr, "Joining the army...")
        else:
            self._render_waiting(stdscr, "Waiting...")

    def _render_waiting(self, stdscr, msg):
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        try:
            stdscr.addstr(h // 2, max(0, (w - len(msg)) // 2), msg, curses.A_BOLD)
        except curses.error:
            pass
        stdscr.refresh()

    def _render_story(self, stdscr, frame):
        stdscr.erase()
        h, w = stdscr.getmaxyx()

        title = frame.get('title', '')
        text = frame.get('text', '')
        choices = frame.get('choices', [])
        player_choice = frame.get('player_choice')
        pr = frame.get('players_ready', 0)
        pt = frame.get('players_total', 1)

        y = 1
        # Title
        try:
            stdscr.addstr(y, 2, f"=== {title} ===", self.color_attr(COLOR_BRIGHT_YELLOW) | curses.A_BOLD)
        except curses.error:
            pass
        y += 2

        # Text (word-wrapped)
        for para in text.split('\n'):
            for line in textwrap.wrap(para, w - 4) or ['']:
                if y < h - len(choices) - 4:
                    try:
                        stdscr.addstr(y, 2, line[:w-4], self.color_attr(COLOR_WHITE))
                    except curses.error:
                        pass
                    y += 1
            y += 1

        # Choices
        y = max(y, h - len(choices) - 3)
        for i, choice in enumerate(choices):
            attr = self.color_attr(COLOR_GREEN) if player_choice == i else self.color_attr(COLOR_YELLOW)
            marker = '>' if player_choice == i else ' '
            try:
                stdscr.addstr(y, 2, f"{marker} {i+1}. {choice}"[:w-4], attr)
            except curses.error:
                pass
            y += 1

        # Waiting status
        if player_choice is not None:
            try:
                stdscr.addstr(h - 1, 2, f"Waiting... ({pr}/{pt} ready)",
                              self.color_attr(COLOR_DIM))
            except curses.error:
                pass
        else:
            try:
                stdscr.addstr(h - 1, 2, "Press 1-9 to choose",
                              self.color_attr(COLOR_YELLOW) | curses.A_REVERSE)
            except curses.error:
                pass

        stdscr.refresh()

    def _render_loot(self, stdscr, frame):
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        items = frame.get('loot_items', [])
        picked = frame.get('picked', False)
        stats = frame.get('stats', {})

        try:
            stdscr.addstr(1, 2, "=== BATTLE SPOILS ===", self.color_attr(COLOR_BRIGHT_YELLOW) | curses.A_BOLD)
        except curses.error:
            pass

        if picked:
            try:
                stdscr.addstr(3, 2, "Item claimed! Waiting for others...", self.color_attr(COLOR_GREEN))
                pr = frame.get('players_ready', 0)
                pt = frame.get('players_total', 1)
                stdscr.addstr(4, 2, f"({pr}/{pt} ready)", self.color_attr(COLOR_DIM))
            except curses.error:
                pass
        else:
            try:
                stdscr.addstr(3, 2, "Choose one item (press number):", self.color_attr(COLOR_WHITE))
            except curses.error:
                pass
            for i, item in enumerate(items):
                stat = ''
                if item['type'] == 'weapon': stat = f'+{item["damage"]} ATK'
                elif item['type'] == 'armor': stat = f'+{item["defense"]} DEF'
                else: stat = f'+{item["heal"]} HP'
                try:
                    stdscr.addstr(5 + i, 4, f"{i+1}. {item['name']}", self.color_attr(COLOR_YELLOW))
                    stdscr.addstr(5 + i, 30, stat, self.color_attr(COLOR_DIM))
                except curses.error:
                    pass

        # Current equip
        try:
            y = h - 2
            stdscr.addstr(y, 2, f"Current: Wpn:{stats.get('weapon','?')} Arm:{stats.get('armor','?')} Lv:{stats.get('level',1)}",
                          self.color_attr(COLOR_DIM))
        except curses.error:
            pass

        stdscr.refresh()

    def _render_battle(self, stdscr, frame):
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        if width < 40 or height < 16:
            try:
                stdscr.addstr(0, 0, "Terminal too small!", curses.A_BOLD)
            except curses.error:
                pass
            stdscr.refresh()
            return

        map_rows = frame.get('map_rows', [])
        color_rows = frame.get('color_rows', [])
        stats = frame.get('stats', {})
        log_msgs = frame.get('log', [])
        alive = frame.get('alive', True)
        army = frame.get('army', {})

        # Map fills the screen, offset 0 (no header row)
        for y, (row, colors) in enumerate(zip(map_rows, color_rows)):
            if y >= height - 3:
                break
            for x, (ch, color) in enumerate(zip(row, colors)):
                if x >= width - 1:
                    break
                try:
                    stdscr.addch(y, x, ch, self.color_attr(color))
                except curses.error:
                    pass

        # Compact stats bar
        sy = height - 3
        hp = stats.get('hp', 0)
        max_hp = stats.get('max_hp', 1)
        hp_pct = hp / max(1, max_hp)
        hp_color = COLOR_GREEN if hp_pct > 0.7 else COLOR_YELLOW if hp_pct > 0.3 else COLOR_RED
        filled = int(hp_pct * 8)
        hp_bar = '#' * filled + '-' * (8 - filled)
        title = frame.get('battle_title', '')
        blue_str = f"A:{army.get('blue',0)}/{army.get('blue_total',0)}"
        red_str = f"E:{army.get('red',0)}/{army.get('red_total',0)}"
        line = (f" [{hp_bar}]{hp}/{max_hp}"
                f" Lv{stats.get('level',1)}"
                f" S{stats.get('str',0)} D{stats.get('def',0)}"
                f" {stats.get('weapon','Fists')}"
                f"  {blue_str} vs {red_str}"
                f"  {title}")
        line = line[:width - 1]
        pad = ' ' * max(0, width - 1 - len(line))
        try:
            stdscr.addstr(sy, 0, line + pad, self.color_attr(hp_color) | curses.A_REVERSE)
        except curses.error:
            pass

        # Log (single line, most recent message)
        log_y = sy + 1
        if log_msgs:
            try:
                stdscr.addstr(log_y, 1, log_msgs[-1][:width-2], self.color_attr(COLOR_WHITE))
            except curses.error:
                pass

        # Bottom hint
        by = height - 1
        hint = " WASD:Move  Bump:Attack  i:Inv  ?:Help"
        if not alive:
            hint = " FALLEN -- Your allies fight on..."
        hint = hint[:width - 1]
        pad = ' ' * max(0, width - 1 - len(hint))
        try:
            stdscr.addstr(by, 0, hint + pad, self.color_attr(COLOR_YELLOW) | curses.A_REVERSE)
        except curses.error:
            pass

        # Inventory overlay
        if self.ui_state == 'INVENTORY':
            self._draw_inventory(stdscr, frame, width, height)

        # Help overlay
        if self.ui_state == 'HELP':
            self._draw_help(stdscr, width, height)

        stdscr.refresh()

    def _draw_inventory(self, stdscr, frame, width, height):
        inv = frame.get('inventory', [])
        stats = frame.get('stats', {})
        box_w = min(44, width - 4)
        box_h = min(len(inv) + 8, height - 4, 20)
        bx = (width - box_w) // 2
        by = (height - box_h) // 2
        self.inv_cursor = max(0, min(self.inv_cursor, len(inv) - 1))

        for row in range(box_h):
            try: stdscr.addstr(by + row, bx, ' ' * box_w, curses.A_REVERSE)
            except curses.error: pass

        try: stdscr.addstr(by, bx + (box_w - 11) // 2, " INVENTORY ", curses.A_REVERSE | curses.A_BOLD)
        except curses.error: pass
        try:
            stdscr.addstr(by + 1, bx + 2, f"Weapon: {stats.get('weapon','?')}", curses.color_pair(3) | curses.A_REVERSE)
            stdscr.addstr(by + 2, bx + 2, f"Armor:  {stats.get('armor','?')}", curses.color_pair(3) | curses.A_REVERSE)
        except curses.error: pass

        if not inv:
            try: stdscr.addstr(by + 4, bx + 2, "(empty)", curses.A_REVERSE)
            except curses.error: pass
        else:
            visible = box_h - 6
            scroll = max(0, self.inv_cursor - visible + 1)
            for i in range(scroll, min(len(inv), scroll + visible)):
                item = inv[i]
                pfx = '>' if i == self.inv_cursor else ' '
                eq = '*' if item.get('equipped') else ' '
                stat = ''
                if item['type'] == 'weapon': stat = f" +{item['damage']}ATK"
                elif item['type'] == 'armor': stat = f" +{item['defense']}DEF"
                elif item.get('heal'): stat = f" +{item['heal']}HP"
                line = f"{pfx}{eq}{item['name']}{stat}"
                attr = curses.A_REVERSE | curses.A_BOLD if i == self.inv_cursor else curses.A_REVERSE
                try: stdscr.addstr(by + 4 + (i - scroll), bx + 1, line[:box_w-2], attr)
                except curses.error: pass

        try: stdscr.addstr(by + box_h - 1, bx + 1, "[e]Equip [d]Drop [q]Use [Esc]Close", curses.A_REVERSE | curses.A_DIM)
        except curses.error: pass

    def _draw_help(self, stdscr, width, height):
        lines = [
            "======== HELP ========",
            "", " WASD or Arrows: Move",
            " Walk into enemies to attack",
            " . Wait  i Inventory",
            " t Chat  ? Help  Q Quit",
            "", " INVENTORY",
            " e Equip  d Drop  q Use",
            " Esc Close",
            "", " Press ? or Esc to close",
            "=======================",
        ]
        bw = max(len(l) for l in lines) + 4
        bh = len(lines) + 2
        bx = (width - bw) // 2
        by = (height - bh) // 2
        for row in range(bh):
            try: stdscr.addstr(by + row, bx, ' ' * bw, curses.A_REVERSE)
            except curses.error: pass
        for i, line in enumerate(lines):
            try: stdscr.addstr(by + 1 + i, bx + 2, line, curses.A_REVERSE)
            except curses.error: pass

    # -- input --

    def handle_input(self, key):
        frame = self.current_frame
        if not frame:
            return
        phase = frame.get('phase', '')

        # Story phase: number keys
        if phase == PHASE_STORY:
            if ord('1') <= key <= ord('9'):
                self.send({'type': 'story_choice', 'choice_idx': key - ord('1')})
            return

        # Loot phase: number keys
        if phase == PHASE_LOOT:
            if ord('1') <= key <= ord('9'):
                self.send({'type': 'loot_pick', 'item_idx': key - ord('1')})
            return

        # Battle phase
        if phase != PHASE_BATTLE:
            return

        if self.ui_state == 'HELP':
            if key in (ord('?'), 27):
                self.ui_state = 'PLAYING'
            return

        if self.ui_state == 'CHAT':
            if key == 27:
                self.ui_state = 'PLAYING'
                self.chat_input = ''
            elif key in (10, 13, curses.KEY_ENTER):
                if self.chat_input.strip():
                    self.send({'type': 'chat', 'message': self.chat_input})
                self.chat_input = ''
                self.ui_state = 'PLAYING'
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                self.chat_input = self.chat_input[:-1]
            elif 32 <= key <= 126:
                self.chat_input += chr(key)
            return

        if self.ui_state == 'INVENTORY':
            inv = frame.get('inventory', [])
            if key in (27, ord('i')):
                self.ui_state = 'PLAYING'
            elif key in (curses.KEY_UP, ord('k')):
                self.inv_cursor = max(0, self.inv_cursor - 1)
            elif key in (curses.KEY_DOWN, ord('j')):
                self.inv_cursor = min(len(inv) - 1, self.inv_cursor + 1)
            elif key == ord('e'):
                self.send({'type': 'equip', 'item_idx': self.inv_cursor})
            elif key == ord('d'):
                self.send({'type': 'drop', 'item_idx': self.inv_cursor})
                if self.inv_cursor > 0: self.inv_cursor -= 1
            elif key == ord('q'):
                self.send({'type': 'use', 'item_idx': self.inv_cursor})
                if self.inv_cursor > 0: self.inv_cursor -= 1
            return

        # PLAYING state
        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            self.send({'type': 'move', 'dx': dx, 'dy': dy})
        elif key == curses.KEY_UP:
            self.send({'type': 'move', 'dx': 0, 'dy': -1})
        elif key == curses.KEY_DOWN:
            self.send({'type': 'move', 'dx': 0, 'dy': 1})
        elif key == curses.KEY_LEFT:
            self.send({'type': 'move', 'dx': -1, 'dy': 0})
        elif key == curses.KEY_RIGHT:
            self.send({'type': 'move', 'dx': 1, 'dy': 0})
        elif key == ord('.'):
            self.send({'type': 'wait'})
        elif key == ord('g'):
            self.send({'type': 'pickup'})
        elif key == ord('i'):
            self.ui_state = 'INVENTORY'
            self.inv_cursor = 0
        elif key == ord('t'):
            self.ui_state = 'CHAT'
            self.chat_input = ''
        elif key == ord('?'):
            self.ui_state = 'HELP'
        elif key == ord('Q'):
            self.running = False

    # -- main loop --

    def curses_main(self, stdscr):
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(50)
        self._init_colors()

        height, width = stdscr.getmaxyx()
        self.send({'type': 'resize', 'width': width, 'height': height})

        for _ in range(300):
            if self.connected or self.connection_error:
                break
            stdscr.erase()
            stdscr.addstr(0, 0, f"Connecting to {self.host}:{self.port}...")
            stdscr.refresh()
            curses.napms(50)

        if not self.connected:
            stdscr.erase()
            stdscr.addstr(0, 0, f"Connection failed: {self.connection_error or 'Timed out'}")
            stdscr.addstr(1, 0, "Press any key to exit.")
            stdscr.nodelay(False)
            stdscr.getch()
            return

        while self.running:
            while True:
                try: self.current_frame = self.frame_queue.get_nowait()
                except queue.Empty: break

            try:
                key = stdscr.getch()
                if key == curses.KEY_RESIZE:
                    height, width = stdscr.getmaxyx()
                    self.send({'type': 'resize', 'width': width, 'height': height})
                elif key != -1:
                    self.handle_input(key)
            except curses.error:
                pass

            self.render(stdscr)

            if not self.connected and self.connection_error:
                stdscr.erase()
                stdscr.addstr(0, 0, f"Disconnected: {self.connection_error}")
                stdscr.addstr(1, 0, "Press any key to exit.")
                stdscr.refresh()
                stdscr.nodelay(False)
                stdscr.getch()
                break


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="EpicAscii game client")
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    print("Connecting to the war...")

    client = GameClient(args.host, args.port)
    net = threading.Thread(target=client.network_thread, daemon=True)
    net.start()

    try:
        curses.wrapper(client.curses_main)
    except KeyboardInterrupt:
        pass
    finally:
        client.running = False


if __name__ == '__main__':
    main()
