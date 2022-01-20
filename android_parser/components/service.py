from xml.etree.ElementTree import Element
from typing import Optional, List, TYPE_CHECKING
from android_parser.utilities.log import log
from dataclasses import dataclass, field
from android_parser.utilities import (
    xml as _xml,
)
from android_parser.components.android_classes import BaseComponent, MetaData
from android_parser.components.intent_filter import IntentFilter, IntentType

if TYPE_CHECKING:
    from android_parser.components.application import Application


@dataclass
class Service(BaseComponent):
    # https://developer.android.com/guide/topics/manifest/service-element

    def __post_init__(self):
        super().__post_init__()

    @property
    def asset_type(self) -> str:
        """The objects corresponding androidLang scad asset type"""
        return "Service"

    def from_xml(service: Element) -> "Service":
        """Creates an Service object out of a xml service tag \n
        Keyword arguments:
        \t service: An service Element object
        Returns:
        \t Service object
        """
        attribs = _xml.get_attributes(service)
        attribs.setdefault("enabled", True)
        attribs.setdefault("directBootAware", False)
        attribs.setdefault("fullBackupOnly", False)
        meta_datas = []
        for meta_data in service.findall("meta-data"):
            meta_datas.append(MetaData.from_xml(meta_data))
        intent_filters = IntentFilter.collect_intent_filters(parent=service)
        if intent_filters and attribs.get("exported") == None:
            attribs["exported"] = True
        else:
            attribs.setdefault("exported", False)

        return Service(
            attributes=attribs,
            meta_datas=meta_datas,
            intent_filters=intent_filters,
        )

    def print_intents(self, intent_type: "IntentType") -> List[str]:
        """Prints the possible intents that can be done to access the Service\n
        Keyword arguments:
        """
        if self.intent_filters and self.attribs["exported"] == False:
            log.info(
                f"Service {self.attribs['name']} has intent filters but is not exported. External components cannot reach it"
            )
        if intent_type == IntentType.IMPLICIT:
            raise (NotImplemented)
        elif intent_type == IntentType.EXPLICIT:
            raise (NotImplemented)

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        super().create_scad_objects(parser=parser)
        if not parser:
            log.error(
                f"{__file__}: Cannot create an scad object without a valid parser"
            )
            return
        parser.create_object(asset_type=self.asset_type, python_obj=self)

    def connect_scad_objects(self, parser: "AndroidParser") -> None:
        super().connect_scad_objects(parser)
