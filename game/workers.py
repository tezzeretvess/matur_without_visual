import pygame as pg
import random
from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
import numpy as np
import time


class Worker:

    def __init__(self, tile, world, character, id):
        self.world = world
        self.world.entities.append(self)
        self.name = "worker"
        self.inventory = 0

        # Timer
        self.update_timer = pg.time.get_ticks()
        self.update_timer_decay = pg.time.get_ticks()
        self.move_timer = pg.time.get_ticks()
        self.data_gather_timer = pg.time.get_ticks()


        self.tile = tile
        self.world.workers[tile["grid"][0]][tile["grid"][1]] = self

        # Status variables
        self.is_moving = True
        self.moving_number = 0
        self.is_interacting = False
        self.is_being_interacted = False

        # Counter
        self.interaction_count = 0
        self.interaction_count_limit = 5
        self.building_looted_count = 0
        self.building_looted_count_limit = 3

        # Export

        self.id = id
        self.character_value = character  # -1 stealing / 1 giving
        self.building_looted_all_time = 0
        self.interaction_count_all_time = 0
        self.interaction_count_with_timer = 0
        self.interaction_transfer = 0
        self.interaction_transfer_all_time = 0
        self.step_counter = 0
        self.step_counter_with_timer = 0
        self.export_inventory = []
        self.export_interaction_with_time = []
        self.export_interaction_transfers_with_time = []
        self.export_steps_with_time = []

        # Need variabeles
        self.need_gather = 0  # control gather behavior
        self.need_steal = 0  # control steal behavior
        self.need_give = 0  # control give behavior
        self.need_interaction = 0  # control interaction behavior

        # Pathfinding
        self.heading = None

        # Other
        self.optimal_building_pos = None
        self.highest_inventory_building_pos = None
        self.last_looted_building = None
        self.optimal_worker_give_pos = None
        self.last_worker_interacted = None
        self.optimal_worker_steal_pos = None
        self.interacting_behaviour = 0
        self.target_worker = None

        self.create_path()

    # Find positions of entities and other utilities

    def find_buildings_positions(self):
        building_positions = [(i, j) for i, row in enumerate(
            self.world.buildings) for j, building in enumerate(row) if building is not None]

        if not building_positions:
            return None

        return building_positions

    def find_distance_buildings(self):
        building_positions = self.find_buildings_positions()
        worker_pos = self.tile["grid"]

        if not building_positions:
            return None, None

        dist_to_all = [pg.math.Vector2(worker_pos).distance_to(
            building_pos) for building_pos in building_positions]
        min_distance = min(dist_to_all)
        min_index = dist_to_all.index(min_distance)
        nearest_building_position = building_positions[min_index]
        return nearest_building_position, dist_to_all

    def find_people_pos(self):
        people_positions = [(i, j) for i, row in enumerate(
            self.world.workers) for j, person in enumerate(row) if person is not None]
        return people_positions

    def find_people_distance(self):
        people_positions = self.find_people_pos()
        worker_pos = self.tile["grid"]

        if not people_positions:
            return None, None

        dist_to_all = [pg.math.Vector2(worker_pos).distance_to(
            person_pos) for person_pos in people_positions]
        min_index = dist_to_all.index(min(dist_to_all))
        nearest_person_position = people_positions[min_index]
        return people_positions, nearest_person_position, dist_to_all

    def get_worker_at_nearest_position(self):
        all_people_pos, nearest_person_pos, all_dist = self.find_people_distance()
        x, y = nearest_person_pos
        if 0 <= x < len(self.world.workers) and 0 <= y < len(self.world.workers[x]):
            return self.world.workers[x][y]
        return None

    def get_position_of_worker(self, worker):
        if worker is not None:
            return worker.tile["grid"]
        return None

    def get_nearest_worker(self):
        all_people_pos, _, all_dist = self.find_people_distance()
        if all_people_pos:
            # Filter out the worker's own position and sort by distance
            distances = [(dist, person_pos) for dist, person_pos in zip(
                all_dist, all_people_pos) if person_pos != self.tile["grid"]]
            distances.sort()  # Sort by distance
            if distances:
                _, nearest_person_position = distances[0]
                x, y = nearest_person_position
                return self.world.workers[x][y]
        return None

    def util_return(self):  # Returns Inventory/Distance of Building and Worker
        nearest_building_position, dist_to_all_buildings = self.find_distance_buildings()
        people_positions, nearest_person_position, dist_to_all_persons = self.find_people_distance()
        worker = self.get_worker_at_nearest_position()

        if nearest_building_position is None:
            building = None
        else:
            x, y = nearest_building_position
            building = self.world.buildings[x][y]

        return nearest_building_position, dist_to_all_buildings, people_positions, nearest_person_position, dist_to_all_persons, worker, building

    # calculates distance from itself to and object
    def calculate_distance_to(self, target_position):
        return pg.math.Vector2(self.tile["grid"]).distance_to(pg.math.Vector2(target_position))

    def find_valid_spot_around_destination(self, destination, radius=1):
        dest_x, dest_y = destination

        for x in range(dest_x - radius, dest_x + radius + 1):
            for y in range(dest_y - radius, dest_y + radius + 1):
                if (
                    0 <= x < len(self.world.world)
                    and 0 <= y < len(self.world.world[0])
                    and not self.world.world[x][y]["collision"]
                    and not x == dest_x and not y == dest_y
                ):
                    return (x, y)  # Return the first valid spot found

        return None  # Return None if no valid spot is found

    # Pathfinding

    def create_path(self, destination=None):
        searching_for_path = True
        if destination is None:
            while searching_for_path:
                x = random.randint(0, self.world.grid_length_x - 1)
                y = random.randint(0, self.world.grid_length_y - 1)
                dest_tile = self.world.world[x][y]
                if not dest_tile["collision"] and (x, y) != self.tile["grid"]:
                    self.grid = Grid(matrix=self.world.collision_matrix)
                    self.start = self.grid.node(*self.tile["grid"])
                    self.end = self.grid.node(x, y)
                    self.heading = (x, y)
                    finder = AStarFinder(
                        diagonal_movement=DiagonalMovement.never)
                    self.path_index = 0
                    self.path, runs = finder.find_path(
                        self.start, self.end, self.grid)
                    searching_for_path = False

        else:
            if destination[0] is None or destination[1] is None:
                return  # Return if either component of the destination is None
            else:
                x = destination[0]
                y = destination[1]
                dest_tile = self.world.world[x][y]
                if not dest_tile["collision"]:
                    self.grid = Grid(matrix=self.world.collision_matrix)
                    self.start = self.grid.node(*self.tile["grid"])
                    self.end = self.grid.node(x, y)
                    self.heading = (x, y)
                    finder = AStarFinder(
                        diagonal_movement=DiagonalMovement.never)
                    self.path_index = 0
                    self.path, runs = finder.find_path(
                        self.start, self.end, self.grid)
                    if self.path:
                        searching_for_path = False

        # Pathfinding

    def change_tile(self, new_tile):
        old_x, old_y = self.tile["grid"]
        new_x, new_y = new_tile

        self.world.workers[old_x][old_y] = None
        self.world.workers[new_x][new_y] = self
        self.tile = self.world.world[new_x][new_y]
        self.step_counter += 1
        if old_x == new_x and old_y == new_y:
            self.step_counter_with_timer += 1

    def move(self):
        # Informations
        nearest_building_position, dist_to_all_buildings, people_positions, nearest_person_position, dist_to_all_persons, worker, building = self.util_return()
        # Move
        if self.is_moving:
            destination = self.moving_behaviour(self.moving_number)
            now = pg.time.get_ticks()
            if now - self.move_timer > 10:
                if not self.path:  # No current path
                    self.create_path(destination)
                    self.path_index = 0  # Reset path index
                elif self.path_index >= len(self.path):  # Path is complete
                    destination = self.moving_behaviour(self.moving_number)
                    self.create_path(destination)
                    self.path_index = 0
                else:
                    new_pos = self.path[self.path_index]
                    self.change_tile(new_pos)
                    self.path_index += 1
                self.move_timer = now

    def moving_behaviour(self, number=None):
        if number == 1 and self.is_moving:
            return None
        elif number == 2 and self.is_moving:
            if self.interacting_behaviour == 1:  # Give behavior
                if self.optimal_worker_give_pos:
                    return self.find_valid_spot_around_destination(self.optimal_worker_give_pos)
            elif self.interacting_behaviour == 2:  # Steal behavior
                if self.optimal_worker_steal_pos:
                    return self.find_valid_spot_around_destination(self.optimal_worker_steal_pos)
        elif number == 3 and self.is_moving:
            if self.optimal_building_pos:
                return self.find_valid_spot_around_destination(self.optimal_building_pos)
        else:
            return None

    # Specific movement

    def follow_person_behavior(self, behaviour=0):
        if behaviour == 1:  # Give behavior
            if self.optimal_worker_give_pos is not None:
                self.create_path(self.find_valid_spot_around_destination(
                    self.optimal_worker_give_pos))
        elif behaviour == 2:  # Steal behavior
            if self.optimal_worker_steal_pos is not None:
                self.create_path(self.find_valid_spot_around_destination(
                    self.optimal_worker_steal_pos))
        else:
            self.moving_number = 4

    def go_to_building_behavior(self):
        # Go to the nearest building
        if self.optimal_building_pos is not None:
            self.heading = self.find_valid_spot_around_destination(
                self.optimal_building_pos)
            self.create_path(self.find_valid_spot_around_destination(
                self.optimal_building_pos))
        else:
            self.moving_number = 4

    # Interaction/Behaviour

    def interacting(self):
        self.check_interacting_status()
        if self.need_interaction > 1:
            if (self.optimal_worker_give_pos or self.optimal_worker_steal_pos) is not None:
                if self.interacting_behaviour == 1:  # Give behaviour
                    self.target_worker = self.world.workers[self.optimal_worker_give_pos[0]
                                                            ][self.optimal_worker_give_pos[1]]
                elif self.interacting_behaviour == 2:  # Steal behaviour
                    self.target_worker = self.world.workers[self.optimal_worker_steal_pos[0]
                                                            ][self.optimal_worker_steal_pos[1]]

                if self.target_worker:
                    distance = pg.math.Vector2(self.tile["grid"]).distance_to(
                        pg.math.Vector2(self.target_worker.tile["grid"]))
                    if distance <= 3:
                        self.is_interacting = True
                        self.target_worker.is_being_interacted = True

    def check_interacting_status(self):  # Resetting of status variables
        if self.building_looted_count >= self.building_looted_count_limit:
            self.building_looted_count = 0
            self.interaction_count = 0
        if (self.need_give == 0 or self.need_steal == 0) and (self.is_being_interacted or self.is_interacting):
            self.is_moving = True
            self.is_being_interacted, self.is_interacting = False, False
        elif self.is_being_interacted and self.is_interacting:
            self.is_moving = True
            self.is_being_interacted, self.is_interacting = False, False
        elif self.is_being_interacted:
            self.is_moving = False
        elif self.is_interacting:
            self.is_moving = False
        else:
            self.is_moving = True

    def loot_building(self):  # loot any building in range of 3 and inv > 15
        building_pos, dist = self.find_distance_buildings()
        if building_pos is not None:
            x, y = building_pos
            if min(dist) < 3:
                building = self.world.buildings[x][y]
                if building.inventory > 1:
                    self.inventory += building.inventory
                    building.inventory = 0
                    self.last_looted_building = building_pos
                    self.building_looted_all_time += 1
                    if self.interaction_count >= self.interaction_count_limit:
                        self.building_looted_count += 1
                else:
                    pass
        else:
            pass

    # Interaction between players
    # give (true) or steal (false)
    def interaction_amount_calculations(self, target, give, percent, random_control=0):
        if give:
            inventory_diff = self.inventory - target.inventory
            give_amount = inventory_diff * \
                (percent + random.uniform(0, 0.4)*random_control)
            return round(give_amount)
        elif not give:
            steal_amount = target.inventory * \
                (percent + random.uniform(0, 0.55)*random_control)
            return round(steal_amount)

    def give_to_person(self, amount=0):
        self.is_interacting, self.is_moving = True, False
        if (self.optimal_worker_give_pos or self.optimal_worker_steal_pos) is not None:
            target_worker = self.world.workers[self.optimal_worker_give_pos[0]
                                               ][self.optimal_worker_give_pos[1]]
            if amount == 0:
                amount = self.interaction_amount_calculations(
                    target_worker, True, 0.1, 1)
            if self.inventory >= amount:
                if target_worker and target_worker is not self:
                    # Inventory transfer
                    self.inventory -= amount
                    target_worker.inventory += amount
                    # Statistics
                    self.interaction_count += 1
                    self.interaction_count_all_time += 1
                    self.interaction_count_with_timer += 1
                    self.interaction_transfer += amount
                    self.interaction_transfer_all_time += amount
                    # Reset of status
                    self.is_interacting, self.is_moving = False, True
                    target_worker.is_being_interacted = False
                    self.last_worker_interacted = target_worker
                    self.create_path()
            else:
                self.is_interacting, self.is_moving = False, True
                target_worker.is_being_interacted = False
                return

    def take_from_person(self, amount=0):
        self.is_interacting, self.is_moving = True, False
        if (self.optimal_worker_give_pos or self.optimal_worker_steal_pos) is not None:
            target_worker = self.world.workers[self.optimal_worker_steal_pos[0]
                                               ][self.optimal_worker_steal_pos[1]]
            if amount == 0:
                amount = self.interaction_amount_calculations(
                    target_worker, False, 0.25, 1)
            if target_worker and target_worker is not self:
                if target_worker.inventory >= amount:
                    # Inventory Transfer
                    self.inventory += amount * \
                        random.uniform(0.8, 0.95)  # Loss logic
                    target_worker.inventory -= amount
                    # Statistics
                    self.interaction_count += 1
                    self.interaction_count_all_time += 1
                    self.interaction_count_with_timer += 1
                    self.interaction_transfer += amount
                    self.interaction_transfer_all_time += amount
                    # Reset of status
                    self.is_interacting, self.is_moving = False, True
                    target_worker.is_being_interacted = False
                    self.last_worker_interacted = target_worker
                    self.create_path()
            else:
                return

    # Need logic
    def need_m_gather(self, proximity_weight=1.0, inventory_weight=1.0, random_weight=0, distance_limit=4):
        # Informations
        building_positions = self.find_buildings_positions()
        _, dist_to_all_buildings, _, _, _, _, _ = self.util_return()

        # Building check
        if not building_positions:
            return

        # Values
        max_building_inventory = 0
        max_building_proximity = 0
        inventory_value = 0
        best_building_position = None
        second_highest_inventory_building = None
        highest_inventory_building = None
        highest_inventory_building_pos = None

        for i, building_pos in enumerate(building_positions):
            x, y = building_pos
            building = self.world.buildings[x][y]
            distance = dist_to_all_buildings[i]
            if not building_pos == self.last_looted_building:
                # Proximity
                if distance > 0:
                    proximity_value = proximity_weight / distance
                else:
                    proximity_value = 0  # Avoid division by zero

                # Inventory
                inventory_value = inventory_weight * building.inventory

                if inventory_value > max_building_inventory:
                    second_highest_inventory_building = highest_inventory_building
                    highest_inventory_building = building
                elif inventory_value > max_building_inventory:
                    second_highest_inventory_building = building

                if distance <= distance_limit:

                    # Update values
                    if inventory_value > max_building_inventory or (inventory_value == max_building_inventory and proximity_value > max_building_proximity):
                        max_building_proximity = proximity_value
                        max_building_inventory = inventory_value
                        best_building_position = building_pos

                # Check if this building has much more inventory than others
                if highest_inventory_building is None or building.inventory > highest_inventory_building.inventory:
                    highest_inventory_building_pos = building_pos
                    highest_inventory_building = building

            # If there's a building with much more inventory, prioritize it
            if (
                highest_inventory_building
                and second_highest_inventory_building
                and highest_inventory_building.inventory >= 4 * second_highest_inventory_building.inventory
            ):
                best_building_position = highest_inventory_building_pos
                self.highest_inventory_building_pos = highest_inventory_building_pos

        # Final need
        self.need_gather = max_building_proximity + max_building_inventory + \
            (random.uniform(-0.1, 0.1) * random_weight)
        self.optimal_building_pos = best_building_position

    def need_m_give(self, proximity_weight=0.2, inventory_weight=0.8, random_weight=0, distance_limit=10):
        # Informations
        _, _, people_positions, _, _, _, _ = self.util_return()

        # Values
        max_payoff = 0
        optimal_worker_give_pos = None
        if self.interaction_count <= self.interaction_count_limit:
            for person_pos in people_positions:
                x, y = person_pos
                person = self.world.workers[x][y]

                if person is not None and person is not self and person is not self.last_worker_interacted:
                    distance = pg.math.Vector2(self.tile["grid"]).distance_to(
                        pg.math.Vector2(person.tile["grid"]))

                    # Check if the distance is within the limit
                    if distance <= distance_limit:
                        # Proximity
                        if distance > 0:
                            proximity_value = proximity_weight / distance
                        else:
                            proximity_value = 0

                        # Inventory
                        inventory_diff = (
                            self.inventory - person.inventory) * inventory_weight

                        # Total payoff
                        total_payoff = proximity_value + inventory_diff
                        if inventory_diff == 0:
                            total_payoff = 0
                        # Update if this worker has a higher payoff
                        if total_payoff > max_payoff:
                            max_payoff = total_payoff + \
                                (random.uniform(-0.1, 0.1)*random_weight)
                            # Update the position of the optimal worker to give to
                            optimal_worker_give_pos = person_pos

        # Calculate final need_give
        self.need_give = max_payoff
        self.optimal_worker_give_pos = optimal_worker_give_pos

    def need_m_steal(self, proximity_weight=1.0, inventory_weight=1.0, random_weight=0, distance_limit=10):
        # Informations
        _, _, people_positions, _, _, _, _ = self.util_return()

        # Values
        max_payoff = 0
        optimal_worker_steal_pos = None
        if self.interaction_count <= self.interaction_count_limit:
            for person_pos in people_positions:
                x, y = person_pos
                person = self.world.workers[x][y]

                if person is not None and person is not self and person is not self.last_worker_interacted:
                    distance = pg.math.Vector2(self.tile["grid"]).distance_to(
                        pg.math.Vector2(person.tile["grid"]))

                    # Check if the distance is within the limit
                    if distance <= distance_limit:
                        # proximity
                        if distance > 0:
                            proximity_value = proximity_weight / distance
                        else:
                            proximity_value = 0

                        # inventory difference
                        inventory_diff = (
                            self.inventory - person.inventory) * inventory_weight

                        # Calculate total payoff
                        total_payoff = proximity_value + inventory_diff
                        if inventory_diff == 0:
                            total_payoff = 0
                        # Update if this worker has a higher payoff
                        if total_payoff > max_payoff:
                            max_payoff = total_payoff + \
                                (random.uniform(-0.1, 0.1)*random_weight)
                            optimal_worker_steal_pos = person_pos

        # Calculate final need_steal
        self.need_steal = max_payoff
        self.optimal_worker_steal_pos = optimal_worker_steal_pos

    def need_management(self):
        # Informations
        nearest_building_position, dist_to_all_buildings, people_positions, nearest_person_position, dist_to_all_persons, worker_close, building = self.util_return()

        # Calculate needs
        if nearest_building_position is not None:
            self.need_m_gather()
        else:
            self.need_gather = 0
        self.need_m_give()
        self.need_m_steal()

        self.need_interaction = max(self.need_steal, self.need_give)

    # Decision making methode

    def brain(self):
        now = pg.time.get_ticks()
        if now - self.update_timer > 500:
            self.update_timer = now
            self.need_management()
            self.check_interacting_status()

            if self.character_value > 0:
                self.interacting_behaviour = 1  # Give
            elif self.character_value < 0:
                self.interacting_behaviour = 2  # Steal
            else:
                self.interacting_behaviour = 0  # Nothing

            # Decide whether to interact, gather, or do nothing (random)
            if not self.is_interacting or not self.is_being_interacted:
                if (
                    self.need_interaction > self.need_gather
                    and self.need_interaction > 0.5
                    and self.interaction_count <= self.interaction_count_limit
                ):
                    self.moving_number = 2  # Follow person behavior
                    self.follow_person_behavior(self.interacting_behaviour)
                elif (
                    self.need_gather > self.need_interaction
                    and self.need_gather > 0
                ):
                    self.moving_number = 3  # Go to building behavior
                    self.go_to_building_behavior()
                else:
                    self.moving_number = 4

            if self.is_interacting:
                # What behaviour when interacting
                if self.need_give > 0 and self.character_value > 0:
                    self.give_to_person()
                elif self.need_steal > 0 and self.character_value < 0:
                    self.take_from_person()

    # Other
    # Decay of materials

    def decay_inventory(self, amount_in_percent=0.01, step_up_per_100=0.01):
        if self.inventory > 0:
            reduction_amount = self.inventory * \
                (amount_in_percent + step_up_per_100 * (self.inventory // 100))
            self.inventory -= reduction_amount

    def management_of_decay(self):
        now = pg.time.get_ticks()
        if self.moving_number == 2 or self.moving_number == 3:  # Building or follow
            if now - self.update_timer_decay > 1000:
                self.update_timer_decay = now
                self.decay_inventory()
                self.inventory = round(self.inventory)
        elif self.moving_number == 4:  # Random
            if now - self.update_timer_decay > 2000:
                self.update_timer_decay = now
                self.decay_inventory()
                self.inventory = round(self.inventory)
        else:
            self.update_timer_decay = now

    # Updating

    def debug(self):
        # print("Gather need: " + str(self.need_gather) + " Give need " + str(self.need_give) +
        #      " Steal need: " + str(self.need_steal) + " Inventory: "+str(self.inventory))
        # print("IS INTERACTING: " + str(self.is_interacting) + " IS MOVING: " + str(self.is_moving))
        # print("Moving number: " + str(self.moving_number))

        # print("Goal: " + str(self.moving_behaviour(self.moving_number)) + " RealPos " + str(self.optimal_building_pos) +
        #     " Own pos " + str(self.tile["grid"]))
        if self.need_give > 10:
            print("Give need: " + str(self.need_give))
        # print("All buildings pos: " + str(self.find_buildings_positions()))
        if self.is_being_interacted:
            print("IS BEING INTERACTED")
        if self.is_interacting:
            print("INTERACTS")

    def data_gather(self):
        now = pg.time.get_ticks()
        if now - self.data_gather_timer >= 1000:
            self.data_gather_timer = now

            self.export_inventory.append(round(self.inventory))
            self.export_interaction_transfers_with_time.append(
                round(self.interaction_transfer))
            self.export_interaction_with_time.append(
                self.interaction_count_with_timer)
            self.export_steps_with_time.append(self.step_counter_with_timer)
            
            # Reset
            self.step_counter_with_timer = 0
            self.interaction_count_with_timer = 0
            self.interaction_transfer = 0

    def update(self):
        # self.debug()
        self.brain()
        self.loot_building()
        self.move()
        self.interacting()
        self.need_management()
        self.management_of_decay()
        self.data_gather()

        # self.debug()
