from typing import Dict, List, TYPE_CHECKING
from dataclasses import dataclass, field
from android_parser.components.android_classes import Base, UID
from android_parser.components.manifest import APILevel
from android_parser.components.application import ContentResolver
from android_parser.utilities.constants import MAX_SDK_VERSION

if TYPE_CHECKING:
    from android_parser.main import AndroidParser
    from android_parser.components.filesystem import Directory
    from securicad.model.object import Object


@dataclass
class MaliciousApp(Base):
    _resolver: ContentResolver = field(default=None, init=False)
    _uid: "UID" = field(default=None, init=False)
    _android_api_level: "APILevel" = field(default=None, init=False)
    internal_app_directories: Dict[str, "Directory"] = field(
        default_factory=dict, init=False
    )

    @property
    def name(self) -> str:
        return "MaliciousApp"

    @property
    def asset_type(self) -> str:
        return "MaliciousApp"

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "_resolver", ContentResolver(_parent=self))
        object.__setattr__(self, "_uid", UID(_parent=self, _name=self.name))
        object.__setattr__(self, "_android_api_level", APILevel(MAX_SDK_VERSION))
        self._android_api_level.parent = self

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        super().create_scad_objects(parser)
        app = parser.create_object(python_obj=self)
        self._resolver.create_scad_objects(parser=parser)
        self._uid.create_scad_objects(parser=parser)
        self._android_api_level.create_scad_objects(parser=parser)

    def connect_scad_objects(self, parser: "AndroidParser") -> None:
        super().connect_scad_objects(parser)
        self._resolver.connect_scad_objects(parser=parser)
        self._uid.connect_scad_objects(parser=parser)
        mal_app = parser.scad_id_to_scad_obj[self.id]
        # Association AppSpecificDirectories
        for app_dir in self.internal_app_directories.values():
            app_dir_obj = parser.scad_id_to_scad_obj[app_dir.id]
            parser.create_associaton(
                s_obj=mal_app,
                t_obj=app_dir_obj,
                s_field="appFolders",
                t_field="app",
            )
        # Defense encrypted
        for int_dir in self.internal_app_directories.values():
            dir_obj = parser.scad_id_to_scad_obj[int_dir.id]
            dir_obj.defense("encrypted").probability = 1.0
        # API Level
        self._android_api_level.connect_scad_objects(parser=parser)
        apps: List["Object"] = parser.model.objects(asset_type="Application")
        for app in apps:
            # Association ExploitingApp
            parser.create_associaton(
                s_obj=mal_app, t_obj=app, s_field="targetApp", t_field="maliciousApp"
            )
        intents: List["Object"] = parser.model.objects(asset_type="Intent")
        for intent in intents:
            # Association CreateIntent
            parser.create_associaton(
                s_obj=mal_app, t_obj=intent, s_field="intents", t_field="app"
            )
