from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Union
from xml.etree.ElementTree import Element

from android_parser.utilities import constants as constants
from android_parser.utilities import xml as _xml
from android_parser.utilities.log import log

if TYPE_CHECKING:
    from securicad.model.object import Object

    from android_parser.components.application import Application
    from android_parser.components.hardware import SystemApp
    from android_parser.components.intent_filter import IntentFilter
    from android_parser.components.manifest import Manifest
    from android_parser.main import AndroidParser
    from android_parser.utilities.malicious_application import MaliciousApp


class MissingAndroidParser(Exception):
    pass


@dataclass()
class Base:
    _id: Optional[int] = field(default=None, init=False)
    _parent: Any = field(default=None, init=False)

    def __post_init__(self) -> None:
        pass

    def to_dict(self) -> Dict[Any, Any]:
        def has_id_type(object: Any) -> bool:
            return True if hasattr(object, "id") else False

        attributes = {attrib: value for attrib, value in self.__dict__.items()}
        for key, attrib in attributes.items():
            if isinstance(attrib, list):
                attrib = [{"scad_id": x.id} if has_id_type(x) else x for x in attrib]  # type: ignore
            elif isinstance(attrib, dict):
                pass
            else:
                attrib = {"scad_id": attrib.id} if has_id_type(attrib) else attrib
            attributes[key] = attrib
        return attributes

    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, id: int) -> None:
        if not isinstance(id, int):  # type: ignore
            log.error(f"id property need to be of int type, was {type(id)}: {id}")
        self._id = id

    @property
    def parent(self) -> Optional[Any]:
        return self._parent

    @parent.setter
    def parent(self, parent: Any) -> None:
        self._parent = parent

    @property
    def asset_type(self) -> str:
        """Returns the correpsonding androidLang securiCAD object of the class"""
        ...

    def create_scad_objects(self, parser: AndroidParser) -> None:
        """creates the androidLang securiCAD object(s) belonging to the object
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        if not parser:
            log.error(f"Cannot create an scad object without a valid parser")
            raise MissingAndroidParser
        # Don't want to add parser.create_object(python_obj=self) because some classes overrides the asset_type

    def connect_scad_objects(self, parser: AndroidParser) -> None:
        """Creates the associations between the created scad objects
        \n Keyword arguments:
        \t parser - the AndroidParser instance that created the securiCAD objects
        """
        if not parser:
            log.error(f"Cannot connect scad objects without a valid parser")
            raise MissingAndroidParser


class IntentType(Enum):
    IMPLICIT = 1
    EXPLICIT = 2
    IMPLICIT_PENDING = 3
    EXPLICIT_PENDING = 4


@dataclass(eq=True)
class MetaData(Base):
    attributes: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_xml(meta_data: Element) -> MetaData:
        """Creates a MetaData object out of a xml meta-data tag \n
        Keyword arguments:
        \t meta_data: An meta-data Element object
        Returns:
        \t MetaData object
        """
        return MetaData(attributes=_xml.get_attributes(tag=meta_data))


@dataclass(eq=True)
class PermissionGroup(Base):
    attributes: Dict[str, Any] = field(default_factory=dict)
    id: int = field(default=None, init=None)  # type: ignore

    @property
    def name(self) -> str:
        return self.attributes.get("name")  # type: ignore

    @property
    def asset_type(self) -> str:
        return "PermissionGroup"

    @property
    def description(self) -> str:
        """The name for a logical grouping of related permissions that permission objects join to"""
        return self.attributes.get("description")  # type: ignore

    @staticmethod
    def from_xml(permission_group: Element) -> PermissionGroup:
        """Creates an PermissionGroup object out of a permission_group tag \n
        Keyword arguments:
        \t permission_group: An permission-group Element object
        Returns:
        \t PermissionGroup object
        """
        attribs = _xml.get_attributes(tag=permission_group)
        return PermissionGroup(attributes=attribs)

    @staticmethod
    def collect_permission_groups(tag: Element) -> Dict[str, PermissionGroup]:
        """Collects all permission-group tags below the provided xml tag.
        \n Keyword arguments:
        \t tag - a manifest xml tag
        \n Returns:
        \t A list of PermissionGroup objects
        """
        permission_groups: Dict[str, PermissionGroup] = {}
        for permission_grp in tag.findall("permission-group"):
            permission_grp = PermissionGroup.from_xml(permission_group=permission_grp)
            permission_groups[permission_grp.name] = permission_grp
        return permission_groups

    def create_scad_objects(self, parser: AndroidParser) -> None:
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)


@dataclass(eq=True)
class PermissionTree(Base):
    attributes: Dict[str, Any] = field(default_factory=dict)
    id: int = field(default=None, init=None)  # type: ignore

    @property
    def name(self) -> str:
        return self.attributes.get("name")  # type: ignore

    @property
    def asset_type(self) -> str:
        return "PermissionTree"

    @staticmethod
    def from_xml(permission_tree: Element) -> PermissionTree:
        """Creates an PermissionTree object out of a permission-tree tag \n
        Keyword arguments:
        \t permission_tree: An permission-tree Element object
        Returns:
        \t PermissionTree object
        """
        attribs = _xml.get_attributes(tag=permission_tree)
        return PermissionTree(attributes=attribs)

    @staticmethod
    def collect_permission_trees(tag: Element) -> Dict[str, PermissionTree]:
        """Collects all permission-tree tags below the provided xml tag.
        \n Keyword arguments:
        \t tag - a manifest xml tag
        \n Returns:
        \t A list of PermissionTree objects
        """
        permission_trees: Dict[str, PermissionTree] = {}
        for permission_tree in tag.findall("permission-tree"):
            permission_tree = PermissionTree.from_xml(permission_tree=permission_tree)
            permission_trees[permission_tree.name] = permission_tree
        return permission_trees

    def create_scad_objects(self, parser: AndroidParser) -> None:
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)


@dataclass(eq=True)
class Permission(Base):
    attributes: Dict[str, Any] = field(default_factory=dict)
    _asset_type: str = field(default="Permission", init=False)

    @property
    def name(self) -> str:
        return self.attributes.get("name")  # type: ignore

    @property
    def permission_group(self) -> Optional[str]:
        return self.attributes.get("permissionGroup")

    @property
    def protection_level(self) -> Optional[str]:
        return self.attributes.get("protectionLevel")

    @property
    def asset_type(self) -> str:
        return self._asset_type

    @asset_type.setter
    def asset_type(self, asset_type: str) -> None:
        self._asset_type = asset_type

    def __post_init__(self) -> None:
        super().__post_init__()
        self.attributes.setdefault("protectionLevel", "signature")

    @staticmethod
    def from_xml(permission: Element) -> Permission:
        """Creates an Permission object out of a permission tag \n
        Keyword arguments:
        \t permission: An permission Element object
        Returns:
        \t Permission object
        """
        attribs = _xml.get_attributes(tag=permission)
        return Permission(attributes=attribs)

    @staticmethod
    def collect_permissions(tag: Element) -> List[Permission]:
        """Collects all permission tags below the provided xml tag.
        \n Keyword arguments:
        \t tag - a manifest xml tag
        \n Returns:
        \t A list of Permission objects
        """
        permissions: List[Permission] = []
        for permission in tag.findall("permission"):
            permissions.append(Permission.from_xml(permission=permission))
        return permissions

    @staticmethod
    def _permission_in_lang(parser: AndroidParser, asset_type: str) -> str:
        """Determines if the permission is a dedicated object in androidLang or not
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        \t asset_type - a permission name string
        \n Returns:
        \t Permission if asset_type isn't in language, else asset_type
        """
        if asset_type not in parser.lang.assets:
            log.info(
                f"{asset_type} not yet in the language, switching to generic Permission"
            )
            return "Permission"
        return asset_type

    def create_scad_objects(self, parser: AndroidParser) -> None:
        """creates the androidLang securiCAD objects belonging to the component
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        base = Permission._trim_android_permission(self.name)
        self.asset_type = Permission._permission_in_lang(parser=parser, asset_type=base)
        parser.create_object(python_obj=self)

    def connect_scad_objects(self, parser: AndroidParser) -> None:
        super().connect_scad_objects(parser)
        # Defense normal, dangerous, signature, signatureOrSystem
        permission_obj = parser.scad_id_to_scad_obj[self.id]  # type: ignore
        protection_levels = self.attributes["protectionLevel"].split("|")
        for protection_level in protection_levels:
            permission_obj.defense(protection_level).probability = 1.0

    @staticmethod
    def _trim_android_permission(name: str) -> str:
        if "android.permission." in name:
            return name.replace("android.permission.", "")
        return name

    @staticmethod
    def create_scad_android_permission(
        parser: AndroidParser, name: str, manifest_obj: Manifest
    ) -> Optional[Object]:
        """Creates an Permission scad object from a str representation of a permission attribute
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        \t name - the name of the action to create
        \t manifest_obj - The Manifest object the permission will belong to. Prevent duplicate permission scad objects being created
        \n Returns:
        \t An scad Permission object or None
        """
        if not name:
            return None
        if not parser:
            log.error(f"Cannot create an scad object without a valid parser")
            raise MissingAndroidParser
        existing_permission_names = set(manifest_obj.scad_permission_objs.keys())
        if name in existing_permission_names:
            log.info(f"{name} was already in ignore")
            return None
        log.info(
            f"An android permission {name} wasn't listed in the manifest with a <permission> tag"
        )
        asset_type = Permission._permission_in_lang(
            parser=parser, asset_type=Permission._trim_android_permission(name=name)
        )
        permission_obj = parser.create_object(asset_type=asset_type, name=name)
        manifest_obj.scad_permission_objs[permission_obj.name] = permission_obj  # type: ignore
        return permission_obj


@dataclass()
class UID(Base):
    _name: str = field()
    _parent: Union[Application, SystemApp, MaliciousApp] = field()

    @property
    def asset_type(self) -> str:
        return "UID"

    @property
    def name(self) -> str:
        return self._name

    @property  # type: ignore
    def parent(self) -> Union[Application, SystemApp, MaliciousApp]:
        return self._parent

    def create_scad_objects(self, parser: AndroidParser) -> None:
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)

    def connect_scad_objects(self, parser: AndroidParser) -> None:
        super().connect_scad_objects(parser)
        parent = self.parent
        app = parser.scad_id_to_scad_obj[parent.id]  # type: ignore
        uid = parser.scad_id_to_scad_obj[self.id]  # type: ignore
        parser.create_associaton(
            s_obj=app,
            t_obj=uid,
            s_field="uid",
            t_field="app",
        )


@dataclass(eq=True)
class UsesPermission(Base):
    attributes: Dict[str, Any] = field(default_factory=dict)

    @property
    def max_sdk_version(self) -> Optional[int]:
        return self.attributes.get("maxSdkVersion")  # type: ignore

    @property
    def name(self) -> str:
        return self.attributes.get("name")  # type: ignore

    @property
    def asset_type(self) -> str:
        return "UsesPermission"

    @staticmethod
    def from_xml(uses_permission: Element) -> UsesPermission:
        """Creates an UsesPermission object out of a uses-permission tag \n
        Keyword arguments:
        \t uses-permission: An uses-permission Element object
        Returns:
        \t UsesPermission object
        """
        attribs = _xml.get_attributes(tag=uses_permission)
        return UsesPermission(attributes=attribs)

    @staticmethod
    def collect_uses_permissions(tag: Element) -> List[UsesPermission]:
        """Collects all uses-permission tags below the provided xml tag.
        \n Keyword arguments:
        \t tag - a manifest xml tag
        \n Returns:
        \t A list of UsesPermission objects
        """
        uses_permissions: List[UsesPermission] = []
        for uses_permission in tag.findall("uses-permission"):
            uses_permissions.append(
                UsesPermission.from_xml(uses_permission=uses_permission)
            )
        return uses_permissions

    def create_scad_objects(self, parser: AndroidParser) -> None:
        super().connect_scad_objects(parser)
        parser.create_object(python_obj=self)


@dataclass(eq=True)
class UsesPermission23(UsesPermission):
    # https://developer.android.com/guide/topics/manifest/uses-permission-sdk-23-element

    @property
    def asset_type(self) -> str:
        return "UsesPermissionSdk23"

    @staticmethod
    def from_xml(uses_permission_sdk_23: Element) -> UsesPermission23:  # type: ignore
        """Creates an UsesPermission23 object out of a uses-permission-sdk-23 tag \n
        Keyword arguments:
        \t uses-permission: An uses-permission-sdk-23 Element object
        Returns:
        \t UsesPermission23 object
        """
        attribs = _xml.get_attributes(tag=uses_permission_sdk_23)
        return UsesPermission23(attributes=attribs)

    @staticmethod
    def collect_uses_permissions(tag: Element) -> List[UsesPermission23]:  # type: ignore
        """Collects all uses-permission-sdk-23 tags below the provided xml tag.
        \n Keyword arguments:
        \t tag - a manifest xml tag
        \n Returns:
        \t A list of UsesPermission23 objects
        """
        uses_permissions: List[UsesPermission23] = []
        for uses_permission in tag.findall("uses-permission-sdk-23"):
            uses_permissions.append(
                UsesPermission23.from_xml(uses_permission_sdk_23=uses_permission)
            )
        return uses_permissions


@dataclass
class BaseComponent(Base):
    # Shared attributes between Activity, BroadcastReceiver, ContentProvider and Service
    attributes: Dict[str, Any] = field(default_factory=dict)
    _process_is_private: bool = field(default=False, repr=False, init=False)
    _parent: Application = field(default=None, init=False)  # type: ignore
    # Shared tags
    meta_datas: List[MetaData] = field(default_factory=list)
    intent_filters: List[IntentFilter] = field(default_factory=list)
    _process: Optional[UID] = field(default=None, init=False)

    def __post_init__(self):
        if self.attributes.get("process"):
            object.__setattr__(
                self,
                "_process_is_private",
                True if self.attributes.get("process", "")[0] == ":" else False,
            )  # https://developer.android.com/guide/topics/manifest/service-element#proc
            procces_name = self.attributes.get("process")
            object.__setattr__(self, "_process", UID(_parent=self, _name=procces_name))  # type: ignore
        self.attributes.setdefault("enabled", True)
        self.attributes.setdefault("exported", False)
        for component in [*self.intent_filters, *self.meta_datas]:
            if not component:
                continue
            component.parent = self

    def to_dict(self) -> Dict[Any, Any]:
        attributes = super().to_dict()
        adb_intents, web_intents = self.get_intents()
        attributes["adbIntents"] = adb_intents
        attributes["chromeIntents"] = web_intents
        return attributes

    @property
    def permission(self) -> Optional[str]:
        return self.attributes.get("permission")  # type: ignore

    @property
    def name(self) -> str:
        return self.attributes.get("name")  # type: ignore

    @property
    def process(self) -> UID:
        return self._process  # type: ignore

    @property
    def enabled(self) -> bool:
        return self.attributes.get("enabled", True)  # type: ignore

    @property
    def exported(self) -> bool:
        return self.attributes.get("exported")  # type: ignore

    @property
    def process_is_private(self) -> bool:
        return self._process_is_private

    @property
    def parent(self) -> Application:
        return self._parent

    @parent.setter
    def parent(self, parent: Application) -> None:
        self._parent = parent

    @property
    def asset_type(self) -> str:
        ...

    @property
    def manifest_parent(self) -> Manifest:
        """The parent of the android component's parent should be a Manifest python object"""
        return self.parent.parent

    def create_scad_objects(self, parser: AndroidParser) -> None:
        """creates the androidLang securiCAD objects belonging to the component
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
        # Intent_filters
        for intent_filter in self.intent_filters:
            intent_filter.create_scad_objects(parser=parser)
        # Permission
        if self.attributes.get("permission"):
            try:
                manifest_obj = self.manifest_parent
                if not hasattr(manifest_obj, "permissions"):
                    log.error(
                        f"parent.parent of {self.name} of type {self.asset_type} is not of type Manifest. Cannot determine package permissions"
                    )
                    return
            except AttributeError:
                log.error(
                    f"Cannot reach the manifest parent of {self.name} of type {self.asset_type}"
                )
                return
            Permission.create_scad_android_permission(
                parser=parser,
                name=self.permission,  # type: ignore
                manifest_obj=manifest_obj,
            )
        # Process
        if self.process:
            parser.create_object(python_obj=self.process)

    def connect_scad_objects(self, parser: AndroidParser) -> None:
        super().connect_scad_objects(parser)
        component = parser.scad_id_to_scad_obj[self.id]  # type: ignore
        # Association SeperateProcess
        if self.attributes.get("process"):
            process_scad_obj = parser.scad_id_to_scad_obj[self.process.id]  # type: ignore
            parser.create_associaton(
                s_obj=process_scad_obj,
                t_obj=component,
                s_field="component",
                t_field="process",
            )
        manifest_parent = self.manifest_parent
        # Association AndroidPermission
        if self.permission:
            permission = manifest_parent.scad_permission_objs[self.permission]
            parser.create_associaton(
                s_obj=component,
                t_obj=permission,
                s_field="androidPermission",
                t_field="component",
            )
        # Defense notEnabled
        component.defense("notEnabled").probability = 0.0 if self.enabled else 1.0
        # Defense notExported
        component.defense("notExported").probability = 0.0 if self.exported else 1.0
        # Defense notUsingIntentExtras
        # TODO: A static code analysis scanner to determine this probability
        component.defense("notUsingIntentExtras").probability = 0.5
        # Intent_filters
        for intent_filter in self.intent_filters:
            intent_filter.connect_scad_objects(parser=parser)

    def get_intents(self) -> Tuple[List[str], List[str]]:
        """Returns a list of potentially possible intents to access to component"""
        total_partial_adb_intents: Set[str] = set()
        total_browser_intents: Set[str] = set()
        for intent_filter in self.intent_filters:
            adb_intents, chrome_intents = intent_filter.print_partial_intent()
            total_partial_adb_intents.union(adb_intents)
            total_browser_intents.union(chrome_intents)
        total_adb_intents: List[str] = self._get_adb_intents(
            partial_intents=total_partial_adb_intents
        )
        return (total_adb_intents, list(total_browser_intents))  # type: ignore

    def _get_adb_intents(
        self, partial_intents: Set[str], options: bool = True
    ) -> List[str]:
        """Returns a list of potential valid intents using adb commands for the components that matches its intent filters
        \n Keyword arguments:
        \t partial_intents - a set of partially done intent strings from the components intent_filters.print_partial_intent()[0]
        \t options - to include predefined options flags defined defined in the component's definition of this function
        """
        ...
