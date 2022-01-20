from xml.etree.ElementTree import Element
from typing import Optional, List, TYPE_CHECKING
from android_parser.utilities.log import log
from dataclasses import dataclass, field
from android_parser.utilities import (
    xml as _xml,
)
from android_parser.components.android_classes import BaseComponent, MetaData
from android_parser.components.intent_filter import IntentFilter, IntentType
from android_parser.components.android_classes import Permission, Base

if TYPE_CHECKING:
    from android_parser.components.application import Application
    from android_parser.main import AndroidParser


@dataclass()
class Provider(BaseComponent):
    """Content Provider"""

    # https://developer.android.com/guide/topics/manifest/provider-element

    grant_uri_permissions: List["GrantURIPermission"] = field(default_factory=list)
    attributes: dict = field(default_factory=dict)
    path_permissions: List["PathPermission"] = field(default_factory=list)
    # intent_filters and meta_datas from basecomponent

    def __post_init__(self):
        super().__post_init__()
        for obj in [*self.path_permissions, *self.grant_uri_permissions]:
            obj.parent = self

    @property
    def write_permission(self) -> Optional[str]:
        return self.attributes.get("writePermission")

    @property
    def read_permission(self) -> Optional[str]:
        return self.attributes.get("readPermission")

    @property
    def asset_type(self) -> str:
        """The objects corresponding androidLang scad asset type"""
        return "ContentProvider"

    def from_xml(provider: Element) -> "Provider":
        """Creates a Provider object out of a xml provider tag \n
        Keyword arguments:
        \t provider: An provider Element object
        Returns:
        \t Provider object
        """
        attribs = _xml.get_attributes(provider)
        attribs.setdefault("allowEmbedded", False)
        attribs.setdefault("allowTaskReparenting", False)
        attribs.setdefault("directBootAware", False)
        attribs.setdefault("enabled", True)
        attribs.setdefault("multiprocess", False)
        # TODO: Exported default depends on api level https://developer.android.com/guide/topics/manifest/provider-element#exported

        meta_datas = []
        for meta_data in provider.findall("meta-data"):
            meta_datas.append(MetaData.from_xml(meta_data))
        intent_filters = IntentFilter.collect_intent_filters(parent=provider)
        path_permissions = []
        for path_permission in provider.findall("path-permission"):
            path_permissions.append(PathPermission.from_xml(path_permission))
        greant_uri_permissions = []
        for grant_uri_permission in provider.findall("grant-uri-permission"):
            greant_uri_permissions.append(
                GrantURIPermission.from_xml(grant_uri_permission)
            )
        return Provider(
            attributes=attribs,
            meta_datas=meta_datas,
            intent_filters=intent_filters,
            grant_uri_permissions=greant_uri_permissions,
            path_permissions=path_permissions,
        )

    def print_intents(self, intent_type: "IntentType") -> List[str]:
        if self.intent_filters and self.attribs["exported"] == False:
            log.info(
                f"Content provider {self.attribs['name']} has intent filters but is not exported. External components cannot reach it"
            )
        raise NotImplemented

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        super().create_scad_objects(parser=parser)
        if not parser:
            log.error(
                f"{__file__}: Cannot create an scad object without a valid parser"
            )
            return
        for path_perm in self.path_permissions:
            path_perm.create_scad_objects(parser=parser)

    def connect_scad_objects(self, parser: "AndroidParser") -> None:
        super().connect_scad_objects(parser)


@dataclass(eq=True)
class PathPermission(Base):
    attributes: dict = field(default_factory=dict)
    paths: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for path in self.create_paths():
            self.paths.append(path)

    @property
    def write_permission(self) -> Optional[str]:
        return self.attributes.get("writePermission")

    @property
    def read_permission(self) -> Optional[str]:
        return self.attributes.get("readPermission")

    def from_xml(path_permission: Element) -> "PathPermission":
        """Creates a PathPermission object out of a xml path-permission tag \n
        Keyword arguments:
        \t path_permission: An path-permission Element object
        Returns:
        \t PathPermission object
        """
        return PathPermission(attributes=_xml.get_attributes(tag=path_permission))

    def create_paths(self) -> List[str]:
        """returns the paths possible for the PathPermission"""
        tmp_path_prefix = (
            f"{self.attributes['pathPrefix']}*"
            if self.attributes.get("pathPrefix")
            else None
        )
        potential_paths = [
            self.attributes.get("path"),
            tmp_path_prefix,
            self.attributes.get("pathPattern"),
        ]
        return [x for x in potential_paths if x]

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        """creates the androidLang securiCAD objects belonging to the component
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        parser.create_object(asset_type="PathPermission", python_obj=self)
        # paths are handled in connect (searhing for directories, files etc.)
        # write_permission
        try:
            manifest_obj = self.parent.manifest_parent
        except AttributeError:
            log.error(
                f"Couldn't find the Manifest parent of PathPermission's Provider parent {self.parent.name}"
            )
            manifest_obj = None
        if manifest_obj:
            Permission.create_scad_android_permission(
                parser=parser, name=self.write_permission, manifest_obj=manifest_obj
            )
            # read_permission
            Permission.create_scad_android_permission(
                parser=parser, name=self.read_permission, manifest_obj=manifest_obj
            )
        # TODO: URIPermissions


class GrantURIPermission(Base):
    attributes: dict = field(default_factory=dict)
    paths: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for path in self.create_paths():
            self.paths.append(path)

    def from_xml(grant_uri_permission: Element) -> "GrantURIPermission":
        """Creates a PathPermission object out of a xml grant-uri-permission tag \n
        Keyword arguments:
        \t grant-uri-permission: An grant-uri-permission Element object
        Returns:
        \t GrantURIPermission object
        """
        return GrantURIPermission(
            attributes=_xml.get_attributes(tag=grant_uri_permission)
        )

    def create_paths(self) -> List[str]:
        """returns the paths possible for the PathPermission"""
        tmp_path_prefix = (
            f"{self.attributes['pathPrefix']}*"
            if self.attributes.get("pathPrefix")
            else None
        )
        potential_paths = [
            self.attributes.get("path"),
            tmp_path_prefix,
            self.attributes.get("pathPattern"),
        ]
        return [x for x in potential_paths if x]
