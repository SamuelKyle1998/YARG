from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

import color

if TYPE_CHECKING:
    from tcod import Console
    from engine import Engine
    from game_map import GameMap

#takes x and y variables that represent a spot on the map, and check if that location is both in bounds
#and visible. If they are, reate a string of entity names at that spot seperated by a comma. and return the string, capitalized.
def get_names_at_location(x: int, y: int, game_map: GameMap) -> str:
    if not game_map.in_bounds(x,y) or not game_map.visible[x,y]:
        return " "

    names = ", ".join(
        entity.name for entity in game_map.entities if entity.x == x and entity.y == y
    )

    return names.capitalize()

#Render the health bar
def render_bar(
    console:console, current_value: int, maximum_value: int, total_width: int
) -> None:
    bar_width = int(float(current_value)/maximum_value * total_width)

    console.draw_rect(x=0, y=45, width=20, height=1, ch=1, bg=color.bar_empty)

    if bar_width > 0:
        console.draw_rect(
            x=0, y=45, width=bar_width, height=1, ch=1, bg = color.bar_filled    
        )
    console.print(
        x=1, y=45, string=f"HP: {current_value}/{maximum_value}", fg=color.bar_text
    )
    
#render the current floor the player is on
def render_dungeon_level(
    console: Console, dungeon_level: int, location: Tuple[int,int]
) -> None:
    """
    Render the level  the player is currently on, at the given location.
    """

    x, y = location

    console.print(x=x, y=y, string=f"Floor: {dungeon_level}")

#takes the console x and y coordinates and the engine, and from the engine, grabs the mouse
#x and y coordinates and passes them to get_names_at_location which returns
#our list of entities at the mouse location as a string. Once we have the entity names returned 
#from that function as a string, we can print them to the given x and y location using console.print.
def render_names_at_mouse_location(
    console: Console, x: int, y: int, engine: Engine
) -> None:
    mouse_x, mouse_y = engine.mouse_location

    names_at_mouse_location = get_names_at_location(
        x=mouse_x, y=mouse_y, game_map=engine.game_map
    )

    console.print(x=x,y=y,string=names_at_mouse_location)

