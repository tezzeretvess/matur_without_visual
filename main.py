import pygame as pg
from game.game import Game

def main():
    pg.init()
    pg.mixer.init()
    screen = pg.display.set_mode((0, 0), pg.FULLSCREEN)
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


# TODO
# - Build Logic to decide which behaviour should be done
# - Why interactions need changing although parameters should be changing?!
# - Needs
# - Optimize remove debug 
# - Change need calulation so that it will look at how much they gain more and then consider doing something 
# 
# DONE
# - Make the trees smaller