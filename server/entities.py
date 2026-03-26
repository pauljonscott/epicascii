"""Entities, soldiers, items, combat, and AI for EpicAscii battle roguelike."""

import random
import math

from shared.protocol import (
    COLOR_RED, COLOR_GREEN, COLOR_YELLOW, COLOR_BLUE, COLOR_CYAN,
    COLOR_WHITE, COLOR_MAGENTA, COLOR_BRIGHT_WHITE, COLOR_BRIGHT_RED,
    COLOR_BRIGHT_GREEN, COLOR_BRIGHT_BLUE, COLOR_BRIGHT_CYAN,
    COLOR_BRIGHT_YELLOW,
    ITEM_WEAPON, ITEM_ARMOR, ITEM_POTION, ITEM_FOOD,
    ARMY_BLUE, ARMY_RED,
    CLASS_SWORDSMAN, CLASS_ARCHER, CLASS_KNIGHT, CLASS_SCOUT, CLASS_PIKEMAN,
    DEFAULT_FOV_RADIUS,
)

# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------

class Item:
    _next_id = 1

    def __init__(self, template):
        self.id = Item._next_id
        Item._next_id += 1
        self.name = template['name']
        self.glyph = template['glyph']
        self.color = template['color']
        self.item_type = template['type']
        self.damage = template.get('damage', 0)
        self.defense = template.get('defense', 0)
        self.heal = template.get('heal', 0)
        self.tier = template.get('tier', 1)


ITEM_TEMPLATES = {
    # Tier 1 - basic
    'short_sword':    {'name': 'Short Sword',    'glyph': '/', 'color': COLOR_WHITE,        'type': ITEM_WEAPON, 'damage': 3,  'tier': 1},
    'wooden_shield':  {'name': 'Wooden Shield',  'glyph': '[', 'color': COLOR_YELLOW,       'type': ITEM_ARMOR,  'defense': 2, 'tier': 1},
    'leather_cap':    {'name': 'Leather Cap',     'glyph': '[', 'color': COLOR_YELLOW,       'type': ITEM_ARMOR,  'defense': 1, 'tier': 1},
    'bread':          {'name': 'War Rations',     'glyph': '%', 'color': COLOR_YELLOW,       'type': ITEM_FOOD,   'heal': 10,   'tier': 1},
    'bandage':        {'name': 'Bandage',         'glyph': '!', 'color': COLOR_WHITE,        'type': ITEM_POTION, 'heal': 15,   'tier': 1},
    # Tier 2 - military
    'long_sword':     {'name': 'Long Sword',      'glyph': '/', 'color': COLOR_CYAN,         'type': ITEM_WEAPON, 'damage': 5,  'tier': 2},
    'war_spear':      {'name': 'War Spear',       'glyph': '/', 'color': COLOR_WHITE,        'type': ITEM_WEAPON, 'damage': 6,  'tier': 2},
    'iron_shield':    {'name': 'Iron Shield',     'glyph': '[', 'color': COLOR_WHITE,        'type': ITEM_ARMOR,  'defense': 4, 'tier': 2},
    'chain_hauberk':  {'name': 'Chain Hauberk',   'glyph': '[', 'color': COLOR_WHITE,        'type': ITEM_ARMOR,  'defense': 5, 'tier': 2},
    'healing_salve':  {'name': 'Healing Salve',   'glyph': '!', 'color': COLOR_RED,          'type': ITEM_POTION, 'heal': 30,   'tier': 2},
    'field_rations':  {'name': 'Field Rations',   'glyph': '%', 'color': COLOR_GREEN,        'type': ITEM_FOOD,   'heal': 20,   'tier': 2},
    # Tier 3 - elite
    'battle_axe':     {'name': 'Battle Axe',      'glyph': '/', 'color': COLOR_BRIGHT_RED,   'type': ITEM_WEAPON, 'damage': 8,  'tier': 3},
    'war_hammer':     {'name': 'War Hammer',      'glyph': '/', 'color': COLOR_BRIGHT_WHITE, 'type': ITEM_WEAPON, 'damage': 10, 'tier': 3},
    'plate_cuirass':  {'name': 'Plate Cuirass',   'glyph': '[', 'color': COLOR_BRIGHT_WHITE, 'type': ITEM_ARMOR,  'defense': 8, 'tier': 3},
    'tower_shield':   {'name': 'Tower Shield',    'glyph': '[', 'color': COLOR_BRIGHT_CYAN,  'type': ITEM_ARMOR,  'defense': 7, 'tier': 3},
    'elixir':         {'name': 'Elixir of Life',  'glyph': '!', 'color': COLOR_MAGENTA,      'type': ITEM_POTION, 'heal': 60,   'tier': 3},
    # Tier 4 - legendary
    'commanders_blade': {'name': "Commander's Blade", 'glyph': '/', 'color': COLOR_BRIGHT_YELLOW, 'type': ITEM_WEAPON, 'damage': 14, 'tier': 4},
    'dragon_mail':      {'name': 'Dragon Mail',       'glyph': '[', 'color': COLOR_BRIGHT_RED,    'type': ITEM_ARMOR,  'defense': 12, 'tier': 4},
}


def generate_loot_pool(tier, count=5):
    """Generate a loot selection for the given tier."""
    eligible = [k for k, v in ITEM_TEMPLATES.items() if v['tier'] <= tier]
    # Weight toward current tier
    weights = []
    for k in eligible:
        t = ITEM_TEMPLATES[k]['tier']
        weights.append(3 if t == tier else 1)
    return random.choices(eligible, weights=weights, k=count)


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

class Entity:
    _next_id = 1

    def __init__(self, x, y, glyph, color, name):
        self.id = Entity._next_id
        Entity._next_id += 1
        self.x = x
        self.y = y
        self.glyph = glyph
        self.color = color
        self.name = name
        self.hp = 10
        self.max_hp = 10
        self.strength = 5
        self.defense = 0
        self.alive = True
        self.inventory = []
        self.weapon = None
        self.armor = None

    def take_damage(self, amount):
        actual = max(1, amount)
        self.hp -= actual
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return actual

    def attack_power(self):
        base = self.strength
        if self.weapon:
            base += self.weapon.damage
        return base

    def total_defense(self):
        d = self.defense
        if self.armor:
            d += self.armor.defense
        return d


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

# Weakling starting stats - class gives a tiny edge, real power comes from leveling
CLASS_STATS = {
    CLASS_SWORDSMAN: {'hp': 35, 'str': 4, 'def': 1, 'dex': 4, 'fov': 14},
    CLASS_ARCHER:    {'hp': 28, 'str': 3, 'def': 0, 'dex': 6, 'fov': 18},
    CLASS_KNIGHT:    {'hp': 40, 'str': 4, 'def': 2, 'dex': 3, 'fov': 12},
    CLASS_SCOUT:     {'hp': 25, 'str': 3, 'def': 0, 'dex': 7, 'fov': 20},
    CLASS_PIKEMAN:   {'hp': 38, 'str': 5, 'def': 1, 'dex': 3, 'fov': 14},
}

# -- Random character generation --
_FIRST_NAMES = [
    "Aldric", "Bran", "Cedric", "Donal", "Elara", "Fenn", "Greta", "Hale",
    "Isolde", "Jorin", "Kael", "Lira", "Maren", "Nix", "Orin", "Pell",
    "Rowan", "Senna", "Thane", "Ula", "Voss", "Wren", "Yara", "Zeph",
    "Ash", "Bryn", "Cass", "Dagny", "Egan", "Flint", "Gael", "Holt",
    "Idris", "Joss", "Keir", "Lark", "Moss", "Neve", "Oren", "Pike",
    "Quinn", "Rune", "Sage", "Tarn", "Ursa", "Vale", "Ward", "Xan",
]
_SURNAMES = [
    "the Unlucky", "Halfpenny", "Ashborn", "Dirtfoot", "Noname",
    "the Hungry", "Mudwalker", "Straydog", "Ragpicker", "Bonethin",
    "Copperless", "the Hopeful", "Lastpick", "Gutter", "Shank",
    "the Lost", "Wormwood", "Duskfield", "Three-Fingers", "Oxblood",
    "the Crow", "Ironbelly", "Saltblood", "Haggard", "Coldfoot",
]
_ORIGINS = [
    "a farm burned by raiders", "the slums of a port city",
    "a mining village in the hills", "a monastery that cast you out",
    "a traveling merchant caravan", "a fishing hamlet by the coast",
    "a border town razed in the last war", "a forest hermit's shack",
    "the back alleys of the capital", "a debtors' prison",
]
_REASONS = [
    "You joined the army because it was that or starve.",
    "You enlisted for the signing bonus -- three silver coins.",
    "A recruiting sergeant grabbed you out of a tavern brawl.",
    "You're running from debts you can never repay.",
    "You volunteered. Everyone said you were a fool.",
    "The magistrate gave you a choice: the army or the noose.",
    "Your village was destroyed. You've nothing left to lose.",
    "You followed a friend who enlisted. They didn't survive training.",
    "You forged someone else's papers to get in.",
    "A fortune teller said you'd die a hero. You're not so sure.",
]
_TRAITS = [
    "You flinch at loud noises.", "You can't read.",
    "You talk to yourself when scared.", "You have a bad knee.",
    "You're always hungry.", "You sleep with one eye open.",
    "You whistle tunelessly when nervous.",
    "You carry a dented lucky coin.",
    "You owe money to the wrong people.",
    "You have a scar you don't remember getting.",
]


def generate_random_character():
    """Generate a random name, class, and backstory for a new recruit."""
    rng = random
    name = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_SURNAMES)}"
    soldier_class = rng.choice([CLASS_SWORDSMAN, CLASS_ARCHER, CLASS_KNIGHT, CLASS_SCOUT, CLASS_PIKEMAN])
    origin = rng.choice(_ORIGINS)
    reason = rng.choice(_REASONS)
    trait = rng.choice(_TRAITS)
    backstory = f"You came from {origin}. {reason} {trait}"
    return name, soldier_class, backstory


class Player(Entity):
    def __init__(self, x, y, name, soldier_class=CLASS_SWORDSMAN):
        stats = CLASS_STATS.get(soldier_class, CLASS_STATS[CLASS_SWORDSMAN])
        super().__init__(x, y, '@', COLOR_BRIGHT_WHITE, name)
        self.soldier_class = soldier_class
        self.hp = stats['hp']
        self.max_hp = stats['hp']
        self.strength = stats['str']
        self.defense = stats['def']
        self.dexterity = stats['dex']
        self.level = 1
        self.xp = 0
        self.xp_next = 100
        self.kills = 0
        self.fov_radius = stats['fov']
        self.log = []
        self.visible = set()
        self.explored = set()
        self.term_width = 80
        self.term_height = 24
        self.backstory = ''
        self.ready = False
        self.story_choice = None
        self.army = ARMY_BLUE

    def gain_xp(self, amount):
        self.xp += amount
        while self.xp >= self.xp_next:
            self._level_up()

    def _level_up(self):
        self.level += 1
        self.xp -= self.xp_next
        self.xp_next = int(self.xp_next * 1.5)
        self.max_hp += 8
        self.hp = min(self.hp + 20, self.max_hp)
        self.strength += 1
        self.defense += 1
        self.log.append(f"*** LEVEL UP! You are now level {self.level}! ***")

    def reset_for_battle(self):
        """Prepare for a new battle: heal up, clear transient state."""
        self.hp = self.max_hp
        self.alive = True
        self.visible = set()
        self.explored = set()
        self.log = []


# ---------------------------------------------------------------------------
# Soldier (AI-controlled army unit)
# ---------------------------------------------------------------------------

SOLDIER_TEMPLATES = {
    'militia':    {'glyph': 'm', 'name': 'Militia',    'hp': 15, 'str': 3, 'def': 0, 'speed': 6, 'xp': 3,  'ranged': False, 'range': 0},
    'swordsman':  {'glyph': 'S', 'name': 'Swordsman',  'hp': 25, 'str': 5, 'def': 2, 'speed': 5, 'xp': 8,  'ranged': False, 'range': 0},
    'archer':     {'glyph': 'A', 'name': 'Archer',     'hp': 18, 'str': 6, 'def': 1, 'speed': 5, 'xp': 10, 'ranged': True,  'range': 8},
    'knight':     {'glyph': 'K', 'name': 'Knight',     'hp': 40, 'str': 8, 'def': 5, 'speed': 7, 'xp': 15, 'ranged': False, 'range': 0},
    'pikeman':    {'glyph': 'P', 'name': 'Pikeman',    'hp': 30, 'str': 7, 'def': 3, 'speed': 6, 'xp': 10, 'ranged': False, 'range': 0},
    'scout':      {'glyph': 's', 'name': 'Scout',      'hp': 14, 'str': 4, 'def': 0, 'speed': 3, 'xp': 5,  'ranged': False, 'range': 0},
    'commander':  {'glyph': 'C', 'name': 'Commander',  'hp': 60, 'str': 10,'def': 6, 'speed': 5, 'xp': 50, 'ranged': False, 'range': 0},
    'war_mage':   {'glyph': 'W', 'name': 'War Mage',   'hp': 22, 'str': 12,'def': 1, 'speed': 6, 'xp': 20, 'ranged': True,  'range': 10},
}


class Soldier(Entity):
    def __init__(self, x, y, army, template_key):
        tmpl = SOLDIER_TEMPLATES[template_key]
        color = COLOR_BRIGHT_BLUE if army == ARMY_BLUE else COLOR_BRIGHT_RED
        # Commanders get special color
        if template_key == 'commander':
            color = COLOR_BRIGHT_CYAN if army == ARMY_BLUE else COLOR_BRIGHT_YELLOW
        super().__init__(x, y, tmpl['glyph'], color, tmpl['name'])
        self.army = army
        self.template_key = template_key
        self.hp = tmpl['hp']
        self.max_hp = tmpl['hp']
        self.strength = tmpl['str']
        self.defense = tmpl['def']
        self.speed = tmpl['speed']
        self.xp_value = tmpl['xp']
        self.is_ranged = tmpl['ranged']
        self.attack_range = tmpl['range']
        self.tick_counter = random.randint(0, tmpl['speed'])  # Stagger initial ticks

    def update_ai(self, battle):
        """Run one AI step. Returns True if acted."""
        self.tick_counter += 1
        if self.tick_counter < self.speed:
            return False
        self.tick_counter = 0

        # Find nearest enemy
        target, dist = battle.find_nearest_enemy(self)
        if target is None:
            return False

        # Ranged: shoot if in range and have LOS
        if self.is_ranged and dist <= self.attack_range and dist > 1:
            from server.battlefield import has_line_of_sight
            if has_line_of_sight(battle.battlefield.is_opaque,
                                 self.x, self.y, target.x, target.y):
                battle.ranged_attack(self, target)
                return True

        # Melee: attack if adjacent
        if dist <= 1:
            battle.melee_attack(self, target)
            return True

        # Move toward target
        dx = (1 if target.x > self.x else -1) if target.x != self.x else 0
        dy = (1 if target.y > self.y else -1) if target.y != self.y else 0

        # Try to move, with fallback directions
        for tdx, tdy in [(dx, dy), (dx, 0), (0, dy)]:
            if tdx == 0 and tdy == 0:
                continue
            nx, ny = self.x + tdx, self.y + tdy
            if battle.can_move_to(nx, ny):
                self.x = nx
                self.y = ny
                return True

        return False
