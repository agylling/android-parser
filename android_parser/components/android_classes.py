from dataclasses import dataclass, field
from os import name
from typing import Dict, List, Optional, Union, Tuple, TYPE_CHECKING
from xml.etree.ElementTree import Element
from enum import Enum
from android_parser.utilities.log import log
from android_parser.utilities import (
    xml as _xml,
    constants as constants,
)

if TYPE_CHECKING:
    from android_parser.components.application import Application


@dataclass
class BaseComponent:
    # Shared attributes between Activity, BroadcastReceiver, ContentProvider and Service
    attributes: dict = field(default_factory=dict)
    _process_is_private: Optional[bool] = field(default=None, repr=False, init=False)
    _parent: "Application" = field(default=None, init=False)
    # Shared tags
    meta_datas: List["MetaData"] = field(default_factory=list)
    intent_filters: List["MetaData"] = field(default_factory=list)

    def __post_init__(self):
        if self.attributes.get("process"):
            object.__setattr__(
                self,
                "_process_is_private",
                True if self.attributes.get("process")[0] == ":" else False,
            )  # https://developer.android.com/guide/topics/manifest/service-element#proc

    @property
    def permission(self) -> str:
        return self.attributes.get("permission")

    @property
    def name(self) -> str:
        return self.attributes.get("name")

    @property
    def process_is_private(self) -> bool:
        return self._process_is_private

    @property
    def parent(self) -> Optional["Application"]:
        return self._parent

    @parent.setter
    def parent(self, parent: "Application") -> None:
        self._parent = parent


@dataclass(frozen=True)
class Data:
    _scheme: Union[str, List[str], None] = field(default=None)
    _host: Optional[str] = field(default=None)
    _port: Optional[str] = field(default=None)
    _path: Optional[str] = field(default=None)
    _path_pattern: Optional[str] = field(default=None)
    _path_prefix: Optional[str] = field(default=None)
    _mime_type: Optional[str] = field(default=None)

    def __post_init__(self):
        """Follows the rules for acceptable URIs"""
        self.uris = self.__create_uris()
        if not self._scheme:
            if self._mime_type:
                object.__setattr__(self, "_scheme", ["content", "file"])
            else:
                object.__setattr__(self, "_scheme", "*")
            self.__ignore_hosts()
            self.__ignore_paths()
        if not self._host:
            self.__ignore_hosts()
            self.__ignore_paths()
        if self._port:
            object.__setattr__(self, "_port", f":{self._port}")

    def __ignore_hosts(self) -> None:
        if self._host:
            object.__setattr__(self, "_host", "*")
        if self._port:
            object.__setattr__(self, "_port", None)

    def __ignore_paths(self) -> None:
        if self._path:
            object.__setattr__(self, "_path", None)
        if self._path_pattern:
            object.__setattr__(self, "_path_pattern", None)
        if self._path_prefix:
            object.__setattr__(self, "_path_prefix", None)

    def __get_paths(self) -> List[str]:
        """Combines all the path/pathPatterns/pathPrefixes into one list"""
        possible_paths = [self._path, self._path_pattern, f"{self._path_prefix}*"]
        return [x for x in possible_paths if x]

    def get_uris(self) -> List[str]:
        uris = set()
        # Because mimeType can make it [file: content:]
        if not isinstance(self._scheme, list):
            schemes = [self._scheme]
        else:
            schemes = self._scheme
        mime_type_extension = f" -t {self._mime_type}" if self._mime_type else ""
        for scheme in schemes:
            if scheme == "*":
                uris.add(f"{scheme}{mime_type_extension}")
                continue
            if self.host == "*":
                uris.add(f"{scheme}://{mime_type_extension}")
            else:
                possible_paths = [
                    f"{scheme}://{self.host}{self.port if self.port else ''}/{x if x else ''}{mime_type_extension}"
                    for x in [self.__get_paths()]
                ]
                for path in possible_paths:
                    uris.add(path)
        return list(uris)

    @property
    def scheme(self) -> Optional[str]:
        return self._scheme

    @property
    def host(self) -> Optional[str]:
        return self._host

    @property
    def port(self) -> Optional[str]:
        return self._port

    @property
    def mime_type(self) -> Optional[str]:
        return self._mime_type


class IntentType(Enum):
    IMPLICIT = 1
    EXPLICIT = 2
    IMPLICIT_PENDING = 3
    EXPLICIT_PENDING = 4


@dataclass(frozen=True, unsafe_hash=True)
class MetaData:
    attributes: dict = field(default_factory=dict)

    def from_xml(meta_data: Element) -> "MetaData":
        """Creates a MetaData object out of a xml meta-data tag \n
        Keyword arguments:
        \t meta_data: An meta-data Element object
        Returns:
        \t MetaData object
        """
        return MetaData(attributes=_xml.get_attributes(tag=meta_data))
