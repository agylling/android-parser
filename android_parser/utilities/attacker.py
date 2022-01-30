from typing import TYPE_CHECKING
from android_parser.utilities.log import log

if TYPE_CHECKING:
    from android_parser.main import AndroidParser


def create_attacker(parser: "AndroidParser") -> None:
    if parser.attacker == None:
        parser.attacker = parser.model.create_attacker()


def connect_attacker(parser: "AndroidParser") -> None:
    if parser.attacker != None:
        malicious_app = parser.scad_id_to_scad_obj[parser.malicious_application.id]
        parser.attacker.connect(malicious_app.attack_step("exploitApplications"))
