from xml.etree.ElementTree import Element
from typing import Optional, List, TYPE_CHECKING
from android_parser.utilities.log import log
from dataclasses import dataclass, field
from android_parser.utilities import (
    xml as _xml,
)
from android_parser.components.android_classes import BaseComponent, MetaData
from android_parser.components.intent_filter import IntentType, IntentFilter

if TYPE_CHECKING:
    from android_parser.components.application import Application
    from android_parser.main import AndroidParser


@dataclass
class Activity(BaseComponent):
    # https://developer.android.com/guide/topics/manifest/activity-element

    def __post_init__(self):
        super().__post_init__()

    @property
    def foreground_service_types(self) -> List[str]:
        if not self.attributes.get("foregroundServiceType"):
            return []
        return [x for x in self.attributes.get("foregroundServiceType").split("|") if x]

    @property
    def scad_asset_type(self) -> str:
        """The objects corresponding androidLang scad asset type"""
        return "Activity"

    def from_xml(activity: Element) -> "Activity":
        """Creates an Activity object out of a xml activity tag \n
        Keyword arguments:
        \t activity: An activity Element object
        Returns:
        \t Activity object
        """
        attribs = _xml.get_attributes(activity)
        attribs.setdefault("directBootAware", False)
        # TODO default attributes
        meta_datas = []
        for meta_data in activity.findall("meta-data"):
            meta_datas.append(MetaData.from_xml(meta_data))
        intent_filters = IntentFilter.collect_intent_filters(parent=activity)
        return Activity(
            attributes=attribs,
            meta_datas=meta_datas,
            intent_filters=intent_filters,
        )

    def print_intents(self, intent_type: "IntentType") -> List[str]:
        """Prints the possible intents that can be done to access the Activity\n
        Keyword arguments:
        """
        if self.intent_filters and self.attribs["exported"] == False:
            log.info(
                f"Activity {self.attribs['name']} has intent filters but is not exported. External components cannot reach it"
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
        parser.create_object(asset_type=self.scad_asset_type, python_obj=self)
        # foreground_service_types
        for type in self.foreground_service_types:
            parser.create_object(asset_type="ForegroundServiceType", name=type)
