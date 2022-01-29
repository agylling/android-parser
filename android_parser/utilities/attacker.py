from typing import TYPE_CHECKING
from android_parser.utilities.log import log

if TYPE_CHECKING:
    from android_parser.main import AndroidParser


def create_attacker(parser: "AndroidParser") -> None:
    if parser.attacker == None:
        parser.attacker = parser.model.create_attacker()


def connect_attacker(parser: "AndroidParser") -> None:
    if parser.attacker != None:
        """parser.attacker_object.connect(
            parser.<scadObject>.attack_step("attackStepName")
        )
        """
        pass
