from typing import TYPE_CHECKING, Union, Optional, Dict, List
from android_parser.utilities.log import log
from dataclasses import dataclass, field
from enum import Enum
from android_parser.utilities import (
    constants as constants,
)
from android_parser.components.android_classes import Base


if TYPE_CHECKING:
    from android_parser.main import AndroidParser
    from securicad.model.object import Object
    from android_parser.components.application import Application


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


def collect_filesystem() -> "FileSystem":
    return FileSystem()


@dataclass()
class FileSystem:
    _internal_storage: "Directory" = field(default=None, init=False)
    _external_storage: "Directory" = field(default=None, init=False)
    directories: Dict[str, "Object"] = field(default_factory=dict, init=False)
    scoped_storage: Dict[str, "ScopedStorage"] = field(default_factory=dict, init=False)

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
            self, "_internal_storage", create_volume(name="", volume=Volume.INTERNAL)
        )
        object.__setattr__(
            self,
            "_external_storage",
            create_volume(name="sdcard", volume=Volume.EXTERNAL),
        )
        self.fill_internal_volume()
        self.fill_external_volume()
        # TODO: MediaStore

    def fill_internal_volume(self):
        """Creates all the top directories of the external"""
        top_dirs = ["data"]
        for top_dir in top_dirs:
            self.internal_storage.create_sub_dir(name=top_dir)
        data_dir: "Directory" = self.internal_storage.sub_dirs["data"]
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
            self.external_storage.create_sub_dir(name=top_dir)
        # Android (App files)
        self.external_storage.sub_dirs["Android"].create_sub_dir("data")

    @property
    def internal_storage(self) -> "Directory":
        return self._internal_storage

    @property
    def external_storage(self) -> "Directory":
        return self._external_storage

    @property
    def int_data_dir(self) -> "Directory":
        return self.internal_storage.sub_dirs["data"].sub_dirs["data"]

    @property
    def ext_data_dir(self) -> "Directory":
        return self.external_storage.sub_dirs["Android"].sub_dirs["data"]

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        """creates the storage related androidLang securiCAD objects out of the directory structure
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        if not parser:
            log.error(
                f"{__file__}: Cannot create an scad object without a valid parser"
            )
            return
        self.internal_storage.create_scad_objects(parser=parser)
        self.external_storage.create_scad_objects(parser=parser)
        for scoped_storage_obj in self.scoped_storage.values():
            scoped_storage_obj.create_scad_objects(parser=parser)

    def connect_scad_objects(self, parser: "AndroidParser") -> None:
        """Creates the associations between the created scad objects
        \n Keyword arguments:
        \t parser - the AndroidParser instance that created the securiCAD objects
        """
        if not parser:
            log.error(f"{__file__}: Cannot connect scad objects without a valid parser")
            return

        def connect_dir_to_root(volume: "Object", sub_dirs: Dict["str", "Directory"]):
            for sub_dir in sub_dirs.values():
                sub_dir_scad_obj = parser.scad_id_to_scad_obj[sub_dir.id]
                # Association PlacedInVolumeRoot
                parser.create_associaton(
                    s_obj=volume,
                    t_obj=sub_dir_scad_obj,
                    s_field="directories",
                    t_field="volume",
                )

        device = parser.device
        if not device:
            log.error(f"{__file__}: There's no device object to connect to")
        else:
            # Association InternalStorageVolumes
            int_storage = parser.scad_id_to_scad_obj[self.internal_storage.id]
            parser.create_associaton(
                s_obj=device,
                t_obj=int_storage,
                s_field="internalStorage",
                t_field="device",
            )
            # Association ExternalStorageVolumes
            ext_storage = parser.scad_id_to_scad_obj[self.external_storage.id]
            parser.create_associaton(
                s_obj=device,
                t_obj=ext_storage,
                s_field="externalStorage",
                t_field="device",
            )
            for scoped_storage in self.scoped_storage:
                for volume in [int_storage, ext_storage]:
                    # Association ContainedIn
                    parser.create_associaton(
                        s_obj=scoped_storage,
                        t_obj=volume,
                        s_field="storageVolumes",
                        t_field="partitions",
                    )
            connect_dir_to_root(
                volume=int_storage, sub_dirs=self.internal_storage.sub_dirs
            )
            connect_dir_to_root(
                volume=ext_storage, sub_dirs=self.external_storage.sub_dirs
            )
        self.internal_storage.connect_scad_objects(parser=parser)
        self.external_storage.connect_scad_objects(parser=parser)


def _path(data: Union["Directory", "File"]) -> str:
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
    return "/".join(components.reverse())


@dataclass()
class ScopedStorage(Base):
    _parent: "Application" = field(default=None)

    @property
    def name(self) -> str:
        return "ScopedStorage"

    @property
    def asset_type(self) -> str:
        return "ScopedStorage"

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        """Creates a ScopedStorage androidLang securiCAD object
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)


@dataclass()
class Directory(Base):
    _name: str = field()
    _data_type: DataType = field(default=DataType.NORMAL)
    _volume: Volume = field(default=Volume.INTERNAL)
    _parent: Optional["Directory"] = field(default=None, init=False)
    sub_dirs: Dict[str, "Directory"] = field(default_factory=dict, init=False)
    files: Dict[str, "File"] = field(default_factory=dict, init=False)

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

    def create_sub_dir(self, name, dir_type: DataType = DataType.NORMAL) -> "Directory":
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
        name,
        file_type: FileType = FileType.DOCUMENT,
        data_type: DataType = DataType.NORMAL,
    ) -> "File":
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

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        """creates the androidLang securiCAD objects belonging to the directory
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)
        # subdirectories
        for sub_dir in self.sub_dirs.values():
            sub_dir.create_scad_objects(parser=parser)
        # files
        for file in self.files.values():
            file.create_scad_objects(parser=parser)

    def connect_scad_objects(self, parser: "AndroidParser") -> None:
        super().connect_scad_objects(parser)
        dir_scad_obj = parser.scad_id_to_scad_obj[self.id]
        for sub_dir in self.sub_dirs.values():
            # Association SubOfDirectoryOf
            sub_dir_scad_obj = parser.scad_id_to_scad_obj[sub_dir.id]
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
            file_scad_obj = parser.scad_id_to_scad_obj[file.id]
            parser.create_associaton(
                s_obj=dir_scad_obj,
                t_obj=file_scad_obj,
                s_field="files",
                t_field="directory",
            )
            # TODO: Can probably make this recursion multithreaded
        # TODO: Association PlacedUnderStorageType


@dataclass()
class File(Base):
    _name: str = field()
    _parent: Directory = field()
    _volume: Volume = field(init=False)
    _data_type: DataType = field(default=DataType.NORMAL)
    _file_type: FileType = field(default=FileType.DOCUMENT)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_volume", self.parent.volume)

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

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        """creates the androidLang securiCAD objects belonging to the directory
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        parser.create_object(asset_type=self.asset_type, python_obj=self)
