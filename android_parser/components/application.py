from xml.etree.ElementTree import Element
from typing import Union, List, TYPE_CHECKING
from android_parser.components.provider import Provider
from android_parser.components.activity import Activity
from android_parser.components.service import Service
from android_parser.components.receiver import Receiver
from android_parser.utilities.log import log
from dataclasses import dataclass, field
from android_parser.utilities import (
    xml as _xml,
    constants as constants,
)
from android_parser.components.android_classes import Base

if TYPE_CHECKING:
    from android_parser.components.manifest import Manifest
    from android_parser.main import AndroidParser
AndroidComponent = Union[Activity, Provider, Service, Receiver]


@dataclass()
class Application(Base):
    attributes: dict = field(default_factory=dict)
    # Components
    _parent: "Manifest" = field(default=None)
    activities: List["Activity"] = field(default_factory=list)  #
    providers: List["Provider"] = field(default_factory=list)
    services: List["Service"] = field(default_factory=list)
    receivers: List["Receiver"] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.attributes.get("name")

    @property
    def process(self) -> str:
        return self.attributes.get("process", self.name)

    def __post_init__(self):
        for component in [
            *self.providers,
            *self.services,
            *self.activities,
            *self.receivers,
        ]:
            if not component:
                continue
            component.parent = self

    def from_xml(application: Element, parent_type: str = None) -> "Application":
        """Creates an Application object out of a application tag \n
        Keyword arguments:
        \t application: An application Element object
        \t parent_type: The xml tag type of the applications parent (can be set to None)
        Returns:
        \t Application object
        """
        attribs = _xml.get_attributes(tag=application)
        attribs.setdefault("enabled", True)
        attribs.setdefault("fullBackupOnly", False)
        attribs.setdefault("allowTaskReparenting", False)
        attribs.setdefault("debuggable", False)
        attribs.setdefault("allowClearUserData", True)
        attribs.setdefault("allowNativeHeapPointerTagging", True)
        attribs.setdefault("hasFragileUserData", False)
        providers = []
        services = []
        activities = []
        receivers = []

        for provider in application.findall("provider"):
            providers.append(Provider.from_xml(provider=provider))
        for service in application.findall("service"):
            services.append(Service.from_xml(service=service))
        for receiver in application.findall("receiver"):
            receivers.append(Receiver.from_xml(receiver=receiver))
        for activity in application.findall("activity"):
            activities.append(Activity.from_xml(activity=activity))

        application_obj = Application(
            attributes=attribs,
            providers=providers,
            activities=activities,
            services=services,
            receivers=receivers,
        )
        return application_obj

    def collect_applications(tag: Element) -> List["Application"]:
        """Collects all application tags below the provided xml tag.
        \n Keyword arguments:
        \t tag - a manifest xml tag
        \n Returns:
        \t A list of Application objects
        """
        applications = []
        for app_tag in tag.findall("application"):
            applications.append(
                Application.from_xml(application=app_tag, parent_type=tag.tag)
            )
        return applications

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        """creates an Application androidLang securiCAD object
        \nKeyword arguments:
        \t parser - an AndroidParser instance
        """
        if not parser:
            log.error(
                f"{__file__}: Cannot create an scad object without a valid parser"
            )
            return
        app_scad_obj = parser.create_object(asset_type="App", python_obj=self)
        # UID (Process)
        parser.create_object(asset_type="UID", name=self.process)
        # ContentResolver
        parser.create_object(
            asset_type="ContentResolver", name=f"ContentResolver-{self.name}"
        )
        # Storage
        # Components
        for component in [
            *self.activities,
            *self.services,
            *self.receivers,
            *self.providers,
        ]:
            component.create_scad_objects(parser=parser)
