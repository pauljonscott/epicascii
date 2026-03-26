"""EpicAscii headless game server - battle roguelike."""

import argparse
import asyncio
import json
import logging
import math
import random
import time

import websockets

from shared.protocol import (
    TILE_INFO, TILE_VOID, TILE_BLOOD,
    COLOR_CYAN, COLOR_BRIGHT_WHITE, COLOR_BRIGHT_RED, COLOR_BRIGHT_BLUE,
    COLOR_DIM, COLOR_BLACK, COLOR_WHITE, COLOR_YELLOW, COLOR_GREEN,
    ITEM_WEAPON, ITEM_ARMOR, ITEM_POTION, ITEM_FOOD,
    ARMY_BLUE, ARMY_RED,
    PHASE_CHARACTER_CREATE, PHASE_STORY, PHASE_BATTLE, PHASE_LOOT,
    SOLDIER_CLASSES, DEFAULT_FOV_RADIUS, SERVER_TICK_RATE, DEFAULT_PORT,
    CLASS_SWORDSMAN,
)
from server.battlefield import Battlefield, compute_fov, has_line_of_sight
from server.entities import (
    Entity, Player, Soldier, Item,
    SOLDIER_TEMPLATES, ITEM_TEMPLATES, generate_loot_pool,
    generate_random_character,
)
from server.story import Campaign

log = logging.getLogger("epicascii")

# ---------------------------------------------------------------------------
# Battle instance
# ---------------------------------------------------------------------------

class Battle:
    def __init__(self, config, players):
        self.config = config
        self.battlefield = Battlefield(
            terrain_type=config.get('terrain', 'open_plains'),
        )
        self.blue_soldiers = []
        self.red_soldiers = []
        self.players = list(players.values())
        self.outcome = None  # None, 'victory', 'defeat'
        self.tick_count = 0
        # Spatial lookup for O(1) collision checks
        self._grid = {}  # (x,y) -> entity

        self._spawn_armies(config)

    def _spawn_armies(self, config):
        # Blue army (AI soldiers)
        blue_comp = config.get('blue_army', {'swordsman': 15})
        blue_positions = self.battlefield.get_blue_spawn_positions(
            sum(blue_comp.values()) + len(self.players) + 5)

        pos_idx = 0
        # Place players first
        for p in self.players:
            if pos_idx < len(blue_positions):
                p.x, p.y = blue_positions[pos_idx]
                pos_idx += 1
            p.reset_for_battle()
            self._grid[(p.x, p.y)] = p

        # Place blue AI soldiers
        for template_key, count in blue_comp.items():
            for _ in range(count):
                if pos_idx < len(blue_positions):
                    x, y = blue_positions[pos_idx]
                    pos_idx += 1
                else:
                    x, y = random.randint(3, 14), random.randint(3, self.battlefield.height - 3)
                s = Soldier(x, y, ARMY_BLUE, template_key)
                self.blue_soldiers.append(s)
                self._grid[(s.x, s.y)] = s

        # Blue commander
        if pos_idx < len(blue_positions):
            x, y = blue_positions[pos_idx]
        else:
            x, y = 5, self.battlefield.height // 2
        cmd = Soldier(x, y, ARMY_BLUE, 'commander')
        self.blue_soldiers.append(cmd)
        self._grid[(cmd.x, cmd.y)] = cmd

        # Red army
        red_comp = config.get('red_army', {'swordsman': 15})
        red_positions = self.battlefield.get_red_spawn_positions(
            sum(red_comp.values()) + 5)

        pos_idx = 0
        for template_key, count in red_comp.items():
            for _ in range(count):
                if pos_idx < len(red_positions):
                    x, y = red_positions[pos_idx]
                    pos_idx += 1
                else:
                    x, y = (self.battlefield.width - random.randint(3, 14),
                            random.randint(3, self.battlefield.height - 3))
                s = Soldier(x, y, ARMY_RED, template_key)
                self.red_soldiers.append(s)
                self._grid[(s.x, s.y)] = s

        # Red commander
        if config.get('red_commander', True):
            if pos_idx < len(red_positions):
                x, y = red_positions[pos_idx]
            else:
                x, y = self.battlefield.width - 5, self.battlefield.height // 2
            cmd = Soldier(x, y, ARMY_RED, 'commander')
            self.red_soldiers.append(cmd)
            self._grid[(cmd.x, cmd.y)] = cmd

    def entity_at(self, x, y):
        return self._grid.get((x, y))

    def can_move_to(self, x, y):
        return self.battlefield.is_walkable(x, y) and (x, y) not in self._grid

    def move_entity(self, ent, nx, ny):
        old = (ent.x, ent.y)
        if old in self._grid and self._grid[old] is ent:
            del self._grid[old]
        ent.x = nx
        ent.y = ny
        self._grid[(nx, ny)] = ent

    def remove_entity(self, ent):
        pos = (ent.x, ent.y)
        if pos in self._grid and self._grid[pos] is ent:
            del self._grid[pos]

    def find_nearest_enemy(self, soldier):
        """Find the nearest enemy of the given soldier. Returns (entity, distance) or (None, 0)."""
        enemies = self._get_enemies_of(soldier)
        best = None
        best_dist = 9999
        for e in enemies:
            if not e.alive:
                continue
            d = abs(e.x - soldier.x) + abs(e.y - soldier.y)
            if d < best_dist:
                best_dist = d
                best = e
        return best, best_dist

    def _get_enemies_of(self, soldier):
        if soldier.army == ARMY_BLUE:
            return self.red_soldiers
        else:
            return self.blue_soldiers + self.players

    def melee_attack(self, attacker, defender):
        atk = attacker.attack_power()
        dfn = defender.total_defense()
        dmg = max(1, atk - dfn + random.randint(-2, 2))
        actual = defender.take_damage(dmg)

        if not defender.alive:
            self.remove_entity(defender)
            self.battlefield.set_tile(defender.x, defender.y, TILE_BLOOD)

        # Log to nearby players
        for p in self.players:
            dist = abs(p.x - attacker.x) + abs(p.y - attacker.y)
            if dist <= p.fov_radius and (attacker.x, attacker.y) in p.visible:
                if isinstance(defender, Player) and defender is p:
                    p.log.append(f"{attacker.name} hits YOU for {actual}! [{p.hp}/{p.max_hp}]")
                    if not p.alive:
                        p.log.append("*** You have fallen in battle! ***")
                elif isinstance(attacker, Player) and attacker is p:
                    msg = f"You hit {defender.name} for {actual}."
                    if not defender.alive:
                        msg += f" {defender.name} falls! (+{defender.xp_value} XP)"
                        p.kills += 1
                        p.gain_xp(defender.xp_value)
                    else:
                        msg += f" [{defender.hp}/{defender.max_hp}]"
                    p.log.append(msg)
                else:
                    if not defender.alive:
                        side = "ally" if attacker.army == ARMY_BLUE else "enemy"
                        p.log.append(f"{attacker.name} slays {defender.name}!")

    def ranged_attack(self, attacker, defender):
        # Ranged is slightly weaker than melee
        atk = attacker.attack_power() - 1
        dfn = defender.total_defense()
        dmg = max(1, atk - dfn + random.randint(-2, 1))
        actual = defender.take_damage(dmg)

        if not defender.alive:
            self.remove_entity(defender)
            self.battlefield.set_tile(defender.x, defender.y, TILE_BLOOD)

        for p in self.players:
            dist = abs(p.x - attacker.x) + abs(p.y - attacker.y)
            if dist <= p.fov_radius:
                if isinstance(defender, Player) and defender is p:
                    p.log.append(f"{attacker.name} shoots YOU for {actual}! [{p.hp}/{p.max_hp}]")
                    if not p.alive:
                        p.log.append("*** You have fallen in battle! ***")
                elif isinstance(attacker, Player) and attacker is p:
                    msg = f"Your arrow hits {defender.name} for {actual}."
                    if not defender.alive:
                        msg += f" {defender.name} falls! (+{defender.xp_value} XP)"
                        p.kills += 1
                        p.gain_xp(defender.xp_value)
                    p.log.append(msg)

    def tick(self):
        """Advance one battle tick."""
        self.tick_count += 1
        any_acted = False

        # Update all soldiers
        all_soldiers = self.blue_soldiers + self.red_soldiers
        dead = []
        for s in all_soldiers:
            if s.alive:
                old_x, old_y = s.x, s.y
                if s.update_ai(self):
                    any_acted = True
                    # Update grid if moved
                    if s.x != old_x or s.y != old_y:
                        if (old_x, old_y) in self._grid and self._grid[(old_x, old_y)] is s:
                            del self._grid[(old_x, old_y)]
                        self._grid[(s.x, s.y)] = s
            else:
                dead.append(s)

        for s in dead:
            if s in self.blue_soldiers:
                self.blue_soldiers.remove(s)
            elif s in self.red_soldiers:
                self.red_soldiers.remove(s)

        # Check battle outcome
        red_alive = sum(1 for s in self.red_soldiers if s.alive)
        blue_alive = (sum(1 for s in self.blue_soldiers if s.alive)
                      + sum(1 for p in self.players if p.alive))

        if red_alive == 0:
            self.outcome = 'victory'
        elif blue_alive == 0:
            self.outcome = 'defeat'

        return any_acted

    def get_army_counts(self):
        blue = (sum(1 for s in self.blue_soldiers if s.alive)
                + sum(1 for p in self.players if p.alive))
        red = sum(1 for s in self.red_soldiers if s.alive)
        blue_total = len(self.blue_soldiers) + len(self.players)
        red_total = len(self.red_soldiers)
        return blue, blue_total, red, red_total


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------

class Game:
    def __init__(self):
        self.phase = PHASE_CHARACTER_CREATE
        self.players = {}       # id -> Player
        self.campaign = Campaign()
        self.battle = None
        self.chat_log = []
        self.tick_count = 0
        self.loot_pool = []     # available items for loot phase
        self.loot_picks = {}    # player_id -> item_key picked

    def create_player(self):
        """Auto-generate a random recruit and throw them into battle."""
        name, soldier_class, backstory = generate_random_character()
        player = Player(0, 0, name, soldier_class)
        player.backstory = backstory
        class_name = SOLDIER_CLASSES[soldier_class]['name']
        player.log.append(f"=== {name} - {class_name} ===")
        player.log.append(backstory)
        self.players[player.id] = player
        log.info("Player '%s' joined as %s", name, soldier_class)

        if self.phase in (PHASE_CHARACTER_CREATE, PHASE_STORY, PHASE_LOOT):
            # Start (or restart) a battle immediately
            self.start_battle()
        elif self.phase == PHASE_BATTLE and self.battle:
            # Late join: drop into existing battle
            b = self.battle
            positions = b.battlefield.get_blue_spawn_positions(100)
            for px, py in positions:
                if b.can_move_to(px, py):
                    player.x, player.y = px, py
                    player.reset_for_battle()
                    b._grid[(px, py)] = player
                    b.players.append(player)
                    player.log.append("You stumble into the fray.")
                    break

        return player

    def remove_player(self, player):
        self.players.pop(player.id, None)
        log.info("Player '%s' left", player.name)

    def process_action(self, player, action):
        atype = action.get('type')

        if atype == 'resize':
            player.term_width = max(40, action.get('width', 80))
            player.term_height = max(16, action.get('height', 24))
            return

        if atype == 'chat':
            msg = str(action.get('message', ''))[:200]
            if msg:
                self.chat_log.append({'from': player.name, 'text': msg})
                self.chat_log = self.chat_log[-50:]
            return

        # Phase-specific actions
        if self.phase == PHASE_CHARACTER_CREATE:
            # Already handled via create_player
            pass

        elif self.phase == PHASE_STORY:
            if atype == 'story_choice':
                idx = action.get('choice_idx', 0)
                player.story_choice = idx
                player.ready = True
                # Check if all players are ready
                if all(p.ready for p in self.players.values()):
                    self._advance_story()

        elif self.phase == PHASE_BATTLE:
            if atype == 'move' and player.alive:
                self._process_battle_move(player, action['dx'], action['dy'])
            elif atype == 'wait':
                pass
            elif atype == 'pickup' and player.alive:
                self._process_pickup(player)
            elif atype == 'equip':
                self._process_equip(player, action.get('item_idx', -1))
            elif atype == 'use':
                self._process_use(player, action.get('item_idx', -1))
            elif atype == 'drop':
                self._process_drop(player, action.get('item_idx', -1))

        elif self.phase == PHASE_LOOT:
            if atype == 'loot_pick':
                idx = action.get('item_idx', -1)
                if 0 <= idx < len(self.loot_pool):
                    key = self.loot_pool[idx]
                    item = Item(ITEM_TEMPLATES[key])
                    player.inventory.append(item)
                    player.log.append(f"You take {item.name}.")
                    self.loot_picks[player.id] = True
                    player.ready = True
                if all(p.ready for p in self.players.values()):
                    self._advance_from_loot()

    def _process_battle_move(self, player, dx, dy):
        if not self.battle:
            return
        nx, ny = player.x + dx, player.y + dy
        if not self.battle.battlefield.in_bounds(nx, ny):
            return

        entity = self.battle.entity_at(nx, ny)
        if entity and entity.alive:
            if entity.army == ARMY_RED:
                # Attack enemy
                self.battle.melee_attack(player, entity)
                return
            else:
                return  # Can't walk through allies

        if not self.battle.battlefield.is_walkable(nx, ny):
            return

        self.battle.move_entity(player, nx, ny)

    def _process_pickup(self, player):
        # Items on ground not implemented in battle mode yet
        player.log.append("Nothing to pick up.")

    def _process_equip(self, player, idx):
        if idx < 0 or idx >= len(player.inventory):
            return
        item = player.inventory[idx]
        if item.item_type == ITEM_WEAPON:
            if player.weapon is item:
                player.weapon = None
                player.log.append(f"You unequip {item.name}.")
            else:
                player.weapon = item
                player.log.append(f"You equip {item.name}. (+{item.damage} ATK)")
        elif item.item_type == ITEM_ARMOR:
            if player.armor is item:
                player.armor = None
                player.log.append(f"You unequip {item.name}.")
            else:
                player.armor = item
                player.log.append(f"You equip {item.name}. (+{item.defense} DEF)")
        else:
            player.log.append("You can't equip that.")

    def _process_use(self, player, idx):
        if idx < 0 or idx >= len(player.inventory):
            return
        item = player.inventory[idx]
        if item.item_type in (ITEM_POTION, ITEM_FOOD):
            old_hp = player.hp
            player.hp = min(player.max_hp, player.hp + item.heal)
            healed = player.hp - old_hp
            player.inventory.pop(idx)
            if player.weapon is item:
                player.weapon = None
            if player.armor is item:
                player.armor = None
            player.log.append(f"You use {item.name}. (+{healed} HP)")
        else:
            player.log.append("You can't use that.")

    def _process_drop(self, player, idx):
        if idx < 0 or idx >= len(player.inventory):
            return
        item = player.inventory.pop(idx)
        if player.weapon is item:
            player.weapon = None
        if player.armor is item:
            player.armor = None
        player.log.append(f"You drop {item.name}.")

    def start_battle(self):
        """Start a battle from the current campaign node."""
        config = self.campaign.get_battle_config()
        self.battle = Battle(config, self.players)
        self.phase = PHASE_BATTLE
        for p in self.players.values():
            p.log.append(f"=== {config['title']} ===")
            p.log.append(config.get('briefing', 'Battle begins!'))
            p.ready = False
        log.info("Battle started: %s", config['title'])

    def _advance_story(self):
        """All players have made story choices. Apply majority vote."""
        votes = {}
        for p in self.players.values():
            c = p.story_choice if p.story_choice is not None else 0
            votes[c] = votes.get(c, 0) + 1
        winner = max(votes, key=votes.get)

        node_id = self.campaign.advance(winner)
        node = self.campaign.get_current_node()

        for p in self.players.values():
            p.ready = False
            p.story_choice = None

        if node['type'] == 'battle':
            self.start_battle()
        else:
            self.phase = PHASE_STORY

    def _advance_from_loot(self):
        """All players have picked loot. Move to next story node."""
        node_id = self.campaign.advance()
        for p in self.players.values():
            p.ready = False
            p.story_choice = None
        self.loot_pool = []
        self.loot_picks = {}
        self.phase = PHASE_STORY

    def _end_battle(self):
        """Battle has ended. Transition to loot phase."""
        outcome = self.battle.outcome
        loot_tier = self.battle.config.get('loot_tier', 1)

        for p in self.players.values():
            if outcome == 'victory':
                p.log.append("*** VICTORY! Your army is triumphant! ***")
                bonus_xp = 20 * loot_tier
                p.gain_xp(bonus_xp)
                p.log.append(f"Battle bonus: +{bonus_xp} XP, {p.kills} kills")
            else:
                p.log.append("*** DEFEAT. Your army has fallen... ***")
                p.log.append("But the story continues...")
            p.kills = 0
            p.ready = False
            # Heal up partially
            p.hp = min(p.max_hp, p.hp + p.max_hp // 3)
            p.alive = True

        # Generate loot
        self.loot_pool = generate_loot_pool(loot_tier, count=6)
        self.phase = PHASE_LOOT
        self.battle = None
        log.info("Battle ended: %s", outcome)

    def tick(self):
        """One server tick."""
        self.tick_count += 1

        if self.phase == PHASE_BATTLE and self.battle:
            acted = self.battle.tick()
            if self.battle.outcome:
                self._end_battle()
            return acted

        # Auto-advance if single player and in story with only one choice
        return False

    def get_frame(self, player):
        """Build the frame to send to a client."""
        if self.phase == PHASE_STORY:
            return self._get_story_frame(player)
        elif self.phase == PHASE_BATTLE:
            return self._get_battle_frame(player)
        elif self.phase == PHASE_LOOT:
            return self._get_loot_frame(player)
        return {'type': 'frame', 'phase': self.phase}

    def _get_story_frame(self, player):
        node = self.campaign.get_current_node()
        return {
            'type': 'frame',
            'phase': PHASE_STORY,
            'title': node['title'],
            'text': node['text'],
            'choices': [c['label'] for c in node.get('choices', [])],
            'player_choice': player.story_choice,
            'players_ready': sum(1 for p in self.players.values() if p.ready),
            'players_total': len(self.players),
            'log': player.log[-10:],
            'chat': self.chat_log[-10:],
        }

    def _get_loot_frame(self, player):
        items = []
        for key in self.loot_pool:
            t = ITEM_TEMPLATES[key]
            items.append({
                'name': t['name'], 'type': t['type'],
                'damage': t.get('damage', 0),
                'defense': t.get('defense', 0),
                'heal': t.get('heal', 0),
            })
        return {
            'type': 'frame',
            'phase': PHASE_LOOT,
            'loot_items': items,
            'picked': player.id in self.loot_picks,
            'stats': self._player_stats(player),
            'inventory': self._player_inventory(player),
            'log': player.log[-10:],
            'chat': self.chat_log[-10:],
            'players_ready': sum(1 for p in self.players.values() if p.ready),
            'players_total': len(self.players),
        }

    def _get_battle_frame(self, player):
        b = self.battle
        if not b:
            return {'type': 'frame', 'phase': PHASE_BATTLE}

        tw = player.term_width
        th = player.term_height
        map_h = max(5, th - 4)  # Reserve only 4 lines: header, stats, log, hints
        map_w = max(10, tw)

        vx = player.x - map_w // 2
        vy = player.y - map_h // 2

        # Compute FOV
        if player.alive:
            player.visible = compute_fov(b.battlefield.is_opaque,
                                         player.x, player.y, player.fov_radius)
        player.explored.update(player.visible)

        # Build entity map for visible area
        ent_map = {}
        for p2 in self.players.values():
            if p2.alive and p2.id != player.id:
                ent_map[(p2.x, p2.y)] = (p2.glyph, COLOR_CYAN, p2.name)
        for s in b.blue_soldiers:
            if s.alive:
                ent_map[(s.x, s.y)] = (s.glyph, s.color, s.name)
        for s in b.red_soldiers:
            if s.alive:
                ent_map[(s.x, s.y)] = (s.glyph, s.color, s.name)

        map_rows = []
        color_rows = []

        for row in range(map_h):
            chars = []
            colors = []
            for col in range(map_w):
                wx, wy = vx + col, vy + row

                if (wx, wy) in player.visible:
                    if wx == player.x and wy == player.y and player.alive:
                        chars.append('@')
                        colors.append(COLOR_BRIGHT_WHITE)
                    elif (wx, wy) in ent_map:
                        g, c, _ = ent_map[(wx, wy)]
                        chars.append(g)
                        colors.append(c)
                    else:
                        info = TILE_INFO.get(b.battlefield.get_tile_type(wx, wy),
                                             TILE_INFO[TILE_VOID])
                        chars.append(info['glyph'])
                        colors.append(info['color'])
                elif (wx, wy) in player.explored:
                    info = TILE_INFO.get(b.battlefield.get_tile_type(wx, wy),
                                         TILE_INFO[TILE_VOID])
                    chars.append(info['glyph'])
                    colors.append(COLOR_DIM)
                else:
                    chars.append(' ')
                    colors.append(COLOR_BLACK)

            map_rows.append(''.join(chars))
            color_rows.append(colors)

        blue_alive, blue_total, red_alive, red_total = b.get_army_counts()

        return {
            'type': 'frame',
            'phase': PHASE_BATTLE,
            'map_rows': map_rows,
            'color_rows': color_rows,
            'stats': self._player_stats(player),
            'army': {
                'blue': blue_alive, 'blue_total': blue_total,
                'red': red_alive, 'red_total': red_total,
            },
            'battle_title': self.battle.config.get('title', 'Battle'),
            'log': player.log[-20:],
            'inventory': self._player_inventory(player),
            'alive': player.alive,
            'chat': self.chat_log[-10:],
            'players_online': [p.name for p in self.players.values()],
        }

    def _player_stats(self, player):
        return {
            'hp': player.hp, 'max_hp': player.max_hp,
            'str': player.strength,
            'dex': player.dexterity,
            'def': player.defense + (player.armor.defense if player.armor else 0),
            'level': player.level,
            'xp': player.xp, 'xp_next': player.xp_next,
            'weapon': player.weapon.name if player.weapon else 'Fists',
            'armor': player.armor.name if player.armor else 'None',
            'class': player.soldier_class,
            'name': player.name,
            'backstory': player.backstory,
            'x': player.x, 'y': player.y,
        }

    def _player_inventory(self, player):
        return [
            {
                'name': it.name, 'type': it.item_type,
                'equipped': (it is player.weapon or it is player.armor),
                'damage': it.damage, 'defense': it.defense, 'heal': it.heal,
            }
            for it in player.inventory
        ]


# ---------------------------------------------------------------------------
# Network server
# ---------------------------------------------------------------------------

class GameServer:
    def __init__(self, game):
        self.game = game
        self.connections = {}   # websocket -> Player
        self.pending = set()    # websockets not yet joined
        self.dirty = set()

    async def handle_client(self, websocket):
        player = None
        self.pending.add(websocket)
        try:
            async for raw in websocket:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                if data.get('type') == 'join' and player is None:
                    try:
                        player = self.game.create_player()
                    except Exception:
                        log.exception("Error creating player")
                        continue
                    self.connections[websocket] = player
                    self.pending.discard(websocket)
                    self.dirty.add(websocket)

                elif player is not None:
                    try:
                        self.game.process_action(player, data)
                    except Exception:
                        log.exception("Error processing action")
                    self.dirty.add(websocket)
        except websockets.ConnectionClosed:
            pass
        except Exception:
            log.exception("Unexpected error in handle_client")
        finally:
            if player:
                self.game.remove_player(player)
                if self.game.battle and player in self.game.battle.players:
                    self.game.battle.players.remove(player)
                    self.game.battle.remove_entity(player)
            self.connections.pop(websocket, None)
            self.pending.discard(websocket)
            self.dirty.discard(websocket)

    async def game_loop(self):
        tick_interval = 1.0 / SERVER_TICK_RATE
        while True:
            t0 = time.monotonic()

            try:
                any_acted = self.game.tick()
            except Exception:
                log.exception("Error in game tick")
                any_acted = False

            # During battle, update all clients every tick if anything happened
            if any_acted or self.game.phase == PHASE_BATTLE:
                self.dirty.update(self.connections.keys())

            to_send = list(self.dirty)
            self.dirty.clear()

            for ws in to_send:
                player = self.connections.get(ws)
                if player is None:
                    continue
                try:
                    frame = self.game.get_frame(player)
                    await ws.send(json.dumps(frame))
                except websockets.ConnectionClosed:
                    pass
                except Exception:
                    log.exception("Error sending frame")

            elapsed = time.monotonic() - t0
            await asyncio.sleep(max(0, tick_interval - elapsed))

    async def run(self, host, port):
        log.info("Starting server on %s:%d", host, port)
        async with websockets.serve(self.handle_client, host, port,
                                    max_size=2 ** 20,
                                    compression=None,
                                    ping_interval=20, ping_timeout=60):
            await self.game_loop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="EpicAscii battle server")
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(message)s',
        datefmt='%H:%M:%S',
    )
    # Silence noisy websockets handshake errors (startup probes, browser preflight)
    logging.getLogger('websockets').setLevel(logging.CRITICAL)

    print("=" * 50)
    print("  EpicAscii - Multiplayer Battle Roguelike")
    print("=" * 50)
    print(f"  Listening on {args.host}:{args.port}")
    print("  Waiting for players...")
    print("=" * 50)

    game = Game()
    server = GameServer(game)
    asyncio.run(server.run(args.host, args.port))


if __name__ == '__main__':
    main()
