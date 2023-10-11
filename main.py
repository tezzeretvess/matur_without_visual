import pygame as pg
from game.game import Game

def main():
    pg.init()
    pg.mixer.init()

    give_worker_count = 20
    steal_worker_count = 20 - give_worker_count

    screen = pg.display.set_mode((0, 0), pg.FULLSCREEN, give_worker_count, steal_worker_count)
    clock = pg.time.Clock()

    game = Game(screen, clock)

    running = True
    playing = True

    while running:

        while playing:
            game.run()


    pg.quit()

if __name__ == "__main__":
    main()



