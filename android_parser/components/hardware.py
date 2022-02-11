from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Union

from android_parser.components.android_classes import UID, Base
from android_parser.components.application import ContentResolver
from android_parser.components.manifest import APILevel
from android_parser.utilities import constants as constants
from android_parser.utilities.constants import MAX_SDK_VERSION

if TYPE_CHECKING:
    from android_parser.components.filesystem import Directory
    from android_parser.main import AndroidParser


@dataclass
class Device(Base):
    system_apps: Dict[str, SystemApp] = field(default_factory=dict, init=False)
    _camera_module: CameraModule = field(default=None, init=False)  # type: ignore
    _gps: GPS = field(default=None, init=False)  # type: ignore
    _microphone: Microphone = field(default=None, init=False)  # type: ignore

    def __post_init__(self) -> None:
        camera_module = CameraModule()
        gps = GPS()
        microphone = Microphone()
        object.__setattr__(self, "_camera_module", camera_module)
        object.__setattr__(self, "_gps", gps)
        object.__setattr__(self, "_microphone", microphone)
        self.__add_system_apps()

    @property
    def name(self) -> str:
        return "Device"

    @property
    def camera_module(self) -> CameraModule:
        return self._camera_module

    @property
    def gps(self) -> GPS:
        return self._gps

    @property
    def microphone(self) -> Microphone:
        return self._microphone

    @property
    def asset_type(self) -> str:
        return "Device"

    def create_scad_objects(self, parser: AndroidParser) -> None:
        """Creates an Application androidLang securiCAD object
        \nKeyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)
        components: List[Union[Microphone, GPS, CameraModule, SystemApp]] = [
            self.camera_module,
            self.gps,
            self.microphone,
            *self.system_apps.values(),
        ]
        for component in components:
            component.create_scad_objects(parser=parser)

    def __add_system_apps(self) -> None:
        """Fills the device with generic androidLang systemApps"""
        system_apps = ["Dialer", "Email", "Calendar", "Camera", "Browser", "MediaStore"]
        for system_app in system_apps:
            self.system_apps[system_app] = SystemApp(_name=system_app)

    def connect_scad_objects(self, parser: AndroidParser) -> None:
        super().connect_scad_objects(parser)
        device = parser.scad_id_to_scad_obj[self.id]  # type: ignore
        components: List[Union[Microphone, GPS, CameraModule, SystemApp]] = [
            self.camera_module,
            self.gps,
            self.microphone,
        ]
        # Association SystemFeature
        for component in components:
            component_obj = parser.scad_id_to_scad_obj[component.id]  # type: ignore
            parser.create_associaton(
                s_obj=device,
                t_obj=component_obj,
                s_field="systemFeatures",
                t_field="device",
            )
        # Assoication RunsApplications
        for system_app in self.system_apps.values():
            system_app_obj = parser.scad_id_to_scad_obj[system_app.id]  # type: ignore
            parser.create_associaton(
                s_obj=device,
                t_obj=system_app_obj,
                s_field="apps",
                t_field="device",
            )
            system_app.connect_scad_objects(parser=parser)


@dataclass()
class CameraModule(Base):
    @property
    def asset_type(self) -> str:
        return "CameraModule"

    def create_scad_objects(self, parser: AndroidParser) -> None:
        """creates a CameraModule androidLang securiCAD object
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)


@dataclass()
class GPS(Base):
    @property
    def asset_type(self) -> str:
        return "Gps"

    def create_scad_objects(self, parser: AndroidParser) -> None:
        """creates a GPS androidLang securiCAD object
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)


@dataclass()
class Microphone(Base):
    @property
    def asset_type(self) -> str:
        return "Microphone"

    def create_scad_objects(self, parser: AndroidParser) -> None:
        """creates a Microphone androidLang securiCAD object
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)


@dataclass()
class SystemApp(Base):
    _name: str = field()
    _content_resolver: ContentResolver = field(default=None, init=False)  # type: ignore
    _uid: UID = field(default=None, init=False)  # type: ignore
    internal_app_directories: Dict[str, "Directory"] = field(
        default_factory=dict, init=False
    )
    _android_api_level: APILevel = field(default=None, init=False)  # type: ignore

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "_content_resolver", ContentResolver(_parent=self))
        object.__setattr__(self, "_uid", UID(_parent=self, _name=self.name))
        object.__setattr__(self, "_android_api_level", APILevel(MAX_SDK_VERSION))
        self._android_api_level.parent = self

    @property
    def name(self) -> str:
        return self._name

    @property
    def asset_type(self) -> str:
        return self.name

    @property
    def process(self) -> UID:
        return self._uid

    @property
    def content_resolver(self) -> ContentResolver:
        return self._content_resolver

    def create_scad_objects(self, parser: AndroidParser) -> None:
        """creates a specific SystemApp androidLang securiCAD object
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)
        self.content_resolver.create_scad_objects(parser=parser)
        self.process.create_scad_objects(parser=parser)
        self._android_api_level.create_scad_objects(parser=parser)

    def connect_scad_objects(self, parser: AndroidParser) -> None:
        super().connect_scad_objects(parser)
        self.content_resolver.connect_scad_objects(parser=parser)
        self.process.connect_scad_objects(parser=parser)
        sys_app = parser.scad_id_to_scad_obj[self.id]  # type: ignore
        # Association AppSpecificDirectories
        for app_dir in self.internal_app_directories.values():
            app_dir_obj = parser.scad_id_to_scad_obj[app_dir.id]  # type: ignore
            parser.create_associaton(
                s_obj=sys_app,
                t_obj=app_dir_obj,
                s_field="appFolders",
                t_field="app",
            )
        # Defense encrypted
        for int_dir in self.internal_app_directories.values():
            dir_obj = parser.scad_id_to_scad_obj[int_dir.id]  # type: ignore
            dir_obj.defense("encrypted").probability = 1.0
        # API Level
        self._android_api_level.connect_scad_objects(parser=parser)
        # Media Store related
        if self.name == "MediaStore":
            shared_storage = parser.scad_id_to_scad_obj[  # type: ignore
                parser.filesystem.media_store.id
            ]
            parser.create_associaton(
                s_obj=sys_app,
                t_obj=shared_storage,
                s_field="sharedStorage",
                t_field="mediaStore",
            )
