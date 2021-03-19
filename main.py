#!urs/bin/env python
import tcod
import color
import traceback
import exceptions
import input_handlers
import setup_game


def save_game(handler: input_handlers.BaseEventHandler, filename: str) -> None:
    """if the current event handler has an active engine then save it."""
    if isinstance(handler, input_handlers.EventHandler):
        handler.engine.save_as(filename)
        print("Game saved.")
def main() -> None:
    #declare screen size variables
    screen_width = 80
    screen_height = 50
    #tell TCOD which font it will use
    tileset = tcod.tileset.load_tilesheet(
        "dejavu10x10_gs_tc.png", 32, 8, tcod.tileset.CHARMAP_TCOD
    )
    handler: input_handlers.BaseEventHandler = setup_game.MainMenu()
    #create the screen
    with tcod.context.new_terminal(
        screen_width,
        screen_height,
        tileset = tileset,
        title = "YARG",
        vsync = True,
    ) as context:
    #create the console the program will draw to, and change numpy order to "x,y"
        root_console = tcod.Console(screen_width, screen_height, order="F")
    #create game loop
        try:
            while True:
                root_console.clear()
                handler.on_render(console = root_console)
                context.present(root_console)

                try:
                    for event in tcod.event.wait():
                        context.convert_event(event)
                        handler = handler.handle_events(event)
                except Exception: #Handle exceptions in game.ii
                    traceback.print_exc() #Print error to stderr.
                    #Then print the error to the message log.
                    if isinstance(handler, input_handlers.EventHandler):
                        handler.engine.message_log.add_message(
                            traceback.format.exc(), color.error
                        )
        except exceptions.QuitWithoutSaving:
            raise
        except SystemExit: 
            save_game(handler, "savegame.sav")
            raise
        except BaseException: 
            save_game(handler, "savegame.sav")
            raise

if __name__ == "__main__":
    main()