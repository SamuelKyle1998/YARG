from __future__ import annotations
from typing import Callable, Optional, Tuple, TYPE_CHECKING, Union
from entity import Item
import os
#use TCOD's event system
import tcod.event
#import Action class and Action subclasses from actions file
import actions
from actions import (
    Action,
    BumpAction,
    WaitAction,
    PickupAction,
)
import color
import exceptions
if TYPE_CHECKING:
    from engine import Engine

MOVE_KEYS = {
    # Arrow Keys
    tcod.event.K_UP: (0, -1),
    tcod.event.K_DOWN: (0, 1),
    tcod.event.K_LEFT: (-1, 0),
    tcod.event.K_RIGHT: (1, 0),
    tcod.event.K_HOME: (-1, -1),
    tcod.event.K_END: (-1, 1),
    tcod.event.K_PAGEUP: (1, -1),
    tcod.event.K_PAGEDOWN: (1, 1),
    # Numpad Keys
    tcod.event.K_KP_1: (-1, 1),
    tcod.event.K_KP_2: (0, 1),
    tcod.event.K_KP_3: (1, 1),
    tcod.event.K_KP_4: (-1, 0),
    tcod.event.K_KP_6: (1, 0),
    tcod.event.K_KP_7: (-1, -1),
    tcod.event.K_KP_8: (0, -1),
    tcod.event.K_KP_9: (1, -1),
    # Vi keys.
    tcod.event.K_h: (-1, 0),
    tcod.event.K_j: (0, 1),
    tcod.event.K_k: (0, -1),
    tcod.event.K_l: (1, 0),
    tcod.event.K_y: (-1, -1),
    tcod.event.K_u: (1, -1),
    tcod.event.K_b: (-1, 1),
    tcod.event.K_n: (1, 1),
}
WAIT_KEYS = {
    tcod.event.K_PERIOD,
    tcod.event.K_KP_5,
    tcod.event.K_CLEAR,
}

CONFIRM_KEYS = {
    tcod.event.K_RETURN,
    tcod.event.K_KP_ENTER,
}

ActionOrHandler = Union[Action, "BaseEventHandler"]
"""An event handler return value which can trigger an action or switch active handlers.

If a handler is returned then it will become the active handler for future events.
If an action is returned it will be attempted and if its valid then 
MainGameEventHandler will become the active handler.
"""

class BaseEventHandler(tcod.event.EventDispatch[ActionOrHandler]):
    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        """Handle an event and return the next active event handler."""
        state = self.dispatch(event)
        if isinstance(state, BaseEventHandler):
            return state
        assert not isinstance(state, Action), f"{self!r} can not handle actions"
        return self

    def on_render(self, console: tcod.Console) -> None:
        raise NotImplementedError()

    def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
        raise SystemExit

class PopupMessage(BaseEventHandler):
    """Display a popup text window."""

    def __init__(self, parent_handler: BaseEventHandler, text: str):
        self.parent = parent_handler
        self.text = text

    def on_render(self, console: tcod.Console) -> None:
        """Render the parent and dim the result, then print the message on top."""
        self.parent.on_render(console)
        console.tiles_rgb["fg"] //= 8
        console.tiles_rgb["bg"] //= 8

        console.print(
            console.width // 2,
            console. height // 2,
            self.text,
            fg = color.white,
            bg = color.black,
            alignment=tcod.CENTER,
        )
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[BaseEventHandler]:
        """Any key returns to the parent handler."""
        return self.parent

#subclass of EventDispatch that allows us to send an event to its proper method based on the type of event
class EventHandler(BaseEventHandler):
    def __init__(self,engine:Engine):
        self.engine = engine

    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        """Handle events for input handlers with an engine."""
        action_or_state = self.dispatch(event)
        if isinstance(action_or_state,BaseEventHandler):
            return action_or_state
        if self.handle_action(action_or_state):
            #A valid action was performed.
            if not self.engine.player.is_alive:
                #The player was killed sometime during or after the action
                return GameOverEventHandler(self.engine)
            elif self.engine.player.level.requires_level_up:
                return LevelUpEventHandler(self.engine)
            return MainGameEventHandler(self.engine) #Return to the main handler.
        return self

    def handle_action(self, action: Optional[Action]) -> bool:
        """Handle actions returned from event methods.
        
        Returns true if the action will advance a turn
        """
        if action is None:
            return False

        try:
            action.perform()
        except exceptions.Impossible as exc:
            self.engine.message_log.add_message(exc.args[0], color.impossible)
            return False #Skip enemy turn on exceptions
        
        self.engine.handle_enemy_turns()
        self.engine.update_fov()
        return True

    #save the mouses location
    def ev_mousemotion(self, event: tcod.event.MouseMotion) -> None:
        if self.engine.game_map.in_bounds(event.tile.x,event.tile.y):
            self.engine.mouse_location = event.tile.x, event.tile.y


    def on_render(self, console: tcod.Console) -> None:
        self.engine.render(console)
    


#set event handlers for a dead player after a game over (keep them from moving)
class GameOverEventHandler(EventHandler):
    def on_quit(self) -> None:
        """Handle exiting out of a finished game."""
        if os.path.exists("savegame.sav"):
            os.remove("savegame.sav") #Deletes the active save file.
        raise exceptions.QuitWithoutSaving() #avoid saving a finished game.

    def ev_quit(self, event: tcod.event.KeyDown) -> None:
        self.on_quit

    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym == tcod.event.K_ESCAPE:
            self.on_quit()

CURSOR_Y_KEYS = {
    tcod.event.K_UP: -1,
    tcod.event.K_DOWN: 1,
    tcod.event.K_PAGEUP: -10,
    tcod.event.K_PAGEDOWN: 10,
}

class HistoryViewer(EventHandler):
    """Print the message history on a larger window which can be navigated"""
    def ev_quit(self, event: tcod.event.Quit) -> None:
        self.on_quit()

    def __init__(self, engine: Engine):
        super().__init__(engine)
        self.log_length = len(engine.message_log.messages)
        self.cursor = self.log_length -1

    def on_render(self,console:tcod.Console) -> None:
        super().on_render(console) #Draw the main state as the bakground
        log_console = tcod.Console(console.width - 6, console.height -6)

        #draw a frame with a custome banner title.
        log_console.draw_frame(0, 0, log_console.width, log_console.height)
        log_console.print_box(
            0,0,log_console.width, 1, "-|Message History|-", alignment=tcod.CENTER
        )

        #Render the message log using the cursor parameter.
        self.engine.message_log.render_messages(
                log_console,
                1,
                1,
                log_console.width - 2,
                log_console.height - 2,
                self.engine.message_log.messages[: self.cursor + 1],
        )
        log_console.blit(console,3,3)

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[MainGameEventHandler]:
        #fancy conditional movement to make it feel right
        if event.sym in CURSOR_Y_KEYS:
            adjust = CURSOR_Y_KEYS[event.sym]
            if adjust < 0 and self.cursor == 0:
                #Only move from the top to the bottom when youre on the edge
                self.cursor = self.log_length -1
            elif adjust > 0 and self.cursor == self.log_length - 1:
                #Same with the bottom to top movement.
                self.cursor = 0
            else:
                #otherwise move while staying clamped to the bounds of the history log.
                self.cursor = max(0, min(self.cursor + adjust, self.log_length - 1))
        elif event.sym == tcod.event.K_HOME:
            self.cursor = 0 #Move directly to the top message
        elif event.sym == tcod.event.K_END:
            self.cursor = self.log_length - 1 #Move directly to the last message
        else: #Any other key moves back to the main game state
            return MainGameEventHandler(self.engine)
        return None

#just exits itself by default if any key is pressed aside from modifier keys. also exits on mouse click
class AskUserEventHandler(EventHandler):
    """Handles user input for actions which require special input."""

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        """By default any key exits this input handler."""
        if event.sym in {  # Ignore modifier keys.
            tcod.event.K_LSHIFT,
            tcod.event.K_RSHIFT,
            tcod.event.K_LCTRL,
            tcod.event.K_RCTRL,
            tcod.event.K_LALT,
            tcod.event.K_RALT,
        }:
            return None
        return self.on_exit()

    def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> Optional[ActionOrHandler]:
        """By default any mouse click exits this input handler."""
        return self.on_exit()

    def on_exit(self) -> Optional[ActionOrHandler]:
        """Called when the user is trying to exit or cancel an action.

        By default this returns to the main event handler.
        """
        return MainGameEventHandler(self.engine)

class CharacterScreenEventHandler(AskUserEventHandler):
    TITLE = "Character Information"

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        if self.engine.player.x <= 30:
            x = 40
        else:
            x = 0
        
        y = 0

        width = len(self.TITLE) + 4

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=7,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0,0,0),
        )

        console.print(
            x=x + 1, y=y + 1, string =f"Level: {self.engine.player.level.current_level}"
        )
        console.print(
            x=x + 1, y=y + 2, string = f"Current XP: {self.engine.player.level.current_xp}"
        )
        console.print(
            x=x + 1, y=y + 3, string=f"XP for next level: {self.engine.player.level.experience_to_next_level}",
        )
        console.print(
            x=x + 1, y=y + 4, string=f"Attack: {self.engine.player.fighter.power}"
        )
        console.print(
            x=x + 1, y=y + 5, string=f"Defense: {self.engine.player.fighter.defense}"
        )


class LevelUpEventHandler(AskUserEventHandler):
    TITLE = "Level Up"

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)

        if self.engine.player.x <= 30:
            x = 40
        else:
            x = 0

        console.draw_frame(
            x=x,
            y=0,
            width=35,
            height=8,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        console.print(x=x + 1, y=1, string="Congratulations! You level up!")
        console.print(x=x + 1, y=2, string="Select an attribute to increase.")

        console.print(
            x=x + 1,
            y=4,
            string=f"a) Constitution (+20 HP, from {self.engine.player.fighter.max_hp})",
        )
        console.print(
            x=x + 1,
            y=5,
            string=f"b) Strength (+1 attack, from {self.engine.player.fighter.power})",
        )
        console.print(
            x=x + 1,
            y=6,
            string=f"c) Agility (+1 defense, from {self.engine.player.fighter.defense})",
        )

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.sym
        index = key - tcod.event.K_a

        if 0 <= index <= 2:
            if index == 0:
                player.level.increase_max_hp()
            elif index == 1:
                player.level.increase_power()
            else:
                player.level.increase_defense()
        else:
            self.engine.message_log.add_message("Invalid entry.", color.invalid)

            return None

        return super().ev_keydown(event)
        
    def ev_mousebuttondown(
        self, event: tcod.event.MouseButtonDown
    ) -> Optional[ActionOrHandler]:
        """
        Don't allow the player to click to exit the menu, like normal.
        """
        return None

    

class InventoryEventHandler(AskUserEventHandler):
    """This handler lets the user select an item.

    What happens then depends on the subclass.
    """

    TITLE = "<missing title>"
    
    def on_render(self, console: tcod.Console) -> None:
        """Render an inventory menu, which displays the items in the inventory, and the letter to select them.
        Will move to a different position based on where the player is located, so the player can always see where
        they are.
        """
        super().on_render(console)
        number_of_items_in_inventory = len(self.engine.player.inventory.items)
        medkit_quantity: int = 0
        medkit_printed: bool = False
        throwing_knife_quantity: int = 0
        knife_printed: bool = False
        flashbang_quantity: int = 0
        flashbang_printed = False
        grenade_quantity: int = 0
        grenade_printed = False
        height = 6

        if height <= 3:
            height = 3

        if self.engine.player.x <= 30:
            x = 40
        else:
            x = 0
        
        y = 0

        width = len(self.TITLE) + 4

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        if number_of_items_in_inventory > 0:
            for i, item in enumerate(self.engine.player.inventory.items):
                if item.name == "med kit":
                    medkit_quantity += 1
                elif item.name == "throwing knife":
                    throwing_knife_quantity += 1
                elif item.name == "grenade":
                    grenade_quantity += 1
                elif item.name == "flashbang":
                    flashbang_quantity += 1
            
            if medkit_quantity > 0:
                item_key = chr(ord("a"))
                console.print(x + 1, y + 1, f"({item_key}) Med Kit X{medkit_quantity}")
            if throwing_knife_quantity > 0:
                item_key = chr(ord("b"))
                console.print(x + 1, y + 2, f"({item_key}) Throwing Knife X{throwing_knife_quantity}")
            if grenade_quantity > 0:
                item_key = chr(ord("c"))
                console.print(x + 1, y + 3, f"({item_key}) Grenade X{grenade_quantity}")
            if flashbang_quantity > 0:
                item_key = chr(ord("d"))
                console.print(x + 1, y + 4, f"({item_key}) Flashbang X{flashbang_quantity}")
        else:
            console.print(x + 1, y + 1, "(Empty)")

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.sym
        number_of_items_in_inventory = len(self.engine.player.inventory.items)
        item_found = False
        if number_of_items_in_inventory == 0:
            return super().ev_keydown(event)
        elif key == tcod.event.K_a:
            for i, item in enumerate(self.engine.player.inventory.items):
                if item.name == "med kit":
                    selected_item = player.inventory.items[i]
                    item_found = True
                    break
            if item_found == False:
                self.engine.message_log.add_message("Invalid entry.", color.invalid)
                return None
        elif key == tcod.event.K_b:
            for i, item in enumerate(self.engine.player.inventory.items):
                if item.name == "throwing knife":
                    selected_item = player.inventory.items[i]
                    item_found = True
                    break
            if item_found == False:
                self.engine.message_log.add_message("Invalid entry.", color.invalid)
                return None
        elif key == tcod.event.K_c:
            for i, item in enumerate(self.engine.player.inventory.items):
                if item.name == "grenade":
                    selected_item = player.inventory.items[i]
                    item_found = True
                    break
            if item_found == False:
                self.engine.message_log.add_message("Invalid entry.", color.invalid)
                return None
        elif key == tcod.event.K_d:
            for i, item in enumerate(self.engine.player.inventory.items):
                if item.name == "flashbang":
                    selected_item = player.inventory.items[i]
                    item_found = True
                    break
            if item_found == False:
                self.engine.message_log.add_message("Invalid entry.", color.invalid)
                return None
        else: 
            return super().ev_keydown(event)
        return self.on_item_selected(selected_item)
        return super().ev_keydown(event)

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        """Called when the user selects a valid item."""
        raise NotImplementedError()

class InventoryActivateHandler(InventoryEventHandler):
    """Handle using an inventory item."""

    TITLE = "Select an item to use"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        """Return the action for the selected item."""
        return item.consumable.get_action(self.engine.player)


class InventoryDropHandler(InventoryEventHandler):
    """Handle dropping an inventory item."""

    TITLE = "Select an item to drop"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        """Drop this item."""
        return actions.DropItem(self.engine.player, item)

class SelectIndexHandler(AskUserEventHandler):
    """Handles asking the user for an index on the map."""
    def __init__(self, engine: Engine):
        """Sets up the cursor to the player when this handler is constructed."""
        super().__init__(engine)
        player = self.engine.player
        engine.mouse_location = player.x, player.y

    def on_render(self, console: tcod.Console) -> None:
        """Highlight the tile under the cursor."""
        super().on_render(console)
        x,y=self.engine.mouse_location
        console.tiles_rgb["bg"][x,y] = color.white
        console.tiles_rgb["fg"][x,y] = color.black

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        """Check for key movement or confirmation keys"""
        key = event.sym
        if key in MOVE_KEYS:
            modifier = 1 #Holding modifier keys will speed up key movement.
            if event.mod & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
                modifier *= 5
            if event.mod & (tcod.event.KMOD_LCTRL | tcod.event.KMOD_RCTRL):
                modifier *=10
            if event.mod &(tcod.event.KMOD_LALT | tcod.event.KMOD_RALT):
                modifier *= 20

            x,y = self.engine.mouse_location
            dx, dy = MOVE_KEYS[key]
            x += dx * modifier
            y += dy * modifier
            #clamp the cursor index to the map size
            x = max(0, min(x, self.engine.game_map.width -1))
            y = max(0, min(y, self.engine.game_map.height -1))
            self.engine.mouse_location = x, y
            return None
        elif key in CONFIRM_KEYS:
            return self.on_index_selected(*self.engine.mouse_location)
        return super().ev_keydown(event)


    def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> Optional[ActionOrHandler]:
        """left click confirms a selection"""
        if self.engine.game_map.in_bounds(*event.tile):
            if event.button == 1:
                return self.on_index_selected(*event.tile)
            return super().ev_mousebuttondown(event)

    def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
        """Called when an index is selected"""
        raise NotImplementedError()

class LookHandler(SelectIndexHandler):
    """Lets the player look around using the keyboard."""
    def on_index_selected(self, x: int, y: int) -> None:
        """Return to main handler"""
        return MainGameEventHandler(self.engine)

class SingleRangedAttackHandler(SelectIndexHandler):
    """Handles targeting a single enemy. Only the enemy selected will be affected."""

    def __init__(
        self,
        engine: Engine, 
        callback: Callable[[Tuple[int, int]], Optional[Action]]
    ):
        super().__init__(engine)

        self.callback = callback

    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        return self.callback((x,y))

class AreaRangedAttackHandler(SelectIndexHandler):
    """Handles targeting an area with a given radius. Any entity within this radius will be affected."""

    def __init__(
        self,
        engine: Engine,
        radius: int,
        callback: Callable[[Tuple[int,int]], Optional[Action]],
    ):
        super().__init__(engine)

        self.radius = radius
        self.callback = callback

    def on_render(self, console: tcod.Console) -> None:
        """Highlight the tile under the cursor."""
        super().on_render(console)

        x,y = self.engine.mouse_location

        #Draw a renctangle around the targeted area, so the player can see the affect tiles
        console.draw_frame(
            x=x - self.radius -1,
            y=y - self.radius -1,
            width = self.radius ** 2,
            height=self.radius ** 2,
            fg=color.red,
            clear=False,
        )
    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        return self.callback((x,y))


class MainGameEventHandler(EventHandler):

    #recieve and work with select keypress events
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        #action holds whatever subclass of Action we end up assigning it to. Defaults to none.
        action: Optional[Action] = None
        #key holds the actual key that we pressed 
        key = event.sym
        modifier = event.mod
        player = self.engine.player

        if key == tcod.event.K_PERIOD and modifier & (
            tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT
        ):
            return actions.TakeStairsAction(player)
        #create a MovementAction for the up, down, left and right keys if any of them are pressed
        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            action = BumpAction(player, dx, dy)
        elif key in WAIT_KEYS:
            action = WaitAction(player)
        
        #if the user presses the escape key, return EscapeAction, which will exit the game. This will exit menus in the future
        elif key == tcod.event.K_ESCAPE:
            raise SystemExit()
        
        elif key == tcod.event.K_v:
            return HistoryViewer(self.engine)

        elif key == tcod.event.K_e:
            action = PickupAction(player)

        elif key == tcod.event.K_i:
            return InventoryActivateHandler(self.engine)
        elif key == tcod.event.K_d:
            return InventoryDropHandler(self.engine)
        elif key == tcod.event.K_SLASH:
            return LookHandler(self.engine)
        elif key == tcod.event.K_c:
            return CharacterScreenEventHandler(self.engine)

        #Whether a valid key is pressed or not, we return the value of action, which is none by default.
        return action
