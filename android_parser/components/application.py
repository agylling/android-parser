from xml.etree.ElementTree import Element
from typing import Optional, List, TYPE_CHECKING
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

if TYPE_CHECKING:
    from android_parser.components.manifest import Manifest


def collect_application(self, application):
    pass


@dataclass()
class Application:
    attributes: dict = field(default_factory=dict)
    # Components
    __manifest_parent: "Manifest" = field(default=None)
    activities: List["Activity"] = field(default_factory=list)  #
    providers: List["Provider"] = field(default_factory=list)
    services: List["Service"] = field(default_factory=list)
    receivers: List["Receiver"] = field(default_factory=list)

    @property
    def manifest_parent(self) -> "Manifest":
        return self.__manifest_parent

    @manifest_parent.setter
    def manifest_parent(self, manifest: "Manifest") -> None:
        self.__manifest_parent = manifest

    def __post_init__(self):
        pass

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
            attributes=attribs, providers=providers, activities=activities
        )
        for component in [*providers, *services, *activities, *receivers]:
            if not component:
                continue
            component.parent = application_obj
        return application_obj
