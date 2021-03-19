from components.ai import HostileEnemy
from components.fighter import Fighter
from components import consumable
from components.inventory import Inventory
from components.level import Level
from entity import Actor, Item

player = Actor(
    char="@", 
    color=(255,255,255), 
    name = "Player", 
    ai_cls=HostileEnemy,
    fighter=Fighter(hp=30, defense=2, power=5),
    inventory = Inventory(capacity=26),
    level = Level(level_up_base = 200),
)
grunt = Actor(
    char="o", 
    color=(63,127,63), 
    name = "grunt", 
    ai_cls=HostileEnemy,
    fighter=Fighter(hp=10, defense=0, power=3),
    inventory = Inventory(capacity=0),
    level=Level(xp_given=50)
)
juggernaut = Actor(
    char="T", 
    color=(0,127,0),
    name = "juggernaut", 
    ai_cls=HostileEnemy,
    fighter=Fighter(hp=16, defense=1, power=4),
    inventory=Inventory(capacity=0),
    level = Level(xp_given=100),
)

med_kit = Item(
    char="+",
    color=(127, 0, 255),
    name="med kit",
    consumable = consumable.HealingConsumable(amount=15),
)

bowie_knife = Item(
    char="~",
    color=(255,255,0),
    name="throwing knife",
    consumable=consumable.KnifeDamageConsumable(damage=20, maximum_range=5),
)

flashbang = Item(
    char="=",
    color=(207, 63, 255),
    name="flashbang",
    consumable = consumable.ConfusionConsumable(number_of_turns=10,)
)

grenade = Item(
    char="~",
    color=(255, 0, 0),
    name="grenade",
    consumable = consumable.GrenadeDamageConsumable(damage = 12, radius= 3),
)