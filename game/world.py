import pygame as pg
import random
import noise
from .settings import TILE_SIZE
from .buildings import Lumbermill,Stonemasonry


class World:

    def __init__(self, resource_manager, entities, hud, grid_length_x, grid_length_y, width, height):
        self.resource_manager = resource_manager
        self.entities = entities
        self.hud = hud
        self.grid_length_x = grid_length_x
        self.grid_length_y = grid_length_y
        self.width = width
        self.height = height

        self.perlin_scale = grid_length_x / 2

        tile_width = grid_length_x * TILE_SIZE * 2
        tile_height = grid_length_y * TILE_SIZE + 2 * TILE_SIZE
        self.grass_tiles = pg.Surface((tile_width, tile_height)).convert_alpha()
        self.tiles = self.load_images()
        self.world = self.create_world()
        self.collision_matrix = self.create_collision_matrix()

        self.buildings = [[None] * (self.grid_length_x + 1) for _ in range(self.grid_length_y + 1)]
        self.workers = [[None] * self.grid_length_x for _ in range(self.grid_length_y)]

        self.temp_tile = None
        self.examine_tile = None


    def update(self, camera):
        mouse_pos = pg.mouse.get_pos()
        mouse_action = pg.mouse.get_pressed()

        if mouse_action[2]:
            self.examine_tile = None
            self.hud.examined_tile = None

        self.temp_tile = None

        selected_tile = self.hud.selected_tile

        grid_pos = self.mouse_to_grid(mouse_pos[0], mouse_pos[1], camera.scroll)

        if self.can_place_tile(grid_pos):
            if selected_tile is not None:
                img = selected_tile["image"].copy()
                img.set_alpha(100)

                tile_data = self.world[grid_pos[0]][grid_pos[1]]

                self.temp_tile = {
                    "image": img,
                    "render_pos": tile_data["render_pos"],
                    "iso_poly": tile_data["iso_poly"],
                    "collision": tile_data["collision"]
                }

                if mouse_action[0] and not tile_data["collision"]:
                    if selected_tile["name"] == "lumbermill":
                        ent = Lumbermill(tile_data["render_pos"], self.resource_manager)
                    elif selected_tile["name"] == "stonemasonry":
                        ent = Stonemasonry(tile_data["render_pos"], self.resource_manager)

                    self.entities.append(ent)
                    self.buildings[grid_pos[0]][grid_pos[1]] = ent
                    tile_data["collision"] = True
                    self.collision_matrix[grid_pos[1]][grid_pos[0]] = 0
                    self.hud.selected_tile = None
            else:
                building = self.buildings[grid_pos[0]][grid_pos[1]]
                if mouse_action[0] and building is not None:
                    self.examine_tile = grid_pos
                    self.hud.examined_tile = building


    def draw(self, screen, camera):
        screen.blit(self.grass_tiles, (camera.scroll.x, camera.scroll.y))

        for x in range(self.grid_length_x):
            for y in range(self.grid_length_y):
                render_pos = self.world[x][y]["render_pos"]
                tile_data = self.world[x][y]

                # Draw world tiles
                tile = tile_data["tile"]
                if tile:
                    tile_image = self.tiles[tile]
                    tile_offset = self.grass_tiles.get_width() / 2
                    tile_position = (
                        render_pos[0] + tile_offset + camera.scroll.x,
                        render_pos[1] - (tile_image.get_height() - TILE_SIZE) + camera.scroll.y
                    )
                    screen.blit(tile_image, tile_position)

                # Draw buildings
                building = self.buildings[x][y]
                if building:
                    building_image = building.image
                    building_offset = self.grass_tiles.get_width() / 2
                    building_position = (
                        render_pos[0] + building_offset + camera.scroll.x,
                        render_pos[1] - (building_image.get_height() - TILE_SIZE) + camera.scroll.y
                    )
                    screen.blit(building_image, building_position)

                    if self.examine_tile == (x, y):
                        building_mask = pg.mask.from_surface(building_image).outline()
                        building_mask = [
                            (
                                x + render_pos[0] + building_offset + camera.scroll.x,
                                y + render_pos[1] - (building_image.get_height() - TILE_SIZE) + camera.scroll.y
                            )
                            for x, y in building_mask
                        ]
                        pg.draw.polygon(screen, (255, 255, 255), building_mask, 3)

                # Draw workers
                worker = self.workers[x][y]
                if worker:
                    worker_image = worker.image
                    worker_offset = self.grass_tiles.get_width() / 2
                    worker_position = (
                        render_pos[0] + worker_offset + camera.scroll.x,
                        render_pos[1] - (worker_image.get_height() - TILE_SIZE) + camera.scroll.y
                    )
                    screen.blit(worker_image, worker_position)

        if self.temp_tile:
            iso_poly = [
                (x + self.grass_tiles.get_width() / 2 + camera.scroll.x, y + camera.scroll.y)
                for x, y in self.temp_tile["iso_poly"]
            ]
            if self.temp_tile["collision"]:
                pg.draw.polygon(screen, (255, 0, 0), iso_poly, 3)
            else:
                pg.draw.polygon(screen, (255, 255, 255), iso_poly, 3)
            render_pos = self.temp_tile["render_pos"]
            temp_image = self.temp_tile["image"]
            temp_offset = self.grass_tiles.get_width() / 2
            temp_position = (
                render_pos[0] + temp_offset + camera.scroll.x,
                render_pos[1] - (temp_image.get_height() - TILE_SIZE) + camera.scroll.y
            )
            screen.blit(temp_image, temp_position)


    def create_world(self):
        world = [
            [
                self.grid_to_world(grid_x, grid_y) for grid_y in range(self.grid_length_y)
            ]
            for grid_x in range(self.grid_length_x)
        ]

        for grid_x, row in enumerate(world):
            for grid_y, world_tile in enumerate(row):
                render_pos = world_tile["render_pos"]
                self.grass_tiles.blit(self.tiles["block"], (render_pos[0] + self.grass_tiles.get_width() / 2, render_pos[1]))

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

    def mouse_to_grid(self, x, y, scroll):
        # transform to world position (removing camera scroll and offset)
        world_x = x - scroll.x - self.grass_tiles.get_width() / 2
        world_y = y - scroll.y
        # transform to cart (inverse of iso)
        cart_y = (2 * world_y - world_x) / 2
        cart_x = cart_y + world_x
        # transform to grid coordinates
        grid_x = int(cart_x // TILE_SIZE)
        grid_y = int(cart_y // TILE_SIZE)
        return grid_x, grid_y

    def load_images(self):
        scaling_factor = 0.75 # Scale factor for assets
        image_files = {
            "building1": "assets/graphics/building01.png",
            "building2": "assets/graphics/building02.png",
            "tree": "assets/graphics/tree.png",
            "tree1": "assets/graphics/tree1.png",
            "tree2": "assets/graphics/tree2.png",
            "stone": "assets/graphics/stone.png",
            "stone1": "assets/graphics/stone1.png",
            "stone2": "assets/graphics/stone2.png",
            "block": "assets/graphics/block.png"
        }
        images = {}
        for name, file_path in image_files.items():
            image = pg.image.load(file_path).convert_alpha()
            if(name == "block"):
                images[name]=image
            else:
                scaled_image = self.scale_image(image, w=image.get_width() * scaling_factor, h=image.get_height() * scaling_factor)
                images[name] = scaled_image
        return images

    def can_place_tile(self, grid_pos):
        mouse_pos = pg.mouse.get_pos()
        mouse_on_panel = any(rect.collidepoint(mouse_pos) for rect in [self.hud.resources_rect, self.hud.build_rect, self.hud.select_rect])
        world_bounds = (0 <= grid_pos[0] < self.grid_length_x) and (0 <= grid_pos[1] < self.grid_length_y)
        return world_bounds and not mouse_on_panel

    def scale_image(self, image, w=None, h=None):
        if w is None and h is None:
            return image

        original_width, original_height = image.get_size()

        if w is not None and h is None:
            scale = w / original_width
            h = scale * original_height
        elif h is not None and w is None:
            scale = h / original_height
            w = scale * original_width

        image = pg.transform.scale(image, (int(w), int(h)))
        return image
