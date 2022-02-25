from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Set
from xml.etree.ElementTree import Element

from android_parser.components.android_classes import (
    Base,
    BaseComponent,
    IntentType,
    MetaData,
)
from android_parser.components.intent_filter import IntentFilter
from android_parser.utilities import xml as _xml
from android_parser.utilities.log import log

if TYPE_CHECKING:
    from android_parser.main import AndroidParser


@dataclass()
class ForegroundServiceType(Base):
    _parent: Service = field()
    foreground_service_types: List[str] = field(default_factory=list)

    @property  # type: ignore
    def parent(self) -> Service:
        return self._parent

    @property
    def name(self) -> str:
        return f"{self.parent.name}-ForegroundServiceType"

    @property
    def asset_type(self) -> str:
        return "ForegroundServiceType"

    def create_scad_objects(self, parser: AndroidParser) -> None:
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)

    def connect_scad_objects(self, parser: AndroidParser) -> None:
        super().connect_scad_objects(parser)
        sys_features = {
            "camera": parser.device.camera_module,
            "microphone": parser.device.microphone,
            "location": parser.device.gps,
            "phoneCall": parser.device.system_apps["Dialer"],
        }
        # TODO: dataSync, connectedDevice, phoneCall, mediaProjection, mediaPlayback
        # Association AccessesSystemFeature / Association AccessesSystemFeature
        foreground_service = parser.scad_id_to_scad_obj[self.id]  # type: ignore
        for foreground_service_type in self.foreground_service_types:
            t_obj = sys_features.get(foreground_service_type)
            s_field = (
                "systemFeature" if foreground_service_type != "phoneCall" else "dialer"
            )
            if t_obj:
                sys_feature_scad_obj = parser.scad_id_to_scad_obj[t_obj.id]  # type: ignore
                parser.create_associaton(
                    s_obj=foreground_service,
                    t_obj=sys_feature_scad_obj,
                    s_field=s_field,
                    t_field="serviceTypes",
                )


@dataclass
class Service(BaseComponent):
    # https://developer.android.com/guide/topics/manifest/service-element
    _foreground_service_type: ForegroundServiceType = field(default=None)  # type: ignore

    def __post_init__(self):
        super().__post_init__()

        foreground_service_types = self.attributes.get(
            "foregroundServiceType", ""
        ).split("|")
        object.__setattr__(
            self,
            "_foreground_service_type",
            ForegroundServiceType(
                _parent=self, foreground_service_types=foreground_service_types
            ),
        )
        self.attributes.setdefault("isolatedProcess", False)

    @property
    def asset_type(self) -> str:
        """The objects corresponding androidLang scad asset type"""
        return "Service"

    @property
    def foreground_service_type(self) -> ForegroundServiceType:
        return self._foreground_service_type

    @property
    def isolatedProcess(self) -> bool:
        return self.attributes["isolatedProcess"]

    @staticmethod
    def from_xml(service: Element) -> Service:
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
        meta_datas: List[MetaData] = []
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

    def print_intents(self, intent_type: IntentType) -> List[str]:  # type: ignore
        """Prints the possible intents that can be done to access the Service\n
        Keyword arguments:
        """
        if self.intent_filters and self.attributes["exported"] == False:
            log.info(
                f"Service {self.attributes['name']} has intent filters but is not exported. External components cannot reach it"
            )
        if intent_type == IntentType.IMPLICIT:
            raise (NotImplemented)
        elif intent_type == IntentType.EXPLICIT:
            raise (NotImplemented)

    def create_scad_objects(self, parser: AndroidParser) -> None:
        super().create_scad_objects(parser=parser)
        if not parser:
            log.error(
                f"{__file__}: Cannot create an scad object without a valid parser"
            )
            return
        parser.create_object(asset_type=self.asset_type, python_obj=self)
        self.foreground_service_type.create_scad_objects(parser=parser)

    def connect_scad_objects(self, parser: AndroidParser) -> None:
        super().connect_scad_objects(parser)
        service = parser.scad_id_to_scad_obj[self.id]  # type: ignore
        self.foreground_service_type.connect_scad_objects(parser=parser)
        # Association foregroundServicesTypes
        foreground_service = parser.scad_id_to_scad_obj[self.foreground_service_type.id]  # type: ignore
        parser.create_associaton(
            s_obj=service,
            t_obj=foreground_service,
            s_field="foregroundServiceTypes",
            t_field="services",
        )
        # Defense isolatedProcess
        service.defense("isolatedProcess").probability = (
            1.0 if self.isolatedProcess else 0.0
        )

    def _get_adb_intents(
        self, partial_intents: Set[str], options: bool = True
    ) -> List[str]:
        final_intents: List[str] = []
        option_flags: str = ""
        for partial_intent in partial_intents:  # type: ignore
            final_intents.append(
                f"adb shell am startservice {option_flags} {partial_intent} -n {self.manifest_parent.package}/{self.name}"
            )
        return final_intents
