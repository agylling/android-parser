from xml.etree.ElementTree import Element
from typing import Union, List, TYPE_CHECKING, Dict, Optional
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
from android_parser.components.android_classes import Base, UID
from android_parser.components.filesystem import (
    FileSystem,
    Directory,
    DataType,
    Volume,
    FileType,
    ScopedStorage,
)
from android_parser.components.intent_filter import Intent

if TYPE_CHECKING:
    from android_parser.components.manifest import Manifest
    from android_parser.main import AndroidParser
    from android_parser.components.intent_filter import IntentFilter

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
    _intent_object: "Intent" = field(default=None, init=False)
    external_app_directories: Dict[str, Directory] = field(
        default_factory=dict, init=False
    )
    internal_app_directories: Dict[str, Directory] = field(
        default_factory=dict, init=False
    )
    _content_resolver: "ContentResolver" = field(default=None, init=False)
    _process: "UID" = field(default=False, init=False)
    _process_is_private: bool = field(default=False, repr=False, init=False)

    @property
    def name(self) -> str:
        return self.attributes.get("name")

    @property
    def intent(self) -> "Intent":
        return self._intent

    @property
    def process(self) -> "UID":
        return self._process

    @property
    def permission(self) -> Optional[str]:
        return self.attributes.get("permission")

    @property
    def process_is_private(self) -> bool:
        return self._process_is_private

    @property
    def content_resolver(self) -> "ContentResolver":
        return self._content_resolver

    @property
    def parent(self) -> "Manifest":
        return self._parent

    @parent.setter
    def parent(self, parent: "Manifest") -> None:
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
    def intent_fitlers(self) -> List["IntentFilter"]:
        """Returns all the intent filters that are defined within the application"""
        return [intent_filter for x in self.components for intent_filter in x]

    def __post_init__(self):
        if self.attributes.get("process"):
            object.__setattr__(
                self,
                "_process_is_private",
                True if self.attributes.get("process")[0] == ":" else False,
            )  # https://developer.android.com/guide/topics/manifest/service-element#proc

        for component in self.components:
            if not component:
                continue
            component.parent = self
        # TODO: In reality an app will start it's internal unreachable components via intents as well... so remove .intent_filters?
        intent_target_components = [x for x in self.components if x.intent_filters]
        object.__setattr__(
            self, "_intent", Intent(targets=intent_target_components, _parent=[self])
        )
        object.__setattr__(self, "_content_resolver", ContentResolver(_parent=self))
        procces_name = self.attributes.get("process", self.name)
        object.__setattr__(self, "_process", UID(_parent=self, _name=procces_name))

    def create_app_storage(self) -> None:
        """Generates the application directories"""
        filesystem: "FileSystem" = self.parent.file_system
        if not filesystem:
            log.error(
                f"No parser connected to parent manifest {self.parent}, cannot access FileSystem"
            )
        if not self.attributes.get("requestLegacyExternalStorage"):
            # App uses scoped storage
            scoped_storage = ScopedStorage(_name=self.name, _parent=self)
            filesystem.scoped_storage[self.name] = scoped_storage
        # External files
        ext_app_dir: "Directory" = filesystem.ext_data_dir.create_sub_dir(
            name=self.name, dir_type=DataType.APP_SPECIFIC
        )
        ext_cache_dir = ext_app_dir.create_sub_dir(
            name="cache", dir_type=DataType.APP_SPECIFIC
        )
        ext_files_dir = ext_app_dir.create_sub_dir(
            name="files", dir_type=DataType.APP_SPECIFIC
        )
        ext_files_files = ext_files_dir.create_file(name="dummy.txt")
        # Internal files
        int_app_dir: "Directory" = filesystem.int_data_dir.create_sub_dir(
            name=self.name, dir_type=DataType.APP_SPECIFIC
        )
        int_cache_dir = int_app_dir.create_sub_dir(
            name="cache", dir_type=DataType.APP_SPECIFIC
        )
        int_files_dir = int_app_dir.create_sub_dir(
            name="files", dir_type=DataType.APP_SPECIFIC
        )
        int_databases_dir = int_app_dir.create_sub_dir(
            name="databases", dir_type=DataType.APP_SPECIFIC
        )
        int_shared_prefs_dir = int_app_dir.create_sub_dir(
            name="shared_prefs", dir_type=DataType.APP_SPECIFIC
        )
        int_files_files = int_files_dir.create_file(name="dummy.txt")
        # TODO: Databases

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
            activities=activities,
            providers=providers,
            services=services,
            receivers=receivers,
        )
        return application_obj

    def collect_applications(tag: Element) -> "Application":
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
        raise _xml.ComponentNotFound("There is no application tag in the manifest")

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        """creates an Application androidLang securiCAD object
        \nKeyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        app_scad_obj = parser.create_object(asset_type="App", python_obj=self)
        # UID (Process)
        parser.create_object(python_obj=self.process)
        # ContentResolver
        parser.create_object(python_obj=self.content_resolver)
        # Storage is handled by filesystem.py
        # TODO: Databases
        # Components
        for component in self.components:
            component.create_scad_objects(parser=parser)

    def connect_scad_objects(self, parser: "AndroidParser") -> None:
        super().connect_scad_objects(parser)
        app = parser.scad_id_to_scad_obj[self.id]
        # Association AppScopedStorage
        try:
            scoped_storage = parser.filesystem.scoped_storage[self.name]
            parser.create_associaton(
                s_obj=scoped_storage,
                t_obj=app,
                s_field="app",
                t_field="scopedStorage",
            )
        except KeyError:
            if not self.attributes.get("requestLegacyExternalStorage"):
                log.warning(
                    f"Expected a scoped storage object on app {self.name}, but none found"
                )
            pass
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
            parser.create_associaton(
                s_obj=app,
                t_obj=component,
                s_field="components",
                t_field="app",
            )
        # Association AppContentResolver
        resolver = parser.scad_id_to_scad_obj[self.content_resolver]
        parser.create_associaton(
            s_obj=app,
            t_obj=resolver,
            s_field="resolver",
            t_field="app",
        )
        # TODO: USES-PERM
        # TODO: Association Process
        # TODO: Association AppSpecificDirectories
        # TODO: Association ScopedAppSpecificDirectories
        # TODO: Association StructuredAppData
        # TODO: Associaton SharedPreferences


@dataclass()
class ContentResolver(Base):
    _parent: "Application" = field(init=True)

    @property
    def parent(self) -> "Application":
        return self._parent

    @property
    def asset_type(self) -> str:
        return "ContentResolver"

    @property
    def name(self) -> str:
        return f"{self.parent.name}-ContentResolver"
