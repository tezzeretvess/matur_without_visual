import pygame as pg
import random
from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
import numpy as np


class Worker:

    def __init__(self, tile, world):
        self.world = world
        self.world.entities.append(self)
        self.name = "worker"
        self.inventory = 0

        self.update_timer = pg.time.get_ticks()

        image = pg.image.load("assets/graphics/worker.png").convert_alpha()
        scaled_width = image.get_width()
        scaled_height = image.get_height()
        self.image = pg.transform.scale(image, (scaled_width, scaled_height))

        self.tile = tile
        self.world.workers[tile["grid"][0]][tile["grid"][1]] = self
        self.move_timer = pg.time.get_ticks()
        # Status variables
        self.is_moving = True
        self.moving_number = 2
        self.is_interacting = False
        self.need_gather = 0  # control gather behavior
        self.need_steal = 0  # control steal behavior
        self.need_give = 0  # control give behavior
        self.need_interaction = 0  # control interaction behavior

        # Other
        self.optimal_building_pos = None
        self.optimal_worker_give_pos = None
        self.optimal_worker_steal_pos = None

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

    # Pathfinding

    def create_path(self, destination=None):
        searching_for_path = True
        if destination is None:
            while searching_for_path:
                x = random.randint(0, self.world.grid_length_x - 1)
                y = random.randint(0, self.world.grid_length_y - 1)
                dest_tile = self.world.world[x][y]
                if not dest_tile["collision"]:
                    self.grid = Grid(matrix=self.world.collision_matrix)
                    self.start = self.grid.node(*self.tile["grid"])
                    self.end = self.grid.node(x, y)
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

    def find_valid_spot_around_destination(self, destination, radius=1):
        dest_x, dest_y = destination

        for x in range(dest_x - radius, dest_x + radius + 1):
            for y in range(dest_y - radius, dest_y + radius + 1):
                if (
                    0 <= x < len(self.world.world)
                    and 0 <= y < len(self.world.world[0])
                    and not self.world.world[x][y]["collision"]
                ):
                    return (x, y)  # Return the first valid spot found

        return None  # Return None if no valid spot is found

    def move(self):
        # Informations
        nearest_building_position, dist_to_all_buildings, people_positions, nearest_person_position, dist_to_all_persons, worker, building = self.util_return()
        # Move
        destination = self.moving_behaviour(self.moving_number)
        now = pg.time.get_ticks()
        if now - self.move_timer > 100:
            if not self.path:  # No current path
                self.create_path(destination)
                self.path_index = 0  # Reset path index
                print("no current path")  # debug
            elif self.path_index >= len(self.path):  # Path is complete
                destination = self.moving_behaviour(self.moving_number)
                print(self.moving_number)
                print(self.optimal_building_pos)
                print("Path completed + New path to: " +
                      str(destination))  # debug
                print(self.tile["grid"])
                self.create_path(destination)
                self.path_index = 0
            elif self.is_moving:
                # print("moving") # debug
                new_pos = self.path[self.path_index]
                self.change_tile(new_pos)
                self.path_index += 1
            self.move_timer = now

    def moving_behaviour(self, number=None):
        if number == 1 and self.is_moving:
            return None
        elif number == 2 and self.is_moving:
            print("Moving Behavior: FOLLOW")  # Debug
            worker_obj = self.get_nearest_worker()
            if worker_obj:
                return self.find_valid_spot_around_destination(worker_obj.tile["grid"])
            return None
        elif number == 3 and self.is_moving:
            print("Moving Behavior: GO TO BUILDING")  # Debug
            if self.optimal_building_pos:
                return self.find_valid_spot_around_destination(self.optimal_building_pos)
            else:
                return None
        else:
            return None

    # Specific movement

    def follow_person_behavior(self, behaviour=0):
        nearest_worker = self.get_nearest_worker()
        if nearest_worker:
            if behaviour == 1:  # Give behaviour
                self.is_interacting = False
                self.create_path(self.find_valid_spot_around_destination(
                    self.optimal_worker_give_pos))
            elif behaviour == 2:  # Steal behaviour
                self.is_interacting = False
                self.create_path(self.find_valid_spot_around_destination(
                    self.optimal_worker_steal_pos))
            else:
                self.is_interacting = False
                self.create_path(self.find_valid_spot_around_destination(
                    self.get_position_of_worker(nearest_worker)))
        else:
            self.moving_number = 4

    def go_to_building_behavior(self):
        # Go to the nearest building
        nearest_building_position, _ = self.find_distance_buildings()
        if nearest_building_position is not None:
            self.is_interacting = False
            self.create_path(self.find_valid_spot_around_destination(
                self.optimal_building_pos))
        else:
            self.moving_number = 4  # Switch to idle if no buildings nearby

    # Interaction
        # controls Is_moving -> stops 2 worker if dist < 2 until interaction finished

    def interacting(self):
        _, _, _, _, dist_to_all_persons, worker, _ = self.util_return()
        if min(dist_to_all_persons) < 5 and self.need_interaction > 1:
            print("Interacting")
            self.is_interacting = True
            worker.is_interacting = True

            # Interaction is complete, reset flags
            self.is_interacting = False
            worker.is_interacting = False

    def loot_building(self):  # loot any building in range of 3 and inv > 15
        building_pos, dist = self.find_distance_buildings()
        if building_pos is not None:
            x, y = building_pos
            if min(dist) < 3:
                building = self.world.buildings[x][y]
                if building.inventory > 15:
                    self.inventory += building.inventory
                    building.inventory = 0
                else:
                    pass
        else:
            pass

        # Interaction between players

    def give_to_person(self, amount=0):
        _, _, _, _, _, worker, _ = self.util_return()
        self.is_interacting, self.is_moving = True, False
        if self.inventory >= amount:
            self.inventory -= amount
            worker.inventory += amount
        else:
            return

    def take_from_person(self, amount=0):
        _, _, _, _, _, worker, _ = self.util_return()
        self.is_interacting, self.is_moving = True, False
        if worker.inventory >= amount:
            self.inventory += amount
            worker.inventory -= amount
        else:
            return

    # Need logic
    def need_m_gather(self, proximity_weight=1.0, inventory_weight=1.0, random_weight=0):
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

        for i, building_pos in enumerate(building_positions):
            x, y = building_pos
            building = self.world.buildings[x][y]
            distance = dist_to_all_buildings[i]

            # Proximity
            if distance > 0:
                proximity_value = proximity_weight / distance

            else:
                proximity_value = 0  # Avoid division by zero

            # Inventory
            inventory_value = inventory_weight * (building.inventory - self.inventory)

            # Inventory boost
            if building.inventory >= 100:
                inventory_value *= 2  

            # Highest payoff building
            if proximity_value > max_building_proximity or (proximity_value == max_building_proximity and inventory_value > max_building_inventory):
                max_building_proximity = proximity_value
                max_building_inventory = inventory_value
                # Update position best building
                best_building_position = building_pos

        # Final need
        self.need_gather = max_building_proximity + max_building_inventory + (random.uniform(-0.1, 0.1) * random_weight)
        self.optimal_building_pos = best_building_position
        print(self.need_gather)

    def need_m_give(self, proximity_weight=0.2, inventory_weight=0.8, random_weight=0):
        # Informations
        _, _, people_positions, _, _, _, _ = self.util_return()

        # Values
        max_payoff = 0
        optimal_worker_give_pos = None

        for person_pos in people_positions:
            x, y = person_pos
            person = self.world.workers[x][y]

            if person is not None and person is not self:
                distance = pg.math.Vector2(self.tile["grid"]).distance_to(
                    pg.math.Vector2(person.tile["grid"]))

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

                # Update best option
                if total_payoff > max_payoff:
                    max_payoff = total_payoff
                    # Update the position of the optimal worker to give to
                    optimal_worker_give_pos = person_pos

        # Calculate final need_give
        self.need_give = max_payoff + (random.uniform(-0.1, 0.1)*random_weight)
        self.optimal_worker_give_pos = optimal_worker_give_pos

    def need_m_steal(self, proximity_weight=1.0, inventory_weight=1.0, random_weight=0):
        # Informations
        _, _, people_positions, _, _, _, _ = self.util_return()

        # Values
        max_payoff = 0
        optimal_worker_steal_pos = None

        for person_pos in people_positions:
            x, y = person_pos
            person = self.world.workers[x][y]

            if person is not None and person is not self:
                distance = pg.math.Vector2(self.tile["grid"]).distance_to(
                    pg.math.Vector2(person.tile["grid"]))

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

                # Update if this worker has a higher payoff
                if total_payoff > max_payoff:
                    max_payoff = total_payoff
                    optimal_worker_steal_pos = person_pos

        # Calculate final need_steal 
        self.need_steal = max_payoff + (random.uniform(-0.1, 0.1)*random_weight)
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
        if now - self.update_timer > 1000:
            self.update_timer = now
            self.need_management()

            if self.need_give > self.need_steal:
                interacting_behaviour = 1
            elif self.need_give < self.need_steal:
                interacting_behaviour = 2
            else:
                interacting_behaviour = 0  

            # Decide whether to interact, gather, or do nothing
            if self.need_interaction > self.need_gather and self.need_interaction > 0.5:
                self.is_moving = True
                self.moving_number = 2  # Follow person behavior
                self.follow_person_behavior(interacting_behaviour)
            elif self.need_gather > self.need_interaction and self.need_gather > 0:
                self.is_interacting = False
                self.is_moving = True
                self.moving_number = 3  # Go to building behavior
                self.go_to_building_behavior()
            else:
                self.moving_number = 4
                self.is_moving = True

        self.move()

        if self.is_interacting:
            # What behaviour when interacting
            if self.need_give > self.need_steal and self.need_give > 0:
                self.give_to_person()
            elif self.need_give < self.need_steal and self.need_steal > 0:
                self.take_from_person()

    # Updating

    def debug(self):
        print("Gather need: " + str(self.need_gather) + " Interaction need: " + str(self.need_interaction) +
              " Give need " + str(self.need_give) + " Steal need: " + str(self.need_steal))
        # if self.is_interacting:
        # print("IS INTERACTING")
        # print(str(self.moving_behaviour(self.moving_number)) +
        #      " Own pos " + str(self.tile["grid"]))

    def update(self):
        # self.debug()
        self.brain()           
        self.loot_building()   
        self.move()       
        self.interacting()
        self.need_management()  
        # self.debug()
