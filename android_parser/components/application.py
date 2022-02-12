from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from xml.etree.ElementTree import Element

from android_parser.components.activity import Activity
from android_parser.components.android_classes import UID, Base
from android_parser.components.intent_filter import Intent
from android_parser.components.provider import Provider
from android_parser.components.receiver import Receiver
from android_parser.components.service import Service
from android_parser.utilities import constants as constants
from android_parser.utilities import xml as _xml
from android_parser.utilities.log import log

if TYPE_CHECKING:
    from android_parser.components.filesystem import Directory
    from android_parser.components.hardware import SystemApp
    from android_parser.components.intent_filter import (
        URI,
        Action,
        Category,
        IntentFilter,
    )
    from android_parser.components.manifest import Manifest
    from android_parser.main import AndroidParser
    from android_parser.utilities.malicious_application import MaliciousApp

AndroidComponent = Union[Activity, Provider, Service, Receiver]


@dataclass()
class Application(Base):
    attributes: dict[str, Any] = field(default_factory=dict)
    # Components
    _parent: Manifest = field(default=None)  # type: ignore
    activities: List[Activity] = field(default_factory=list)
    providers: List[Provider] = field(default_factory=list)
    services: List[Service] = field(default_factory=list)
    receivers: List[Receiver] = field(default_factory=list)
    _intent_object: Intent = field(default=None, init=False)  # type: ignore
    external_app_directories: Dict[str, Directory] = field(
        default_factory=dict, init=False
    )
    internal_app_directories: Dict[str, Directory] = field(
        default_factory=dict, init=False
    )
    _content_resolver: ContentResolver = field(default=None, init=False)  # type: ignore
    _process: UID = field(default=None, init=False)  # type: ignore
    _process_is_private: bool = field(default=False, repr=False, init=False)
    actions: Dict[str, Action] = field(
        default_factory=dict, init=False
    )  # To prevent duplicates in model
    categories: Dict[str, Category] = field(
        default_factory=dict, init=False
    )  # To prevent duplicates in model
    uris: Dict[str, URI] = field(
        default_factory=dict, init=False
    )  # To prevent duplicates in model

    @property
    def name(self) -> str:
        return self.attributes.get("name")  # type: ignore

    @property
    def asset_type(self) -> str:
        return "App"

    @property
    def intent(self) -> Intent:
        return self._intent  # type: ignore

    @property
    def process(self) -> UID:
        return self._process

    @property
    def permission(self) -> Optional[str]:
        return self.attributes.get("permission")

    @property
    def process_is_private(self) -> bool:
        return self._process_is_private

    @property
    def content_resolver(self) -> ContentResolver:
        return self._content_resolver

    @property
    def parent(self) -> Manifest:
        return self._parent

    @parent.setter
    def parent(self, parent: Manifest) -> None:
        self._parent = parent

    @property
    def components(self) -> List[AndroidComponent]:
        return [
            *self.providers,
            *self.services,
            *self.activities,
            *self.receivers,
        ]

    @property
    def intent_filters(self) -> List[IntentFilter]:
        """Returns all the intent filters that are defined within the application"""
        return [
            intent_filter for x in self.components for intent_filter in x.intent_filters
        ]

    @property
    def allow_task_reparenting(self) -> Optional[bool]:
        return self.attributes.get("allowTaskReparenting")

    def __post_init__(self):
        if self.attributes.get("process"):
            object.__setattr__(
                self,
                "_process_is_private",
                True if self.attributes.get("process", "")[0] == ":" else False,
            )  # https://developer.android.com/guide/topics/manifest/service-element#proc

        for component in self.components:
            if not component:
                continue
            component.parent = self
        # TODO: In reality an app will start it's internal unreachable components via intents as well... so remove .intent_filters?
        intent_target_components = [x for x in self.components if x.intent_filters]
        object.__setattr__(
            self, "_intent", Intent(targets=intent_target_components, _parent=self)
        )
        object.__setattr__(self, "_content_resolver", ContentResolver(_parent=self))
        procces_name = self.attributes.get("process", self.name)
        object.__setattr__(self, "_process", UID(_parent=self, _name=procces_name))
        # default attributes that goes to components
        for activity in self.activities:
            if self.allow_task_reparenting and not activity.allow_task_reparenting:
                activity.allow_task_reparenting = self.allow_task_reparenting

    @staticmethod
    def from_xml(
        application: Element, parent_type: Optional[str] = None
    ) -> Application:
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
        providers: List[Provider] = []
        services: List[Service] = []
        activities: List[Activity] = []
        receivers: List[Receiver] = []

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
            activities=activities,
            providers=providers,
            services=services,
            receivers=receivers,
        )
        return application_obj

    @staticmethod
    def collect_applications(tag: Element) -> Application:
        """Collects the application tag below the provided manifest tag.
        \n Keyword arguments:
        \t tag - a manifest xml tag
        \n Returns:
        \t An Application object
        """

        # An application tag can only occur once under a manifest
        application = tag.find("application")
        if application:
            return Application.from_xml(application=application, parent_type=tag.tag)
        else:
            raise _xml.ComponentNotFound("There is no application tag in the manifest")

    def create_scad_objects(self, parser: AndroidParser) -> None:
        """creates an Application androidLang securiCAD object
        \nKeyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)
        # UID (Process)
        self.process.create_scad_objects(parser=parser)
        # ContentResolver
        self.content_resolver.create_scad_objects(parser=parser)
        # Storage is handled by filesystem.py
        # TODO: Databases
        # Components
        for component in self.components:
            component.create_scad_objects(parser=parser)
        # Intent
        self.intent.create_scad_objects(parser=parser)

    def connect_scad_objects(self, parser: AndroidParser) -> None:
        super().connect_scad_objects(parser)
        self.content_resolver.connect_scad_objects(parser=parser)
        app = parser.scad_id_to_scad_obj[self.id]  # type: ignore
        manifest = self.parent
        # Association AndroidPermission
        if self.permission:
            permission = manifest.scad_permission_objs[self.permission]
            parser.create_associaton(
                s_obj=app,
                t_obj=permission,
                s_field="androidPermission",
                t_field="onApp",
            )
        # Association onApp
        for component in self.components:
            component_obj = parser.scad_id_to_scad_obj[component.id]  # type: ignore
            parser.create_associaton(
                s_obj=app,
                t_obj=component_obj,
                s_field="components",
                t_field="app",
            )
            component.connect_scad_objects(parser=parser)
        # Association Process
        self.process.connect_scad_objects(parser=parser)
        # Association AppSpecificDirectories
        for app_dir in [
            *self.internal_app_directories.values(),
            *self.external_app_directories.values(),
        ]:
            app_dir_obj = parser.scad_id_to_scad_obj[app_dir.id]  # type: ignore
            parser.create_associaton(
                s_obj=app,
                t_obj=app_dir_obj,
                s_field="appFolders",
                t_field="app",
            )
        # Defense encrypted
        for int_dir in self.internal_app_directories.values():
            dir_obj = parser.scad_id_to_scad_obj[int_dir.id]  # type: ignore
            if manifest.target_sdk_version >= 29:
                dir_obj.defense("encrypted").probability = 1.0
            else:
                dir_obj.defense("encrypted").probability = 0.5
        for ext_dir in self.external_app_directories.values():
            dir_obj = parser.scad_id_to_scad_obj[ext_dir.id]  # type: ignore
            dir_obj.defense("encrypted").probability = 0.5
        # Association AppScopedStorage
        try:
            scoped_storage = parser.scad_id_to_scad_obj[
                parser.filesystem.scoped_storage[self.name].id
            ]  # type: ignore
            parser.create_associaton(
                s_obj=app,
                t_obj=scoped_storage,
                s_field="scopedStorage",
                t_field="app",
            )
            for app_dir in [
                *self.internal_app_directories,
                *self.external_app_directories,
            ]:
                # Association ScopedAppSpecificDirectories
                app_dir_obj = parser.scad_id_to_scad_obj[app_dir.id]  # type: ignore
                parser.create_associaton(
                    s_obj=scoped_storage,
                    t_obj=app_dir_obj,
                    s_field="appFolders",
                    t_field="scopedStorage",
                )
        except KeyError:
            if not self.attributes.get("requestLegacyExternalStorage"):
                log.warning(
                    f"Expected a scoped storage object on app {self.name}, but none found"
                )
        # Assoication RunsApplications
        device = parser.scad_id_to_scad_obj[parser.device.id]  # type: ignore
        parser.create_associaton(
            s_obj=device,
            t_obj=app,
            s_field="apps",
            t_field="device",
        )
        # TODO: Association StructuredAppData
        # TODO: Associaton SharedPreferences
        # Defense ScopedStorage
        if self.name in parser.filesystem.scoped_storage:
            app.defense("ScopedStorage").probability = 1.0
        # Intent
        self.intent.connect_scad_objects(parser=parser)


@dataclass()
class ContentResolver(Base):
    _parent: Union[Application, MaliciousApp, SystemApp] = field(init=True)

    @property  # type: ignore
    def parent(self) -> Union[Application, MaliciousApp, SystemApp]:
        return self._parent

    @property
    def asset_type(self) -> str:
        return "ContentResolver"

    @property
    def name(self) -> str:
        return f"{self.parent.name}-ContentResolver"

    def create_scad_objects(self, parser: AndroidParser) -> None:
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)

    def connect_scad_objects(self, parser: AndroidParser) -> None:
        super().connect_scad_objects(parser)
        # Association AppContentResolver
        app = parser.scad_id_to_scad_obj[self.parent._id]  # type: ignore
        resolver = parser.scad_id_to_scad_obj[self.id]  # type: ignore
        parser.create_associaton(
            s_obj=app,
            t_obj=resolver,
            s_field="resolver",
            t_field="app",
        )
