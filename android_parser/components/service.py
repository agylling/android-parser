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
        intent_filters = []
        for intent_filter in service.findall("intent-filter"):
            intent_filters.append(
                IntentFilter.from_xml(intent_filter, parent_type=service.tag)
            )
        if intent_filters and attribs.get("exported") == None:
            attribs["exported"] = True
        else:
            attribs.setdefault("exported", False)

        Service(
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
