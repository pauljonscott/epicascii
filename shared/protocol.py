"""Shared protocol definitions for EpicAscii battle roguelike."""

# -- Color indices (map to curses color pairs on the client) --
COLOR_BLACK = 0
COLOR_RED = 1
COLOR_GREEN = 2
COLOR_YELLOW = 3
COLOR_BLUE = 4
COLOR_MAGENTA = 5
COLOR_CYAN = 6
COLOR_WHITE = 7
COLOR_DIM = 8
COLOR_BRIGHT_RED = 9
COLOR_BRIGHT_GREEN = 10
COLOR_BRIGHT_YELLOW = 11
COLOR_BRIGHT_BLUE = 12
COLOR_BRIGHT_MAGENTA = 13
COLOR_BRIGHT_CYAN = 14
COLOR_BRIGHT_WHITE = 15

# -- Tile types --
TILE_VOID = 0
TILE_GRASS = 1
TILE_TALL_GRASS = 2
TILE_DIRT = 3
TILE_MUD = 4
TILE_TREE = 5
TILE_ROCK = 6
TILE_HILL = 7
TILE_CREEK = 8
TILE_BRIDGE = 9
TILE_TRENCH = 10
TILE_BARRICADE = 11
TILE_WALL = 12
TILE_FLOOR = 13
TILE_CAMPFIRE = 14
TILE_BLOOD = 15

TILE_INFO = {
    TILE_VOID:      {'glyph': ' ', 'color': COLOR_BLACK,        'walkable': False, 'opaque': True,  'name': 'void'},
    TILE_GRASS:     {'glyph': '.', 'color': COLOR_GREEN,        'walkable': True,  'opaque': False, 'name': 'grass'},
    TILE_TALL_GRASS:{'glyph': '"', 'color': COLOR_GREEN,        'walkable': True,  'opaque': False, 'name': 'tall grass'},
    TILE_DIRT:      {'glyph': '.', 'color': COLOR_YELLOW,       'walkable': True,  'opaque': False, 'name': 'dirt'},
    TILE_MUD:       {'glyph': '~', 'color': COLOR_YELLOW,       'walkable': True,  'opaque': False, 'name': 'mud'},
    TILE_TREE:      {'glyph': 'T', 'color': COLOR_GREEN,        'walkable': False, 'opaque': True,  'name': 'tree'},
    TILE_ROCK:      {'glyph': 'o', 'color': COLOR_WHITE,        'walkable': False, 'opaque': True,  'name': 'boulder'},
    TILE_HILL:      {'glyph': '^', 'color': COLOR_YELLOW,       'walkable': True,  'opaque': False, 'name': 'hill'},
    TILE_CREEK:     {'glyph': '~', 'color': COLOR_CYAN,         'walkable': True,  'opaque': False, 'name': 'creek'},
    TILE_BRIDGE:    {'glyph': '=', 'color': COLOR_WHITE,        'walkable': True,  'opaque': False, 'name': 'bridge'},
    TILE_TRENCH:    {'glyph': '_', 'color': COLOR_YELLOW,       'walkable': True,  'opaque': False, 'name': 'trench'},
    TILE_BARRICADE: {'glyph': '#', 'color': COLOR_YELLOW,       'walkable': False, 'opaque': True,  'name': 'barricade'},
    TILE_WALL:      {'glyph': '#', 'color': COLOR_WHITE,        'walkable': False, 'opaque': True,  'name': 'wall'},
    TILE_FLOOR:     {'glyph': '.', 'color': COLOR_WHITE,        'walkable': True,  'opaque': False, 'name': 'floor'},
    TILE_CAMPFIRE:  {'glyph': '*', 'color': COLOR_BRIGHT_RED,   'walkable': False, 'opaque': False, 'name': 'campfire'},
    TILE_BLOOD:     {'glyph': '.', 'color': COLOR_RED,          'walkable': True,  'opaque': False, 'name': 'blood'},
}

# -- Battlefield --
BATTLE_WIDTH = 120
BATTLE_HEIGHT = 50

# -- Game phases --
PHASE_CHARACTER_CREATE = 'create'
PHASE_STORY = 'story'
PHASE_BATTLE = 'battle'
PHASE_LOOT = 'loot'

# -- Armies --
ARMY_BLUE = 0
ARMY_RED = 1

# -- Soldier classes --
CLASS_SWORDSMAN = 'swordsman'
CLASS_ARCHER = 'archer'
CLASS_KNIGHT = 'knight'
CLASS_SCOUT = 'scout'
CLASS_PIKEMAN = 'pikeman'

SOLDIER_CLASSES = {
    CLASS_SWORDSMAN: {'name': 'Swordsman', 'desc': 'Balanced fighter. Reliable in the line.'},
    CLASS_ARCHER:    {'name': 'Archer',    'desc': 'Ranged attacks. Deadly before melee.'},
    CLASS_KNIGHT:    {'name': 'Knight',    'desc': 'Heavy armor. Slow but hard to kill.'},
    CLASS_SCOUT:     {'name': 'Scout',     'desc': 'Fast and light. Flanks the enemy.'},
    CLASS_PIKEMAN:   {'name': 'Pikeman',   'desc': 'Long reach. Strong on defense.'},
}

# -- Game constants --
DEFAULT_FOV_RADIUS = 14
SERVER_TICK_RATE = 10
DEFAULT_PORT = 8765

# -- Item types --
ITEM_WEAPON = 'weapon'
ITEM_ARMOR = 'armor'
ITEM_POTION = 'potion'
ITEM_FOOD = 'food'
