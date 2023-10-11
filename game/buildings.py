import pygame as pg

class Lumbermill:

    def __init__(self, pos, game):
        self.name = "lumbermill"
        self.resource_cooldown = pg.time.get_ticks()
        self.inventory = 0
        self.game = game

    def update(self):
        now = pg.time.get_ticks()
        if now - self.resource_cooldown > 200:
            self.inventory += 1
            self.game.total_resources += 1
            self.resource_cooldown = now


