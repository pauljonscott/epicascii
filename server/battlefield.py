"""Battlefield generation and field of view for EpicAscii."""

import random

from shared.protocol import (
    TILE_VOID, TILE_GRASS, TILE_TALL_GRASS, TILE_DIRT, TILE_MUD,
    TILE_TREE, TILE_ROCK, TILE_HILL, TILE_CREEK, TILE_BRIDGE,
    TILE_TRENCH, TILE_BARRICADE, TILE_WALL, TILE_CAMPFIRE, TILE_BLOOD,
    TILE_INFO, BATTLE_WIDTH, BATTLE_HEIGHT,
)

# ---------------------------------------------------------------------------
# Shadow-casting FOV (carried over)
# ---------------------------------------------------------------------------

_FOV_MULT = [
    [1,  0,  0, -1, -1,  0,  0,  1],
    [0,  1, -1,  0,  0, -1,  1,  0],
    [0,  1,  1,  0,  0, -1, -1,  0],
    [1,  0,  0,  1, -1,  0,  0, -1],
]


def compute_fov(is_opaque_fn, ox, oy, radius):
    visible = {(ox, oy)}
    for octant in range(8):
        _cast_light(
            is_opaque_fn, visible, ox, oy, radius, 1, 1.0, 0.0,
            _FOV_MULT[0][octant], _FOV_MULT[1][octant],
            _FOV_MULT[2][octant], _FOV_MULT[3][octant],
        )
    return visible


def _cast_light(is_opaque_fn, visible, ox, oy, radius, row, start, end, xx, xy, yx, yy):
    if start < end:
        return
    radius_sq = radius * radius
    new_start = 0.0
    for j in range(row, radius + 1):
        dx, dy = -j - 1, -j
        blocked = False
        while dx <= 0:
            dx += 1
            mx = ox + dx * xx + dy * xy
            my = oy + dx * yx + dy * yy
            l_slope = (dx - 0.5) / (dy + 0.5)
            r_slope = (dx + 0.5) / (dy - 0.5)
            if start < r_slope:
                continue
            elif end > l_slope:
                break
            if dx * dx + dy * dy < radius_sq:
                visible.add((mx, my))
            if blocked:
                if is_opaque_fn(mx, my):
                    new_start = r_slope
                    continue
                else:
                    blocked = False
                    start = new_start
            elif is_opaque_fn(mx, my) and j < radius:
                blocked = True
                _cast_light(is_opaque_fn, visible, ox, oy, radius,
                            j + 1, start, l_slope, xx, xy, yx, yy)
                new_start = r_slope
        if blocked:
            break


def has_line_of_sight(is_opaque_fn, x0, y0, x1, y1):
    """Bresenham line-of-sight check (for ranged attacks)."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    cx, cy = x0, y0
    while True:
        if cx == x1 and cy == y1:
            return True
        if (cx, cy) != (x0, y0) and is_opaque_fn(cx, cy):
            return False
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            cx += sx
        if e2 < dx:
            err += dx
            cy += sy


# ---------------------------------------------------------------------------
# Battlefield
# ---------------------------------------------------------------------------

TERRAIN_PRESETS = {
    'open_plains': {
        'tree_density': 0.01,
        'rock_density': 0.005,
        'has_creek': False,
        'has_trenches': False,
        'hill_clusters': 2,
    },
    'forest_edge': {
        'tree_density': 0.08,
        'rock_density': 0.01,
        'has_creek': False,
        'has_trenches': False,
        'hill_clusters': 1,
    },
    'river_crossing': {
        'tree_density': 0.03,
        'rock_density': 0.005,
        'has_creek': True,
        'has_trenches': False,
        'hill_clusters': 1,
    },
    'fortified_camp': {
        'tree_density': 0.02,
        'rock_density': 0.01,
        'has_creek': False,
        'has_trenches': True,
        'hill_clusters': 0,
    },
    'hill_assault': {
        'tree_density': 0.03,
        'rock_density': 0.02,
        'has_creek': False,
        'has_trenches': True,
        'hill_clusters': 4,
    },
    'ambush': {
        'tree_density': 0.12,
        'rock_density': 0.02,
        'has_creek': False,
        'has_trenches': False,
        'hill_clusters': 0,
    },
}


class Battlefield:
    def __init__(self, terrain_type='open_plains', seed=None):
        self.width = BATTLE_WIDTH
        self.height = BATTLE_HEIGHT
        self.seed = seed if seed is not None else random.randint(0, 999_999)
        self.tiles = [[TILE_GRASS] * self.width for _ in range(self.height)]
        self._generate(terrain_type)

    def in_bounds(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def get_tile_type(self, x, y):
        if not self.in_bounds(x, y):
            return TILE_VOID
        return self.tiles[y][x]

    def set_tile(self, x, y, tile):
        if self.in_bounds(x, y):
            self.tiles[y][x] = tile

    def is_walkable(self, x, y):
        if not self.in_bounds(x, y):
            return False
        return TILE_INFO[self.tiles[y][x]]['walkable']

    def is_opaque(self, x, y):
        if not self.in_bounds(x, y):
            return True
        return TILE_INFO[self.tiles[y][x]]['opaque']

    def _generate(self, terrain_type):
        rng = random.Random(self.seed)
        preset = TERRAIN_PRESETS.get(terrain_type, TERRAIN_PRESETS['open_plains'])

        # Base terrain: mostly grass with some dirt patches
        for y in range(self.height):
            for x in range(self.width):
                if rng.random() < 0.15:
                    self.tiles[y][x] = TILE_DIRT
                elif rng.random() < 0.08:
                    self.tiles[y][x] = TILE_TALL_GRASS

        # Trees
        for y in range(self.height):
            for x in range(self.width):
                if rng.random() < preset['tree_density']:
                    # Trees tend to cluster
                    self.tiles[y][x] = TILE_TREE
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = x + dx, y + dy
                        if self.in_bounds(nx, ny) and rng.random() < 0.4:
                            self.tiles[ny][nx] = TILE_TREE

        # Rocks
        for y in range(self.height):
            for x in range(self.width):
                if self.tiles[y][x] == TILE_GRASS and rng.random() < preset['rock_density']:
                    self.tiles[y][x] = TILE_ROCK

        # Hill clusters
        for _ in range(preset['hill_clusters']):
            cx = rng.randint(20, self.width - 20)
            cy = rng.randint(10, self.height - 10)
            radius = rng.randint(4, 8)
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if dx * dx + dy * dy <= radius * radius:
                        nx, ny = cx + dx, cy + dy
                        if self.in_bounds(nx, ny) and self.tiles[ny][nx] in (TILE_GRASS, TILE_DIRT, TILE_TALL_GRASS):
                            self.tiles[ny][nx] = TILE_HILL

        # Creek running vertically through the middle
        if preset['has_creek']:
            cx = self.width // 2 + rng.randint(-5, 5)
            bridge_y = self.height // 2 + rng.randint(-5, 5)
            for y in range(self.height):
                wobble = rng.randint(-1, 1)
                for dx in range(-1, 2):
                    nx = cx + wobble + dx
                    if self.in_bounds(nx, y):
                        if abs(y - bridge_y) <= 1:
                            self.tiles[y][nx] = TILE_BRIDGE
                        else:
                            self.tiles[y][nx] = TILE_CREEK

        # Trenches (horizontal, in the middle third)
        if preset['has_trenches']:
            ty = self.height // 2 + rng.randint(-3, 3)
            for x in range(10, self.width - 10):
                if rng.random() < 0.7:
                    self.tiles[ty][x] = TILE_TRENCH
            # Barricades behind trench
            for x in range(10, self.width - 10):
                if rng.random() < 0.3 and self.tiles[ty - 2][x] not in (TILE_TREE, TILE_ROCK):
                    self.tiles[ty - 2][x] = TILE_BARRICADE

        # Clear spawn zones (left 15 cols for blue, right 15 for red)
        for y in range(2, self.height - 2):
            for x in range(2, 15):
                if self.tiles[y][x] in (TILE_TREE, TILE_ROCK, TILE_BARRICADE):
                    self.tiles[y][x] = TILE_GRASS
            for x in range(self.width - 15, self.width - 2):
                if self.tiles[y][x] in (TILE_TREE, TILE_ROCK, TILE_BARRICADE):
                    self.tiles[y][x] = TILE_GRASS

    def get_blue_spawn_positions(self, count):
        """Return spawn positions on the left side."""
        positions = []
        mid_y = self.height // 2
        for dist in range(self.height // 2):
            for dy in ([0] if dist == 0 else [dist, -dist]):
                y = mid_y + dy
                for x in range(3, 14):
                    if self.is_walkable(x, y) and (x, y) not in positions:
                        positions.append((x, y))
                        if len(positions) >= count:
                            return positions
        return positions

    def get_red_spawn_positions(self, count):
        """Return spawn positions on the right side."""
        positions = []
        mid_y = self.height // 2
        for dist in range(self.height // 2):
            for dy in ([0] if dist == 0 else [dist, -dist]):
                y = mid_y + dy
                for x in range(self.width - 14, self.width - 3):
                    if self.is_walkable(x, y) and (x, y) not in positions:
                        positions.append((x, y))
                        if len(positions) >= count:
                            return positions
        return positions
