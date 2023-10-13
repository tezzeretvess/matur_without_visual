import pygame as pg
import sys
from .world import World
from .settings import TILE_SIZE
from .utils import draw_text
from .workers import Worker
import random
import pandas as pd
import os
import datetime
import winsound


class Game:

    def __init__(self, screen, clock, give_worker_count, steal_worker_count):
        self.screen = screen
        self.clock = clock
        self.width, self.height = self.screen.get_size()
        self.start_time = pg.time.get_ticks()
        self.end_time = 1*(1000*60)  # minutes to ms
        save_directory = r'C:\Users\js200\OneDrive\Dokumente\Matur\DATA\Control\Balanced'
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.excel_filename = os.path.join(save_directory, f'game_data_{timestamp}.xlsx')
        self.last_min_value = 0

        # Controls
        self.GIVING_WORKER_COUNT = give_worker_count
        self.STEALING_WORKER_COUNT = steal_worker_count
        self.BUILDING_COUNT = 20
        self.WORLD_SIZE = 100
        self.export_items_count = 600

        # entities
        self.entities = []

        # resource manager
        self.total_resources = 0

        # world
        self.world = World(self.entities, self.WORLD_SIZE,
                           self.WORLD_SIZE, self)
        for _ in range(self.BUILDING_COUNT):
            self.create_random_lumbermill()
        for _ in range(self.GIVING_WORKER_COUNT):
            Worker(self.world.world[25][25], self.world, 1, "GW" + str(_))
        for _ in range(self.STEALING_WORKER_COUNT):
            Worker(self.world.world[25][25], self.world, -1,
                   "BW" + str(self.GIVING_WORKER_COUNT + _))

    def run(self):
        self.playing = True
        while self.playing:
            self.clock.tick(60)
            self.handle_events()
            self.update()
            self.draw()

    def handle_events(self):
        """
        #now = pg.time.get_ticks()
        if self.worker_has_inventory_count(): #now - self.start_time >= self.end_time
            self.quit_game()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit_game()
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.quit_game()
                    """
        if self.worker_has_inventory_count():  # Check if the game should end
            self.quit_game()
            self.playing = False


        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()

    def quit_game(self):
        self.export_data_to_excel()
        print("FINISHED " + str((pg.time.get_ticks() - self.start_time) / 1000) + " seconds")
        winsound.Beep(500, 1000)
        #pg.quit()
        #sys.exit()

    def export_data_to_excel(self):
        # Create a single Excel writer to manage the file
        with pd.ExcelWriter(self.excel_filename, engine='xlsxwriter') as writer:
            data = []

            for entity in self.entities:
                if isinstance(entity, Worker):
                    data.append([
                        entity.id,
                        entity.character_value,
                        entity.building_looted_all_time,
                        entity.interaction_count_all_time,
                        entity.interaction_transfer_all_time,
                        entity.step_counter,
                        entity.export_inventory,  # Modified to use the adjusted inventory_values
                        entity.export_interaction_with_time,
                        entity.export_interaction_transfers_with_time
                    ])

            self.export_sheet_data(writer, "game_data", [
                ["ID", "Character value", "Building looted", "Interaction count", "Interaction transfer",
                    "Step counter", "Inventory", "Interactions with timer", "Interactions transfers with timer"]
            ] + data)

            self.export_sheet_data(writer, "general_game_data", [
                ["Total Worker", "Nice worker", "Bad worker", "Total building",
                    "Total resources produced", "Duration", "World size"],
                [self.GIVING_WORKER_COUNT + self.STEALING_WORKER_COUNT, self.GIVING_WORKER_COUNT, self.STEALING_WORKER_COUNT,
                    self.BUILDING_COUNT, self.total_resources, self.end_time / 1000, self.WORLD_SIZE]
            ])

            data = []
            for entity in self.entities:
                if isinstance(entity, Worker):

                    inventory_values = entity.export_inventory

                    # Ensure inventory_values has exactly 32 items, padding with the last item
                    while len(inventory_values) < self.export_items_count:
                        inventory_values.append(inventory_values[-1])

                    inventory_values = inventory_values[:self.export_items_count]

                    row_data = [entity.id]
                    row_data.extend(["Inventory"])
                    row_data.extend(inventory_values)
                    data.append(row_data)

            
            self.export_sheet_data(writer, "inventory_data", [
                ["ID", "Inventory"] +
                [i+1 for i in range(len(inventory_values))]
            ] + data)

            data = []
            for entity in self.entities:
                if isinstance(entity, Worker):
                    interaction_values = entity.export_interaction_with_time
                    while len(interaction_values) < self.export_items_count:
                        interaction_values.append(interaction_values[-1])
                    interaction_values = interaction_values[:self.export_items_count]
                    row_data = [entity.id]
                    row_data.extend(["Interactions"])
                    row_data.extend(interaction_values)
                    data.append(row_data)

            self.export_sheet_data(writer, "interactions_with_time_data", [
                ["ID", "Interactions"] +
                [i+1 for i in range(len(interaction_values))]
            ] + data)

            data = []
            for entity in self.entities:
                if isinstance(entity, Worker):
                    interaction_transfer_values = entity.export_interaction_transfers_with_time
                    while len(interaction_transfer_values) < self.export_items_count:
                        interaction_transfer_values.append(interaction_transfer_values[-1])
                    interaction_transfer_values = interaction_transfer_values[:self.export_items_count]
                    row_data = [entity.id]
                    row_data.extend(["Interaction transfer amounts"])
                    row_data.extend(interaction_transfer_values)
                    data.append(row_data)

            self.export_sheet_data(writer, "interaction_transfer_data", [
                ["ID", "Interaction transfer amounts"] +
                [i+1 for i in range(len(interaction_transfer_values))]
            ] + data)

            data = []
            for entity in self.entities:
                if isinstance(entity, Worker):
                    step_values = entity.export_steps_with_time
                    while len(step_values) < self.export_items_count:
                        step_values.append(step_values[-1])
                    step_values = step_values[:self.export_items_count]
                    row_data = [entity.id]
                    row_data.extend(["Steps with time"])
                    row_data.extend(step_values)
                    data.append(row_data)

            self.export_sheet_data(writer, "Steps with time", [
                ["ID", "Steps with time"] +
                [i+1 for i in range(len(step_values))]
            ] + data)


    def export_sheet_data(self, writer, sheet_name, data):
        df = pd.DataFrame(data[1:], columns=data[0])
        df.to_excel(writer, sheet_name=sheet_name, index=False)

    def update(self):

        for entity in self.entities:
            entity.update()

    def draw(self):
        self.screen.fill((0, 0, 0))
        draw_text(
            self.screen, f'fps={round(self.clock.get_fps())}', 25, (255, 255, 255), (10, 10))
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
                self.world.create_building((x, y), self)
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

    def worker_has_inventory_count(self):
        inventory_lengths = []  # Initialize a list to store the lengths
        inventory_values = []  # Initialize a list to store the flattened inventory values

        for entity in self.entities:
            if isinstance(entity, Worker):
                inventory = entity.export_inventory
                inventory_values.extend(inventory)  # Flatten the inventory values
                inventory_lengths.append(len(inventory))  # Store the length

        if not inventory_values:
            # Handle the case where there are no valid inventory values
            return False

        min_value = min(inventory_lengths)

        if min_value >= self.export_items_count:
            progress_percentage = (min_value / self.export_items_count) * 100
            print(f"Progress: {progress_percentage}")
            return True


        if min_value % 10 == 0 and not min_value == self.last_min_value:
            progress_percentage = round((min_value / self.export_items_count) * 100)
            self.last_min_value = min_value
            print(f"Progress: {progress_percentage}%")

        return False

        
