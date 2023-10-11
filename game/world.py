import random
import noise
from .settings import TILE_SIZE
from .buildings import Lumbermill

class World:
    def __init__(self, entities, grid_length_x, grid_length_y, game):
        self.entities = entities
        self.grid_length_x = grid_length_x
        self.grid_length_y = grid_length_y
        self.game = game

        self.perlin_scale = grid_length_x / 2
        self.world = self.create_world()
        self.collision_matrix = self.create_collision_matrix()

        self.buildings = [[None] * (self.grid_length_x + 1) for _ in range(self.grid_length_y + 1)]
        self.workers = [[None] * self.grid_length_x for _ in range(self.grid_length_y)]

        self.temp_tile = None
        self.examine_tile = None

    def create_building(self, grid_pos, game):
        ent = Lumbermill(self.world[grid_pos[0]][grid_pos[1]]["render_pos"], game)
        tile_data = self.world[grid_pos[0]][grid_pos[1]]
        self.entities.append(ent)
        self.buildings[grid_pos[0]][grid_pos[1]] = ent
        tile_data["collision"] = True
        self.collision_matrix[grid_pos[1]][grid_pos[0]] = 0

    def create_world(self):
        world = [
            [
                self.grid_to_world(grid_x, grid_y) for grid_y in range(self.grid_length_y)
            ]
            for grid_x in range(self.grid_length_x)
        ]
        return world

    def grid_to_world(self, grid_x, grid_y):
        rect = [
            (grid_x * TILE_SIZE, grid_y * TILE_SIZE),
            (grid_x * TILE_SIZE + TILE_SIZE, grid_y * TILE_SIZE),
            (grid_x * TILE_SIZE + TILE_SIZE, grid_y * TILE_SIZE + TILE_SIZE),
            (grid_x * TILE_SIZE, grid_y * TILE_SIZE + TILE_SIZE)
        ]

        iso_poly = [self.cart_to_iso(x, y) for x, y in rect]

        minx = min(x for x, _ in iso_poly)
        miny = min(y for _, y in iso_poly)

        perlin_scale = self.perlin_scale
        perlin = 100 * noise.pnoise2(grid_x / perlin_scale, grid_y / perlin_scale)
        r = random.randint(1, 100)

        if perlin >= 15 or perlin <= -35:
            tree_mapping = {"1": "tree", "2": "tree1", "3": "tree2"}
            tile = tree_mapping.get(str(random.randint(1, 4)), "tree")
        elif r <= 4:
            stone_mapping = {"1": "stone", "2": "stone1", "3": "stone2"}
            tile = stone_mapping.get(str(random.randint(1, 4)), "stone")
        else:
            tile = ""

        out = {
            "grid": [grid_x, grid_y],
            "cart_rect": rect,
            "iso_poly": iso_poly,
            "render_pos": [minx, miny],
            "tile": tile,
            "collision": False if tile == "" else True
        }

        return out

    def create_collision_matrix(self):
        collision_matrix = [[1 for _ in range(self.grid_length_x)] for _ in range(self.grid_length_y)]
        for x in range(self.grid_length_x):
            for y in range(self.grid_length_y):
                collision_matrix[y][x] = 0 if self.world[x][y]["collision"] else 1
        return collision_matrix

    def cart_to_iso(self, x, y):
        iso_x = x - y
        iso_y = (x + y) / 2
        return iso_x, iso_y

