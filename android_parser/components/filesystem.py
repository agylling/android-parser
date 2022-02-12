from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Dict, Optional, Union

from android_parser.components.android_classes import Base
from android_parser.utilities import constants as constants
from android_parser.utilities.log import log

if TYPE_CHECKING:
    from securicad.model.object import Object

    from android_parser.components.application import Application
    from android_parser.components.hardware import SystemApp
    from android_parser.main import AndroidParser
    from android_parser.utilities.malicious_application import MaliciousApp


class Volume(Enum):
    INTERNAL = 1
    EXTERNAL = 2
    SCOPED_STORAGE = 3


class DataType(Enum):
    APP_SPECIFIC = "AppSpecific"
    NORMAL = ""


class FileType(Enum):
    DOCUMENT = "Document"
    APPREFERENCES = "AppPreferences"
    PHOTO = "Photo"
    VIDEO = "Video"
    AUDIO = "Audio"


def collect_filesystem() -> FileSystem:
    return FileSystem()


@dataclass()
class FileSystem:
    _internal_volume: VolumeStorage = field(default=None, init=False)  # type: ignore
    _external_volume: VolumeStorage = field(default=None, init=False)  # type: ignore
    _internal_storage_dir: Directory = field(default=None, init=False)  # type: ignore
    _external_storage_dir: Directory = field(default=None, init=False)  # type: ignore
    _media_store: SharedStorage = field(default=None, init=False)  # type: ignore
    paths: Dict[str, Object] = field(default_factory=dict, init=False)
    scoped_storage: Dict[str, ScopedStorage] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        def create_volume(name: str, volume: Volume) -> Directory:
            """Creates either internal or external storage volume on the device
            \n Keyword arguments:
            \t name - Name of the volume ("" if internal, sdcard if external)
            \n Returns:
            \t A Directory Object
            """
            return Directory(_name=name, _data_type=DataType.NORMAL, _volume=volume)

        object.__setattr__(
            self,
            "_internal_volume",
            VolumeStorage(_name="InternalStorage", _volume=Volume.INTERNAL),
        )
        object.__setattr__(
            self,
            "_external_volume",
            VolumeStorage(_name="ExternalStorage", _volume=Volume.EXTERNAL),
        )
        object.__setattr__(
            self,
            "_internal_storage_dir",
            create_volume(name="/", volume=Volume.INTERNAL),
        )
        object.__setattr__(
            self,
            "_external_storage_dir",
            create_volume(name="sdcard", volume=Volume.EXTERNAL),
        )
        object.__setattr__(
            self,
            "_media_store",
            SharedStorage(_parent=self, _name="Shared Media Storage"),
        )
        self.fill_internal_volume()
        self.fill_external_volume()

    def fill_internal_volume(self):
        """Creates all the top directories of the external"""
        top_dirs = ["data"]
        for top_dir in top_dirs:
            self.internal_storage_dir.create_sub_dir(name=top_dir)
        data_dir: Directory = self.internal_storage_dir.sub_dirs["data"]
        data_dirs = ["media", "data"]
        for sub_dir in data_dirs:
            data_dir.create_sub_dir(name=sub_dir)

    def fill_external_volume(self):
        """Creates all the top directories of the external"""
        top_dirs = [
            "Alarms",
            "Android",
            "DCIM",
            "Download",
            "Movies",
            "Music",
            "Notifications",
            "Pictures",
        ]
        for top_dir in top_dirs:
            self.external_storage_dir.create_sub_dir(name=top_dir)
        # Android (App files)
        self.external_storage_dir.sub_dirs["Android"].create_sub_dir("data")

    @property
    def internal_volume(self) -> VolumeStorage:
        return self._internal_volume

    @property
    def internal_storage_dir(self) -> Directory:
        return self._internal_storage_dir

    @property
    def external_volume(self) -> VolumeStorage:
        return self._external_volume

    @property
    def external_storage_dir(self) -> Directory:
        return self._external_storage_dir

    @property
    def int_data_dir(self) -> Directory:
        return self.internal_storage_dir.sub_dirs["data"].sub_dirs["data"]

    @property
    def ext_data_dir(self) -> Directory:
        return self.external_storage_dir.sub_dirs["Android"].sub_dirs["data"]

    @property
    def media_store(self) -> SharedStorage:
        return self._media_store

    def create_app_storage(
        self, app: Union[Application, SystemApp, MaliciousApp]
    ) -> None:
        """Generates the application directories
        \n Keyword arguments:
        \t app - Either an Application or SystemApp instance
        """
        if app.__class__.__name__ == "Application":
            if hasattr(app, "attributes") and not app.attributes.get(  # type: ignore
                "requestLegacyExternalStorage"
            ):
                # App uses scoped storage
                scoped_storage = ScopedStorage(_parent=app)
                self.scoped_storage[app.name] = scoped_storage
            # External files
            ext_app_dir: Directory = self.ext_data_dir.create_sub_dir(
                name=app.name, dir_type=DataType.APP_SPECIFIC
            )
            ext_app_dirs = app.external_app_directories  # type: ignore
            ext_app_dirs[ext_app_dir.path] = ext_app_dir
            ext_cache_dir = ext_app_dir.create_sub_dir(
                name="cache", dir_type=DataType.APP_SPECIFIC
            )
            ext_app_dirs[ext_cache_dir.path] = ext_cache_dir
            ext_files_dir = ext_app_dir.create_sub_dir(
                name="files", dir_type=DataType.APP_SPECIFIC
            )
            ext_app_dirs[ext_files_dir.path] = ext_files_dir
            ext_files_files = ext_files_dir.create_file(name="dummy.txt")  # type: ignore
        # Internal files
        int_app_dir: Directory = self.int_data_dir.create_sub_dir(
            name=app.name, dir_type=DataType.APP_SPECIFIC
        )
        app.internal_app_directories[int_app_dir.path] = int_app_dir
        int_cache_dir = int_app_dir.create_sub_dir(
            name="cache", dir_type=DataType.APP_SPECIFIC
        )
        app.internal_app_directories[int_cache_dir.path] = int_cache_dir
        int_files_dir = int_app_dir.create_sub_dir(
            name="files", dir_type=DataType.APP_SPECIFIC
        )
        app.internal_app_directories[int_files_dir.path] = int_files_dir
        int_databases_dir = int_app_dir.create_sub_dir(
            name="databases", dir_type=DataType.APP_SPECIFIC
        )
        app.internal_app_directories[int_databases_dir.path] = int_databases_dir
        int_shared_prefs_dir = int_app_dir.create_sub_dir(
            name="shared_prefs", dir_type=DataType.APP_SPECIFIC
        )
        app.internal_app_directories[int_shared_prefs_dir.path] = int_shared_prefs_dir
        int_files_files = int_files_dir.create_file(name="dummy.txt")  # type: ignore
        # TODO: Databases

    def create_scad_objects(self, parser: AndroidParser) -> None:
        """creates the storage related androidLang securiCAD objects out of the directory structure
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        if not parser:
            log.error(
                f"{__file__}: Cannot create an scad object without a valid parser"
            )
            return
        self.internal_storage_dir.create_scad_objects(parser=parser)
        self.external_storage_dir.create_scad_objects(parser=parser)
        for scoped_storage_obj in self.scoped_storage.values():
            scoped_storage_obj.create_scad_objects(parser=parser)
        self.internal_volume.create_scad_objects(parser=parser)
        self.external_volume.create_scad_objects(parser=parser)
        self.media_store.create_scad_objects(parser=parser)

    def connect_scad_objects(self, parser: AndroidParser) -> None:
        """Creates the associations between the created scad objects
        \n Keyword arguments:
        \t parser - the AndroidParser instance that created the securiCAD objects
        """
        if not parser:
            log.error(f"{__file__}: Cannot connect scad objects without a valid parser")
            return

        device = parser.scad_id_to_scad_obj[parser.device.id]  # type: ignore
        if not device:
            log.error(f"{__file__}: There's no device object to connect to")
        else:
            int_storage = parser.scad_id_to_scad_obj[self.internal_storage_dir.id]  # type: ignore
            ext_storage = parser.scad_id_to_scad_obj[self.external_storage_dir.id]  # type: ignore
            for scoped_storage in self.scoped_storage:
                scoped_storage_obj = parser.scad_id_to_scad_obj[scoped_storage.id]  # type: ignore
                for volume in [int_storage, ext_storage]:
                    # Association ContainedIn
                    parser.create_associaton(
                        s_obj=scoped_storage_obj,
                        t_obj=volume,
                        s_field="storageVolumes",
                        t_field="partitions",
                    )
        self.internal_volume.connect_scad_objects(parser=parser)
        self.external_volume.connect_scad_objects(parser=parser)
        self.internal_storage_dir.connect_scad_objects(parser=parser)
        self.external_storage_dir.connect_scad_objects(parser=parser)
        self.media_store.connect_scad_objects(parser=parser)


def _path(data: Union[Directory, File]) -> str:
    """Returns the absolute path to the file/directory"""
    queue = [data]
    components = [data.name]
    for x in queue:
        if x.parent:
            components.append(x.parent.name)
            queue.append(x.parent)
    if data.volume == Volume.INTERNAL:
        components.append("")
    else:
        components.append("sdcard")
    components[0] = "" if components[0] == "/" else components[0]
    return "/".join(components[::-1])


@dataclass
class SharedStorage(Base):
    _name: str = field()
    _parent: FileSystem = field()

    @property
    def name(self) -> str:
        return self._name

    @property
    def asset_type(self) -> str:
        return "SharedStorage"

    @property  # type: ignore
    def parent(self) -> FileSystem:
        return self._parent

    def create_scad_objects(self, parser: AndroidParser) -> None:
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)

    def connect_scad_objects(self, parser: AndroidParser) -> None:
        super().connect_scad_objects(parser)
        # Association ContainedIn
        shared_storage = parser.scad_id_to_scad_obj[self.id]  # type: ignore
        volumes = [self.parent.internal_volume, self.parent.external_volume]
        for volume in volumes:
            volume_obj = parser.scad_id_to_scad_obj[volume.id]  # type: ignore
            parser.create_associaton(
                s_obj=shared_storage,
                t_obj=volume_obj,
                s_field="storageVolumes",
                t_field="partitions",
            )


@dataclass()
class ScopedStorage(Base):
    _parent: Union[Application, SystemApp, MaliciousApp] = field()

    @property
    def name(self) -> str:
        return "ScopedStorage"

    @property
    def asset_type(self) -> str:
        return "ScopedStorage"

    def create_scad_objects(self, parser: AndroidParser) -> None:
        """Creates a ScopedStorage androidLang securiCAD object
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)


@dataclass()
class VolumeStorage(Base):
    """To create the Internal and ExternalStorage of a device"""

    _name: str = field()
    _volume: Volume = field(default=Volume.INTERNAL)

    @property
    def asset_type(self) -> str:
        """Returns the androidLang asset type; InternalStorage or ExternalStorage"""
        if self.volume == Volume.INTERNAL:
            return "InternalStorage"
        else:
            return "ExternalStorage"

    @property
    def name(self) -> str:
        return self._name

    @property
    def volume(self) -> Volume:
        """Returns wether the volume is external or internal"""
        return self._volume

    def create_scad_objects(self, parser: AndroidParser) -> None:
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)

    def connect_scad_objects(self, parser: AndroidParser) -> None:
        file_system = parser.filesystem
        volume = parser.scad_id_to_scad_obj[self.id]  # type: ignore
        if self.volume == Volume.INTERNAL:
            root_directory = file_system.internal_storage_dir
            s_field = "internalStorage"
        else:
            root_directory = file_system.external_storage_dir
            s_field = "externalStorage"
        root_directory_obj = parser.scad_id_to_scad_obj[root_directory.id]  # type: ignore
        # Association PlacedInVolumeRoot
        parser.create_associaton(
            s_obj=volume,
            t_obj=root_directory_obj,
            s_field="directories",
            t_field="volume",
        )
        # Association InternalStorageVolumes , Association ExternalStorageVolume
        device = parser.scad_id_to_scad_obj[parser.device.id]  # type: ignore
        parser.create_associaton(
            s_obj=device,
            t_obj=volume,
            s_field=s_field,
            t_field="device",
        )
        super().connect_scad_objects(parser)


@dataclass()
class Directory(Base):
    _name: str = field()
    _data_type: DataType = field(default=DataType.NORMAL)
    _volume: Volume = field(default=Volume.INTERNAL)
    _parent: Optional[Directory] = field(default=None, init=False)
    sub_dirs: Dict[str, Directory] = field(default_factory=dict, init=False)
    files: Dict[str, File] = field(default_factory=dict, init=False)

    @property
    def asset_type(self) -> str:
        """Returns the androidLang asset type; wether the directory is an AppSpecificDirectory or not"""
        return f"{self.data_type.value}Directory"

    @property
    def data_type(self) -> DataType:
        return self._data_type

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> str:
        """Returns the absolute path to the directory"""
        return _path(self)

    @property
    def volume(self) -> Volume:
        """Returns wether the directory is in external or internal storage"""
        return self._volume

    def create_sub_dir(
        self, name: str, dir_type: DataType = DataType.NORMAL
    ) -> Directory:
        """Creates a directory within the directory
        \n Keyword arguments:
        \t name - the name of the directory
        \t dir_type - if the directory is app specific or not
        \n Return:
        \t The created sub directory
        """
        dir = Directory(_name=name, _data_type=dir_type, _volume=self.volume)
        self.sub_dirs[name] = dir
        return dir

    def create_file(
        self,
        name: str,
        file_type: FileType = FileType.DOCUMENT,
        data_type: DataType = DataType.NORMAL,
    ) -> File:
        """Creates a file within the directory
        \n Keyword arguments:
        \t name - the name of the file (including extension)
        \t file_type - The type of file (document, video, audio etc.)
        \t data_type - if the file is app specific or not
        \n Return:
        \t The created file within the directory
        """
        # Parent directory takes precedence (TODO: find reference)
        if self._data_type == DataType.APP_SPECIFIC:
            data_type = DataType.APP_SPECIFIC
        file = File(
            _parent=self, _name=name, _data_type=data_type, _file_type=file_type
        )
        self.files[name] = file
        return file

    def create_scad_objects(self, parser: AndroidParser) -> None:
        """creates the androidLang securiCAD objects belonging to the directory
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        scad_obj = parser.create_object(python_obj=self)
        # subdirectories
        for sub_dir in self.sub_dirs.values():
            sub_dir.create_scad_objects(parser=parser)
        # files
        for file in self.files.values():
            file.create_scad_objects(parser=parser)
        parser.filesystem.paths[self.path] = scad_obj  # type: ignore

    def connect_scad_objects(self, parser: AndroidParser) -> None:
        super().connect_scad_objects(parser)
        dir_scad_obj = parser.scad_id_to_scad_obj[self.id]  # type: ignore
        for sub_dir in self.sub_dirs.values():
            # Association SubOfDirectoryOf
            sub_dir_scad_obj = parser.scad_id_to_scad_obj[sub_dir.id]  # type: ignore
            parser.create_associaton(
                s_obj=dir_scad_obj,
                t_obj=sub_dir_scad_obj,
                s_field="subDirectory",
                t_field="superDirectory",
            )
            # TODO: Can probably make this recursion multithreaded
            sub_dir.connect_scad_objects(parser=parser)
        for file in self.files.values():
            # Association Contains
            file_scad_obj = parser.scad_id_to_scad_obj[file.id]  # type: ignore
            parser.create_associaton(
                s_obj=dir_scad_obj,
                t_obj=file_scad_obj,
                s_field="files",
                t_field="directory",
            )
            # TODO: Can probably make this recursion multithreaded


@dataclass()
class File(Base):
    _name: str = field()
    _parent: Directory = field()
    _volume: Volume = field(default=None, init=False)  # type: ignore
    _data_type: DataType = field(default=DataType.NORMAL)
    _file_type: FileType = field(default=FileType.DOCUMENT)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_volume", self._parent.volume)

    @property
    def asset_type(self) -> str:
        """Returns the androidLang asset type; wether the file is an AppSpecificFile or not"""
        return self._file_type.value

    @property
    def data_type(self) -> DataType:
        return self._data_type

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> str:
        """Returns the absolute path to the file"""
        return _path(self)

    @property
    def volume(self) -> Volume:
        return self._volume

    def create_scad_objects(self, parser: AndroidParser) -> None:
        """creates the androidLang securiCAD objects belonging to the directory
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        scad_obj = parser.create_object(asset_type=self.asset_type, python_obj=self)
        parser.filesystem.paths[self.path] = scad_obj  # type: ignore
