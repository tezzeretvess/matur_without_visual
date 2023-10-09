import pygame as pg
import sys
from .world import World
from .settings import TILE_SIZE
from .utils import draw_text
from .camera import Camera
from .hud import Hud
from .resource_manager import ResourceManager
from .workers import Worker
import random


class Game:

    def __init__(self, screen, clock):
        self.screen = screen
        self.clock = clock
        self.width, self.height = self.screen.get_size()

        # entities
        self.entities = []

        # resource manager
        self.resource_manager = ResourceManager()
        self.total_resources = 0

        # hud
        self.hud = Hud(self.total_resources, self.width, self.height)

        # world
        self.world = World(self.entities, self.hud, 50, 50, self.width, self.height)
        for _ in range(7):
            self.create_random_lumbermill()
        for _ in range(1):
            Worker(self.world.world[25][25], self.world)

        
        

        # camera
        self.camera = Camera(self.width, self.height)

    def run(self):
        self.playing = True
        while self.playing:
            self.clock.tick(60)
            self.handle_events()
            self.update()
            self.draw()

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit_game()
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.quit_game()

    def quit_game(self):
        pg.quit()
        sys.exit()

    def update(self):
        self.camera.update()
    
        for entity in self.entities:
            entity.update()

        self.hud.update()
        self.world.update(self.camera)
        self.hud.total_resources = self.total_resources

    def draw(self):
        self.screen.fill((0, 0, 0))
        self.world.draw(self.screen, self.camera)
        self.hud.draw(self.screen)
        draw_text(self.screen, f'fps={round(self.clock.get_fps())}', 25, (255, 255, 255), (10, 10))
        pg.display.flip()
    
    # creates buildings randomly in the world
    def create_random_lumbermill(self):
        while True:
            # Randomly choose a grid position
            x = random.randint(0, self.world.grid_length_x - 1)
            y = random.randint(0, self.world.grid_length_y - 1)

            # Check if the chosen position is suitable (not in collision and not too close to existing buildings)
            if (
                not self.world.world[x][y]["collision"]
                and self.is_far_from_existing_buildings(x, y, min_distance=5)
            ):
                # Create the Lumbermill at the chosen position
                self.world.create_building((x, y), "lumbermill", self)
                break

    def is_far_from_existing_buildings(self, x, y, min_distance):
        for i in range(self.world.grid_length_x):
            for j in range(self.world.grid_length_y):
                if self.world.buildings[i][j] and self.distance(x, y, i, j) < min_distance:
                    return False
        return True

    def distance(self, x1, y1, x2, y2):
        # Calculate the Euclidean distance between two grid positions
        return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
