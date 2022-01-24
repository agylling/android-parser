from xml.etree.ElementTree import Element
from typing import List, TYPE_CHECKING, Optional, Union
from android_parser.utilities.log import log
from dataclasses import dataclass, field
from android_parser.utilities import (
    xml as _xml,
)
from android_parser.components.android_classes import IntentType, Base

if TYPE_CHECKING:
    from android_parser.main import AndroidParser
    from android_parser.components.application import Application, AndroidComponent


@dataclass
class Intent(Base):
    _parent: "Application" = field()
    targets: List["AndroidComponent"] = field(default_factory=list)

    @property
    def name(self) -> str:
        return "Intent"

    @property
    def asset_type(self) -> str:
        return "Intent"

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        """creates an Intent androidLang securiCAD object
        \nKeyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)

    def connect_scad_objects(self, parser: "AndroidParser") -> None:
        super().connect_scad_objects(parser)
        application_obj = self.parent
        intent_scad_obj = parser.scad_id_to_scad_obj[self.id]
        # Association CreateIntent
        parser.create_associaton(
            s_obj=application_obj,
            t_obj=intent_scad_obj,
            s_field="intents",
            t_field="app",
        )
        for target in self.targets:
            target_scad_obj = parser.scad_id_to_scad_obj[target.id]
            # Association startComponent
            parser.create_associaton(
                s_obj=intent_scad_obj,
                t_obj=target_scad_obj,
                s_field="components",
                t_field="intents",
            )
        intent_filters = self.parent.intent_fitlers
        for intent_filter in intent_filters:
            for action in intent_filter.actions:
                action_scad_obj = parser.scad_id_to_scad_obj[action.id]
                # Association IntentAction
                parser.create_associaton(
                    s_obj=intent_scad_obj,
                    t_obj=action_scad_obj,
                    s_field="actions",
                    t_field="intents",
                )
            for category in intent_filter.categories:
                cat_scad_obj = parser.scad_id_to_scad_obj[category.id]
                # Association IntentCategory
                parser.create_associaton(
                    s_obj=intent_scad_obj,
                    t_obj=cat_scad_obj,
                    s_field="categories",
                    t_field="intents",
                )
            for uri in intent_filter.uris:
                uri_scad_obj = parser.scad_id_to_scad_obj[uri.id]
                # Association IntentURI
                parser.create_associaton(
                    s_obj=intent_scad_obj,
                    t_obj=uri_scad_obj,
                    s_field="uris",
                    t_field="intents",
                )


@dataclass()
class Action(Base):
    attributes: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.attributes.get("name")

    @property
    def asset_type(self) -> str:
        if self.name.endswith("action.VIEW"):
            return "ACTION_VIEW"
        else:
            return "Action"

    def from_xml(action: Element) -> "Action":
        """Creates an Action object out of a xml action tag \n
        Keyword arguments:
        \t action: An action Element object
        Returns:
        \t Action object
        """
        return Action(attributes=_xml.get_attributes(tag=action))

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)


@dataclass()
class Category(Base):
    attributes: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.attributes.get("name")

    @property
    def asset_type(self) -> str:
        if self.name.endswith("category.BROWSABLE"):
            return "CategoryDefault"
        elif self.name.endswith("category.DEFAULT"):
            return "CategoryBrowsable"
        else:
            return "Category"

    def from_xml(category: Element) -> "Category":
        """Creates a Category object out of a xml category tag \n
        Keyword arguments:
        \t category: An category Element object
        Returns:
        \t Category object
        """
        return Category(attributes=_xml.get_attributes(tag=category))

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)


@dataclass()
class URI(Base):
    _name: str = field()

    @property
    def asset_type(self) -> str:
        return "Data"

    @property
    def name(self) -> str:
        return self._name

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        parser.create_object(python_obj=self)


@dataclass()
class Data(Base):
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


@dataclass(eq=True)
class IntentFilter(Base):
    priority: int = field(default=0)
    order: int = field(default=0)
    actions: List["Action"] = field(default_factory=list)
    categories: List["Category"] = field(default_factory=list)
    data: List["Data"] = field(default_factory=list)
    uris: List["URI"] = field(default_factory=list)
    parent_type: str = field(default=None)

    @property
    def name(self) -> str:
        return f"IntentFilter"

    def __post_init__(self):
        object.__setattr__(self, "uris", self.__create_uris())

    def __create_uris(self) -> List[str]:
        """Creates a list of URI strings that can be matched against the data tags of the intent filter
        Returns:
        \tList of uri strings
        """
        uris = set()
        # <scheme>://<host>:<port>[<path>|<pathPrefix>|<pathPattern>]
        for data_obj in self.data:
            for path in data_obj.get_uris():
                uris.add(path)
        # All the different combinations of each other (deep links)
        # https://developer.android.com/training/app-links/deep-linking
        schemes = [x.scheme for x in self.data if x.scheme]
        hosts = [x.host for x in self.data if x.host]
        ports = [x.port for x in self.data if x.port]
        mime_types = [x.mime_type for x in self.data if x.mime_type]
        paths = set()
        for path_list in [x.get_paths() for x in self.data]:
            for path in path_list:
                if path:
                    paths.append(path)
        paths = list(paths)
        for x in [
            f"{scheme}://{self.host}{self.port if self.port else ''}/{path}"
            for scheme in schemes
            for host in hosts
            for port in ports
            for path in paths
        ]:
            if mime_types:
                for mime_type in mime_types:
                    uris.add(f"{path} -t {mime_type}")
            else:
                uris.add(path)
        return [URI(_name=uri) for uri in list(uris)]

    def from_xml(intent_filter: Element, parent_type: str) -> "IntentFilter":
        """Creates an IntentFilter object out of a xml intent-filter tag \n
        Keyword arguments:
        \intent_filter: An intent-filter Element object
        \tparent_type: The xml tag type of the intent-filters parent
        Returns:
        \t IntentFilter object
        """
        attribs = _xml.get_attributes(intent_filter)
        # Actions
        intent_actions = []
        for action in intent_filter.findall("action"):
            intent_actions.append(Action.from_xml(action=action))
        # Categories
        intent_categories = []
        for category in intent_filter.findall("category"):
            intent_categories.append(Category.from_xml(category=category))
        # Data
        intent_data = []
        for data_tag in intent_filter.findall("data"):
            data_attribs = _xml.get_attributes(data_tag)
            scheme = data_attribs.get("scheme")
            data = Data(
                _scheme=scheme,
                _host=data_attribs.get("scheme"),
                _port=data_attribs.get("port"),
                _path=data_attribs.get("path"),
                _path_pattern=data_attribs.get("pathPattern"),
                _path_prefix=data_attribs.get("pathPrefix"),
                _mime_type=data_attribs.get("mimeType"),
            )
            intent_data.append(data)
        return IntentFilter(
            priority=attribs.get("priority", 0),
            order=attribs.get("order", 0),
            actions=intent_actions,
            categories=intent_categories,
            data=intent_data,
            parent_type=parent_type,
        )

    def collect_intent_filters(parent: Element) -> List["IntentFilter"]:
        """Returns a list of IntentFilter objects found within the parent xml tag
        \n Keyword arguments:
        \t parent - an android component xml tag, e.g. service, activity, receiver or provider
        \n Returns
            A list if IntentFilter objects
        """
        intent_filters = []
        for intent_filter in parent.findall("intent-filter"):
            intent_filters.append(
                IntentFilter.from_xml(intent_filter, parent_type=parent.tag)
            )
        return intent_filters

    def print_partial_intent(self) -> List[str]:
        """Prints the intent filter part of an intent, meaning the actions, categories and uris\n"""
        # https://developer.android.com/studio/command-line/adb#IntentSpec
        partial_intent_strings = set()
        for action in self.actions:
            for category in self.categories:
                for uri in self.uris:
                    # mime type flags (-t) are already hardcoded into the uri
                    partial_intent_strings.add(f"-a {action} -c {category} -d {uri}")
        return list(partial_intent_strings)

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        super().create_scad_objects(parser)
        # TODO: Can probably create globally unique URIs
        parser.create_object(asset_type="IntentFilter", python_obj=self)
        for category in self.categories:
            category.create_scad_objects(parser=parser)
        for action in self.actions:
            action.create_scad_objects(parser=parser)
        for uri in self.uris:
            uri.create_scad_objects(parser=parser)
        # TODO order
        # TODO priority

    def connect_scad_objects(self, parser: "AndroidParser") -> None:
        super().connect_scad_objects(parser)
        intent_filter_scad_obj = parser.scad_id_to_scad_obj[self.id]
        component_obj = parser.scad_id_to_scad_obj[self.parent.id]
        # Association IntentFilter
        parser.create_associaton(
            s_obj=intent_filter_scad_obj,
            t_obj=component_obj,
            s_field="component",
            t_field="intentFilters",
        )
        for action in self.actions:
            action_scad_obj = parser.scad_id_to_scad_obj[action.id]
            # Association IntentAction
            parser.create_associaton(
                s_obj=intent_filter_scad_obj,
                t_obj=action_scad_obj,
                s_field="actions",
                t_field="intentFilters",
            )
        for category in self.categories:
            cat_scad_obj = parser.scad_id_to_scad_obj[category.id]
            # Association IntentCategory
            parser.create_associaton(
                s_obj=intent_filter_scad_obj,
                t_obj=cat_scad_obj,
                s_field="categories",
                t_field="intentFilters",
            )
        for uri in self.uris:
            uri_scad_obj = parser.scad_id_to_scad_obj[uri.id]
            # Association IntentData
            parser.create_associaton(
                s_obj=intent_filter_scad_obj,
                t_obj=uri_scad_obj,
                s_field="data",
                t_field="intentFilters",
            )
