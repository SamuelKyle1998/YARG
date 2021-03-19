from __future__ import annotations
from typing import List, Optional, Tuple, TYPE_CHECKING

import numpy as np 
import tcod
import random

from actions import Action, BumpAction, MeleeAction, MovementAction, WaitAction

if TYPE_CHECKING:
    from entity import Actor

class BaseAI(Action):
    #BaseAI doesnt implement a perform method because the entities using it will be using an AI
    #class that inherits from this one
    def perform(self) -> None:
        raise NotImplementedError()

    #get_path_to uses the walkable tiles on our map along with some TCOD tools to get the path from the BaseAI's
    #parent entity to whatever thir target might be.
    def get_path_to(self, dest_x: int, dest_y: int) -> List[Tuple[int,int]]:
        """Compute and return a path to the target position.
            if there is no valid path, returns an empty list.
        """
        #copy the walkable array. Determines how costly or time consuming it will take to reach a target.
        #If a piece of terrain or entity takes a longer time to traverse, the cost of 
        #moving is higher. this allows us to encourage the ai to take paths that cost less, and to avoid structures/ other entities 
        cost = np.array(self.entity.gamemap.tiles["walkable"], dtype=np.int8)

        for entity in self.entity.gamemap.entities:
            #check that an entity blocks movement and the cost isnt zero (blocking)
            if entity.blocks_movement and cost[entity.x, entity.y]:
                #Add to the cost of a blocked position
                #A lower number means more enemies will crowd behind eachother in 
                #hallways. A higher number means enemies will take longer paths in 
                #order to surround the player.
                cost[entity.x, entity.y] += 10
        #create a graph from the cost array and pass that graph to a new pathfinder
        graph = tcod.path.SimpleGraph(cost=cost, cardinal=2, diagonal=3)
        pathfinder = tcod.path.Pathfinder(graph)
        pathfinder.add_root((self.entity.x, self.entity.y)) #start position
        #compute the path to the destination and remove the starting point.
        path: List[List[int]] = pathfinder.path_to((dest_x, dest_y))[1:].tolist()
        #convert from List[List[int]] to List[Tuple[int,int]].
        return [(index[0], index[1]) for index in path]

#AI class we will use for our enemies
class HostileEnemy(BaseAI):
    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []

    def perform(self) -> None:
        target = self.engine.player
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y
        distance = max(abs(dx), abs(dy))  # Chebyshev distance.

        if self.engine.game_map.visible[self.entity.x, self.entity.y]:
            if distance <= 1:
                return MeleeAction(self.entity, dx, dy).perform()

            self.path = self.get_path_to(target.x, target.y)

        if self.path:
            dest_x, dest_y = self.path.pop(0)
            return MovementAction(
                self.entity, dest_x - self.entity.x, dest_y - self.entity.y,
            ).perform()

        return WaitAction(self.entity).perform()

class ConfusedEnemy(BaseAI):
    """
    A confused enemy will stumble around aimlessly for a given number of turns, then revert back to its previous AI.
    If an actor occupies a tile it is randomly moving into, it will attack
    """

    def __init__(
        self, entity: Actor, previous_ai: Optional[BaseAI], turns_remaining: int
    ):
        super().__init__(entity)

        self.previous_ai = previous_ai
        self.turns_remaining = turns_remaining

    #Causes the enemy to move in a randomly selected direction
    def perform(self) -> None:
        """Revert the AI back to the original state if the effect has run its course"""
        if self.turns_remaining <= 0:
            self.engine.message_log.add_message(
                f"The {self.entity.name} is no longer confused."
            )
            self.entity.ai = self.previous_ai
        else:
            #Pick a random direction
            direction_x, direction_y = random.choice(
                [
                    (-1, -1), #NorthWest
                    (0, -1),  #North
                    (1, -1),  #NorthEast
                    (-1, 0),  #West
                    (1, 0),   #East
                    (-1, 1),  #SouthWest
                    (0, 1),   #South
                    (1, 1),   #SouthEast
                ]
            )
            self.turns_remaining -= 1

            return BumpAction(self.entity, direction_x, direction_y,).perform()
