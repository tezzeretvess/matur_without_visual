import pygame as pg
import random
from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
import numpy as np
import time


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
        self.moving_number = 0
        self.is_interacting = False
        # Need variabeles
        self.need_gather = 0  # control gather behavior
        self.need_steal = 0  # control steal behavior
        self.need_give = 0  # control give behavior
        self.need_interaction = 0  # control interaction behavior
        # Character
        self.character_value = 1  # -1 stealing / 1 giving #CHANGE
        
        # Other
        self.optimal_building_pos = None
        self.optimal_worker_give_pos = None
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

    def calculate_distance_to(self, target_position): # calculates distance from itself to and object
        return pg.math.Vector2(self.tile["grid"]).distance_to(pg.math.Vector2(target_position))

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
                    print("Random location"+str(x)+" ,"+str(y))
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
            else:
                #print("moving") # debug
                new_pos = self.path[self.path_index]
                self.change_tile(new_pos)
                self.path_index += 1
            self.move_timer = now

    def moving_behaviour(self, number=None):
        if number == 1 and self.is_moving:
            return None
        elif number == 2 and self.is_moving:
            print("Moving Behavior: FOLLOW")  # Debug
            if self.interacting_behaviour == 1:  # Give behavior
                if self.optimal_worker_give_pos:
                    return self.find_valid_spot_around_destination(self.optimal_worker_give_pos)
            elif self.interacting_behaviour == 2:  # Steal behavior
                if self.optimal_worker_steal_pos:
                    return self.find_valid_spot_around_destination(self.optimal_worker_steal_pos)
        elif number == 3 and self.is_moving:
            print("Moving Behavior: GO TO BUILDING")  # Debug
            if self.optimal_building_pos:
                return self.find_valid_spot_around_destination(self.optimal_building_pos)
        else:
            return None


    # Specific movement

    def follow_person_behavior(self, behaviour=0):
        if behaviour == 1:  # Give behavior
            if self.optimal_worker_give_pos is not None:
                self.create_path(self.find_valid_spot_around_destination(self.optimal_worker_give_pos))
        elif behaviour == 2:  # Steal behavior
            if self.optimal_worker_steal_pos is not None:
                self.create_path(self.find_valid_spot_around_destination(self.optimal_worker_steal_pos))
        else:
            self.moving_number = 4

    def go_to_building_behavior(self):
        # Go to the nearest building
        if self.optimal_building_pos is not None:
            self.create_path(self.find_valid_spot_around_destination(self.optimal_building_pos))
            #print("Pos building: "+ str(self.find_valid_spot_around_destination(self.optimal_building_pos)))
        else:
            self.moving_number = 4

    # Interaction/Behaviour
        # controls Is_moving -> stops 2 worker if dist < 2 until interaction finished

    def interacting(self):
        if self.need_interaction > 1:
            print("Interacting")
            if (self.optimal_worker_give_pos or self.optimal_worker_steal_pos) is not None:
                if self.interacting_behaviour == 1:  # Give behaviour
                    self.target_worker = self.world.workers[self.optimal_worker_give_pos[0]][self.optimal_worker_give_pos[1]]
                elif self.interacting_behaviour == 2:  # Steal behaviour
                    self.target_worker = self.world.workers[self.optimal_worker_steal_pos[0]][self.optimal_worker_steal_pos[1]]
                
                if self.target_worker:
                    distance = pg.math.Vector2(self.tile["grid"]).distance_to(pg.math.Vector2(self.target_worker.tile["grid"]))
                    if distance <= 3:
                        self.is_interacting = True
                        self.target_worker.is_interacting = True

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
    def interaction_amount_calculations(self, target, give, percent, random_control=0): # give (true) or steal (false)
        if give:
            inventory_diff = self.inventory - target.inventory
            give_amount = inventory_diff * (percent + random.uniform(0, 0.4)*random_control)
            return give_amount
        elif not give:
            steal_amount = target.inventory * (percent + random.uniform(0, 0.55)*random_control)
            return steal_amount

    def give_to_person(self, amount=0):
        self.is_interacting, self.is_moving = True, False
        if (self.optimal_worker_give_pos or self.optimal_worker_steal_pos) is not None:
            target_worker = self.world.workers[self.optimal_worker_give_pos[0]][self.optimal_worker_give_pos[1]]
            if amount == 0:
                amount = self.interaction_amount_calculations(target_worker, True, 0.1,1)
            if self.inventory >= amount:
                if target_worker and target_worker is not self:
                    self.inventory -= amount
                    target_worker.inventory += amount
            else:
                return

    def take_from_person(self, amount=0):
        self.is_interacting, self.is_moving = True, False
        if (self.optimal_worker_give_pos or self.optimal_worker_steal_pos) is not None:
            target_worker = self.world.workers[self.optimal_worker_steal_pos[0]][self.optimal_worker_steal_pos[1]]
            if amount == 0:
                amount = self.interaction_amount_calculations(target_worker, False, 0.25,1)
            if target_worker and target_worker is not self:
                if target_worker.inventory >= amount:
                    self.inventory += amount
                    target_worker.inventory -= amount
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
            inventory_value = inventory_weight * building.inventory
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
        

    def need_m_give(self, proximity_weight=0.2, inventory_weight=0.8, random_weight=0, distance_limit=30):
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
                        max_payoff = total_payoff + (random.uniform(-0.1, 0.1)*random_weight)
                        # Update the position of the optimal worker to give to
                        optimal_worker_give_pos = person_pos

        # Calculate final need_give
        self.need_give = max_payoff 
        self.optimal_worker_give_pos = optimal_worker_give_pos

    def need_m_steal(self, proximity_weight=1.0, inventory_weight=1.0, random_weight=0, distance_limit=30):
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
                        max_payoff = total_payoff + (random.uniform(-0.1, 0.1)*random_weight)
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

    def brain(self, consume_limit=20):
        now = pg.time.get_ticks()
        if now - self.update_timer > 50:
            self.update_timer = now
            self.need_management()

            if self.character_value > 0:
                self.interacting_behaviour = 1
            elif self.character_value < 0:
                self.interacting_behaviour = 2
            else:
                self.interacting_behaviour = 0

            # Decide whether to interact, gather, or do nothing (random)
            
            if (
                self.need_interaction > self.need_gather
                and self.need_interaction > 0.5
            ):
                self.is_moving = True
                self.moving_number = 2  # Follow person behavior
                self.follow_person_behavior(self.interacting_behaviour)
            elif (
                self.need_gather > self.need_interaction
                and self.need_gather > 0
                and (
                    self.calculate_distance_to(self.optimal_building_pos) <= consume_limit # consume
                )
            ):
                self.moving_number = 3  # Go to building behavior
                self.go_to_building_behavior()
            else:
                self.moving_number = 4
                self.is_moving = True


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
            if now - self.update_timer > 1000:
                self.update_timer = now
                self.decay_inventory()
        if self.moving_number == 4:  # Random
            if now - self.update_timer > 2000:
                self.update_timer = now
                self.decay_inventory()
        else:
            self.update_timer = now

    # Updating

    def debug(self):
        print("Gather need: " + str(self.need_gather) + " Give need " + str(self.need_give) + " Steal need: " + str(self.need_steal) + " Interaction n " + str(self.need_interaction))
        #print("Inventory:"+str(self.inventory))
        #print("IS INTERACTING: " + str(self.is_interacting) + " IS MOVING: " + str(self.is_moving))
        print("Moving number: " + str(self.moving_number))
            
        print("Goal: " + str(self.moving_behaviour(self.moving_number)) + " RealPos " + str(self.optimal_building_pos) +
              " Own pos " + str(self.tile["grid"]))
        
        print("All buildings pos: " + str(self.find_buildings_positions()))
    

    def update(self):
        #self.debug()
        self.brain()
        self.loot_building()
        self.move()
        self.interacting()
        self.need_management()
        self.management_of_decay()
        
        # self.debug()
