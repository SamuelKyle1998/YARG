from __future__ import annotations
from typing import Tuple
from game_map import GameMap
import entity_factories
import tile_types
import random
from typing import Iterator, List, Tuple, TYPE_CHECKING
from typing import Dict, Iterator, List, Tuple, TYPE_CHECKING
import tcod
if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity

max_items_by_floor = [
    (1, 1),
    (4, 2),
]

max_monsters_by_floor = [
    (1, 2),
    (4, 3),
    (6, 5),
]

item_chances: Dict[int, List[Tuple[Entity, int]]] = {
    0: [(entity_factories.med_kit, 35)],
    2: [(entity_factories.flashbang, 10)],
    4: [(entity_factories.bowie_knife, 25)],
    6: [(entity_factories.grenade, 25)],
}

enemy_chances: Dict[int, List[Tuple[Entity, int]]] = {
    
}
def get_max_value_for_floor(
    max_value_by_floor: List[Tuple[int,int]], floor: int
) -> int:
    current_value = 0

    for floor_minimum, value in max_value_by_floor:
        if floor_minimum > floor:
            break
        else:
            current_value = value

    return current_value

class RectangularRoom:
    #take the x and y coords of the top left corner and compute the bottom right corner based on the width and height parameters
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height

    #center is a property which acts like a read only variable for the RectangularRoom class. It describes the x and y coordinates at the
    #center of the room.
    @property
    def center(self) -> Tuple[int,int]:
        center_x = int((self.x1 + self.x2) / 2)
        center_y = int((self.y1 + self.y2) / 2)

        return center_x, center_y

    #The inner property returns two slices, which represent the inner parts of our room. This is the part that we'll be digging
    #out for our room in the dungeon generator. this gives us an easy way to get the part we want to carve out. Add 1 to x1 and y1 
    #to prevent lack of wall seperation between rooms
    @property
    def inner(self) -> Tuple[slice,slice]:
        """Return the inner area of this room as a 2D array index"""
        return slice(self.x1 + 1, self.x2), slice(self.y1 + 1, self.y2)

    def intersects(self, other: RectangularRoom) -> bool:
        """Return True if this room overlaps with another RectangularRoom."""
        return(
            self.x1 <= other.x2
            and self.x2 >= other.x1
            and self.y1 <= other.y2
            and self.y2 >= other.y1
        )
def place_entities(room:RectangularRoom, dungeon:GameMap, floor_number: int,) -> None:
    number_of_monsters = random.randint(
        0, get_max_value_for_floor(max_monsters_by_floor, floor_number)
    )
    number_of_items = random.randint(
        0, get_max_value_for_floor(max_monsters_by_floor, floor_number)
    )
    for i in range(number_of_monsters):
        x = random.randint(room.x1 + 1, room.x2 - 1)
        y = random.randint(room.y1 + 1, room.y2 - 1)
        #remember to check if there is already an entity at this spot 
        if not any(entity.x == x and entity.y == y for entity in dungeon.entities):
            if random.random() < 0.8:
                entity_factories.grunt.spawn(dungeon, x, y)
            else:
                entity_factories.juggernaut.spawn(dungeon, x, y)
    for i in range(number_of_items):
        x = random.randint(room.x1 + 1, room.x2 - 1)
        y = random.randint(room.y1 + 1, room.y2 - 1)

        if not any (entity.x ==x and entity.y == y for entity in dungeon.entities):
            item_chance = random.random()

            if item_chance < 0.7:
                entity_factories.med_kit.spawn(dungeon, x, y)
            elif item_chance < 0.8:
                entity_factories.grenade.spawn(dungeon, x, y)
            elif item_chance < 0.9:
                entity_factories.flashbang.spawn(dungeon, x, y)
            else:
                entity_factories.bowie_knife.spawn(dungeon, x, y)
        

#This function takes 2 arguments, both Tuples consisting of two integers.
#It should return an iterator of a Tuple of two ints. All Tuples will be x y coords on the map
def tunnel_between(
    start: Tuple[int,int], end: Tuple[int,int]
) -> Iterator[Tuple[int,int]]:
    #grab the coordinates out of the Tuples
    """Return an L shaped tunnel between these two points"""
    x1, y1 = start
    x2, y2 = end
    if random.random() < 0.5:  #50% chance of happening
        #move horizontally, then vertically
        corner_x, corner_y = x2, y1
    else:
        #move vertically, then horizonally
        corner_x, corner_y = x1, y2
    #generate coordinates for this tunnel
    """tcod includes a function in its line of sight module to draw bresenham lines.
    while we arent working with line of sight, the function is useful for getting a line
    from one point to another. in this case, we get one line, then another, to create an 'L' shaped
    tunnel. tolist converts the points in the line into a list. Yield allows us to return a generator, and 
    rather than returning the values and exiting the function, we return the values but stay in the local state.
    This allows the function to pick up where it left off when called again instead of starting over
    from the beginning."""
    for x, y in tcod.los.bresenham((x1,y1),(corner_x, corner_y)).tolist():
        yield x,y
    for x, y in tcod.los.bresenham((corner_x, corner_y), (x2, y2)).tolist():
        yield x,y

def generate_dungeon(
    max_rooms: int,
    room_min_size: int,
    room_max_size: int,
    map_width: int,
    map_height: int,
    engine: Engine,
) -> GameMap:
    """Generate a new dungeon map"""
    player = engine.player
    dungeon = GameMap(engine, map_width, map_height, entities=[player])
    #keep a running list of all of the rooms
    rooms: List[RectangularRoom] = []

    center_of_last_room = (0, 0)

    for r in range(max_rooms):
        #use given minimum and maximum room sizes to set the room's width and height
        room_width = random.randint(room_min_size,room_max_size)
        room_height = random.randint(room_min_size,room_max_size)

        x = random.randint(0, dungeon.width - room_width - 1)
        y = random.randint(0, dungeon.height - room_height - 1)

        #"RectangularRoom" class makes rectangles easier to work with
        new_room = RectangularRoom(x, y, room_width, room_height)

        #Run through the other rooms to see if they intersect with this one 
        if any(new_room.intersects(other_room) for other_room in rooms):
            continue #This room intersects, so go on to next attempt
        #If there are no intersections then the room is valid.

        #dig out this room's inner area.
        dungeon.tiles[new_room.inner] = tile_types.floor

        if len(rooms) == 0:
            #The first room, where the player starts
            player.place(*new_room.center, dungeon)
        else: #All rooms that come after the first
             #Dig out a tunnel between this room and the previous room
            for x, y in tunnel_between(rooms[-1].center, new_room.center):
                dungeon.tiles[x, y] = tile_types.floor

            center_of_last_room = new_room.center
        
        place_entities(new_room, dungeon, engine.game_world.current_floor)
        
        dungeon.tiles[center_of_last_room] = tile_types.down_stairs
        dungeon.downstairs_location = center_of_last_room
        
        #Finally, append the new room to the list.
        rooms.append(new_room)

    return dungeon
