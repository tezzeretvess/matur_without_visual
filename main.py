import pygame as pg
from game.game import Game
import sys
import winsound

def main():
    pg.init()
    pg.mixer.init()

    give_worker_count = 20
    steal_worker_count = 0

    screen = pg.display.set_mode((0, 0), pg.FULLSCREEN)
    clock = pg.time.Clock()

    game = Game(screen, clock, give_worker_count, steal_worker_count)

    running = True
    playing = True

    while running:
        # Create a new game with the current give_worker_count
        screen = pg.display.set_mode((0, 0), pg.FULLSCREEN)
        clock = pg.time.Clock()
        game = Game(screen, clock, give_worker_count, steal_worker_count)

        print("Start")
        playing = True
        while playing:
            game.run()
            playing = game.playing
        # The game has ended, reduce give_worker_count by 1
        give_worker_count -= 1
        steal_worker_count += 1
        print("Simulations left: " + str(give_worker_count) + " Good Worker: " + str(give_worker_count) + " Bad Worker: " + str(steal_worker_count))
        # Check if the game should continue with a lower give_worker_count
        if give_worker_count < 10 or steal_worker_count > 20:
            winsound.Beep(1000, 300)
            winsound.Beep(400, 1000)
            print("Simulation finished")
            running = False
            pg.quit()
            sys.exit()

    



if __name__ == "__main__":
    main()



