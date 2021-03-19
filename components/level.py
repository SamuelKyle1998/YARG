from __future__ import annotations

from typing import TYPE_CHECKING

from components.base_component import BaseComponent

if TYPE_CHECKING:
    from entity import Actor

class Level(BaseComponent):
    parent: Actor
    def __init__(
        self,
        current_level: int = 1,
        current_xp: int = 0,
        level_up_base: int = 0,
        level_up_factor: int = 150,
        xp_given: int = 0,
    ):
        self.current_level = current_level
        self.current_xp = current_xp
        self.level_up_base = level_up_base
        self.level_up_factor = level_up_factor
        self.xp_given = xp_given

    @property
    #Calculate the amount of experience needed to reach the next level. scales with player level by a factor of 150
    def experience_to_next_level(self) -> int:
        return self.level_up_base + self.current_level * self.level_up_factor

    #Use this function to determine whether or not the player needs to level up based on their current xp.
    #If current xp is higher than experience to next level, then the player levels up.
    @property
    def requires_level_up(self) -> bool:
        return self.current_xp >= self.experience_to_next_level

    #add to the xp pool, and check if requires level up
    def add_xp(self, xp: int) -> None:
        if xp == 0 or self.level_up_base == 0:
            return
        self.current_xp += xp
        self.engine.message_log.add_message(f"You gain {xp} experience points.")

        if self.requires_level_up:
         self.engine.message_log.add_message(
             f"You advance to level {self.current_level + 1}!"
         )

    #add to the current level, and decrease the current_xp by the experience to next level so that it takes more experience to level up to the next level
    def increase_level(self) -> None:
        self.current_xp -= self.experience_to_next_level
        self.current_level += 1

    #increase the players stat attributes
    def increase_max_hp(self, amount: int = 20) -> None:
        self.parent.fighter.max_hp += amount
        self.parent.fighter.hp += amount

        self.engine.message_log.add_message("Your health improves!")
        self.increase_level()
    
    #increase the players stat attributes
    def increase_power(self, amount: int = 1) -> None:
        self.parent.fighter.power += amount

        self.engine.message_log.add_message("You feel stronger!")

        self.increase_level()

    #increase the players stat attributes
    def increase_defense(self, amount: int = 1) -> None:
        self.parent.fighter.defense += amount

        self.engine.message_log.add_message("You feel sturdier!")

        self.increase_level()

