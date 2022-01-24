from typing import TYPE_CHECKING, Union, Dict, List
from android_parser.utilities.log import log
from dataclasses import dataclass, field
from android_parser.utilities import (
    constants as constants,
)
from android_parser.components.android_classes import Base


if TYPE_CHECKING:
    from android_parser.main import AndroidParser
    from securicad.model.object import Object


@dataclass
class Device(Base):
    system_apps: Dict[str, "SystemApp"] = field(default_factory=dict, init=False)
    _camera_module: "CameraModule" = field(default=None, init=False)
    _gps: "GPS" = field(default=None, init=False)
    _microphone: "Microphone" = field(default=None, init=False)

    def __post_init__(self) -> None:
        camera_module = CameraModule()
        gps = GPS()
        microphone = Microphone()
        object.__setattr__(self, "_camera_module", camera_module)
        object.__setattr__(self, "_gps", gps)
        object.__setattr__(self, "_microphone", microphone)
        self.__add_system_apps()

    @property
    def camera_module(self) -> "CameraModule":
        return self._camera_module

    @property
    def gps(self) -> "GPS":
        return self._gps

    @property
    def microphone(self) -> "Microphone":
        return self._microphone

    @property
    def asset_type(self) -> str:
        return "Device"

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        """Creates an Application androidLang securiCAD object
        \nKeyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)
        components: List[Union["Microphone", "GPS", "CameraModule", "SystemApp"]] = [
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

    def connect_scad_objects(self, parser: "AndroidParser") -> None:
        super().connect_scad_objects(parser)
        device = parser.scad_id_to_scad_obj[self.id]
        components: List[Union["Microphone", "GPS", "CameraModule", "SystemApp"]] = [
            self.camera_module,
            self.gps,
            self.microphone,
        ]
        # Association SystemFeature
        for component in components:
            component_obj = parser.scad_id_to_scad_obj[component.id]
            parser.create_associaton(
                s_obj=device,
                t_obj=component_obj,
                s_field="systemFeatures",
                t_field="device",
            )
        # Assoication RunsApplications
        for system_app in self.system_apps.values():
            system_app_obj = parser.scad_id_to_scad_obj[system_app.id]
            parser.create_associaton(
                s_obj=device,
                t_obj=system_app_obj,
                s_field="apps",
                t_field="device",
            )


@dataclass()
class CameraModule(Base):
    @property
    def asset_type(self) -> str:
        return "CameraModule"

    def create_scad_objects(self, parser: "AndroidParser") -> None:
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

    def create_scad_objects(self, parser: "AndroidParser") -> None:
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

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        """creates a Microphone androidLang securiCAD object
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)


@dataclass()
class SystemApp(Base):
    _name: str = field()

    @property
    def name(self) -> str:
        return self._name

    @property
    def asset_type(self) -> str:
        return self.name

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        """creates a specific SystemApp androidLang securiCAD object
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)
