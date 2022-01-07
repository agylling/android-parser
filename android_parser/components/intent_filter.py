from xml.etree.ElementTree import Element
from typing import List, TYPE_CHECKING
from android_parser.utilities.log import log
from dataclasses import dataclass, field
from android_parser.utilities import (
    xml as _xml,
)
from android_parser.components.android_classes import IntentType, Data


def collect_intent_filters(self, parent: Element) -> List["IntentFilter"]:
    """Returns"""
    intent_filters = []
    for intent_filter in parent.findall("intent-filter"):
        intent_filters.append(IntentFilter.from_xml(intent_filter))
    return intent_filters


@dataclass
class IntentFilter:
    priority: int = field(default=0)
    order: int = field(default=0)
    actions: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    data: List["Data"] = field(default_factory=list)
    uris: List[str] = field(default_factory=list)
    parent_type: str = field(default=None)

    def __post_init__(self):
        self.uris = self.__create_uris()

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
        return list(uris)

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
            action_attribs = _xml.get_attributes(action)
            if action_attribs.get("name"):
                intent_actions.append(action_attribs.get("name"))
        # Categories
        intent_categories = []
        for category in intent_filter.findall("category"):
            category_attribs = _xml.get_attributes(category)
            if action_attribs.get("name"):
                intent_categories.append(category_attribs.get("name"))
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
