from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set
from xml.etree.ElementTree import Element

from android_parser.components.android_classes import (
    Base,
    BaseComponent,
    IntentType,
    MetaData,
    Permission,
)
from android_parser.components.intent_filter import IntentFilter
from android_parser.utilities import xml as _xml
from android_parser.utilities.log import log

if TYPE_CHECKING:
    from securicad.model.object import Object

    from android_parser.main import AndroidParser


@dataclass()
class Provider(BaseComponent):
    """Content Provider"""

    # https://developer.android.com/guide/topics/manifest/provider-element

    grant_uri_permissions: List[GrantURIPermission] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    path_permissions: List[PathPermission] = field(default_factory=list)
    # intent_filters and meta_datas from basecomponent

    def __post_init__(self):
        super().__post_init__()
        for obj in [*self.path_permissions, *self.grant_uri_permissions]:
            obj.parent = self
        self.attributes.setdefault("grantUriPermissions", False)
        if self.grant_uri_permissions:
            self.attributes["grantUriPermissions"] = True

    @property
    def write_permission(self) -> Optional[str]:
        return self.attributes.get("writePermission")

    @property
    def read_permission(self) -> Optional[str]:
        return self.attributes.get("readPermission")

    @property
    def wontGrantURIPermissions(self) -> bool:
        return self.attributes.get("wontGrantURIPermissions")  # type: ignore

    @property
    def asset_type(self) -> str:
        """The objects corresponding androidLang scad asset type"""
        return "ContentProvider"

    @staticmethod
    def from_xml(provider: Element) -> Provider:
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

        meta_datas: List[MetaData] = []
        for meta_data in provider.findall("meta-data"):
            meta_datas.append(MetaData.from_xml(meta_data))
        intent_filters = IntentFilter.collect_intent_filters(parent=provider)
        path_permissions: List[PathPermission] = []
        for path_permission in provider.findall("path-permission"):
            path_permissions.append(PathPermission.from_xml(path_permission))
        greant_uri_permissions: List[GrantURIPermission] = []
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

    def print_intents(self, intent_type: IntentType) -> List[str]:
        intent_type = intent_type
        if self.intent_filters and self.attributes["exported"] == False:
            log.info(
                f"Content provider {self.attributes['name']} has intent filters but is not exported. External components cannot reach it"
            )
        raise NotImplemented

    def create_scad_objects(self, parser: AndroidParser) -> None:
        super().create_scad_objects(parser=parser)
        parser.create_object(python_obj=self)
        if not parser:
            log.error(
                f"{__file__}: Cannot create an scad object without a valid parser"
            )
            return
        for path_perm in self.path_permissions:
            path_perm.create_scad_objects(parser=parser)
        # TODO: GrantURIPermission

    def connect_scad_objects(self, parser: AndroidParser) -> None:
        super().connect_scad_objects(parser=parser)
        provider_obj = parser.scad_id_to_scad_obj[self.id]  # type: ignore
        # Association externalAppsRequireReadPermissions
        if self.read_permission:
            read_perm_obj = self.manifest_parent.scad_permission_objs[
                self.read_permission
            ]
            parser.create_associaton(
                s_obj=provider_obj,
                t_obj=read_perm_obj,
                s_field="readPermission",
                t_field="readProviders",
            )
        # Association externalAppsRequireWritePermissions
        if self.write_permission:
            write_perm_obj = self.manifest_parent.scad_permission_objs[
                self.write_permission
            ]
            parser.create_associaton(
                s_obj=provider_obj,
                t_obj=write_perm_obj,
                s_field="readPermission",
                t_field="writeProviders",
            )
        # Association PathPermissions
        for path_perm in self.path_permissions:
            path_perm_obj = parser.scad_id_to_scad_obj[path_perm.id]  # type: ignore
            parser.create_associaton(
                s_obj=provider_obj,
                t_obj=path_perm_obj,
                s_field="pathPermissions",
                t_field="providers",
            )
        # Defense wontGrantURIPermissions
        provider_obj.defense("wontGrantURIPermissions").probability = (
            0.0 if self.wontGrantURIPermissions else 1.0
        )

    def _get_adb_intents(
        self, partial_intents: Set[str], options: bool = True
    ) -> List[str]:
        final_intents: List[str] = []
        option_flags: str = "--user all" if options else ""
        for path in [y for x in self.path_permissions for y in x.paths]:
            uri = f"content://{self.name}/{path}"
            for partial_intent in partial_intents:  # type: ignore
                final_intents.append(
                    f"adb shell content read --uri {uri} {option_flags} {partial_intent} -n {self.manifest_parent.package}/{self.name} > file.ext"
                )
                final_intents.append(
                    f"adb shell content write --uri {uri} {option_flags} {partial_intent} -n {self.manifest_parent.package}/{self.name} < file.ext "
                )
                final_intents.append(
                    f"adb shell content delete --uri {uri} {option_flags} {partial_intent} -n {self.manifest_parent.package}/{self.name}"
                )
        return final_intents


@dataclass(eq=True)
class PathPermission(Base):
    attributes: Dict[str, Any] = field(default_factory=dict)
    paths: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        for path in self.create_paths():
            self.paths.append(path)

    @property
    def permission(self) -> Optional[str]:
        return self.attributes.get("permission")

    @property
    def write_permission(self) -> Optional[str]:
        return self.attributes.get("writePermission")

    @property
    def read_permission(self) -> Optional[str]:
        return self.attributes.get("readPermission")

    @property  # type: ignore
    def parent(self) -> Provider:
        return self._parent

    @parent.setter  # type: ignore
    def parent(self, parent: Provider) -> None:
        self._parent = parent

    @staticmethod
    def from_xml(path_permission: Element) -> PathPermission:
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

    def create_scad_objects(self, parser: AndroidParser) -> None:
        """creates the androidLang securiCAD objects belonging to the component
        \n Keyword arguments:
        \t parser - an AndroidParser instance
        """
        super().create_scad_objects(parser)
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
            if self.write_permission:
                Permission.create_scad_android_permission(
                    parser=parser, name=self.write_permission, manifest_obj=manifest_obj
                )
            # read_permission
            if self.read_permission:
                Permission.create_scad_android_permission(
                    parser=parser, name=self.read_permission, manifest_obj=manifest_obj
                )
        # TODO: URIPermissions

    def connect_scad_objects(  # type: ignore
        self, parser: AndroidParser, called_by_cp: Provider
    ) -> None:
        """Creates the associations between the created scad objects
        \n Keyword arguments:
        \t parser - the AndroidParser instance that created the securiCAD objects
        \t called_by_cp - A ContentOrovider that has the PathPermission, so that we can reach the permission objects in the correct Manifest
        """

        def get_matching_paths(parser: AndroidParser, path: str) -> List[Object]:
            """Returns the closest matching directory or file in the filesystem that matches the path string
            \n Keyword arguments:
            \t parser - the AndroidParser instance that created the securiCAD objects
            \t path - a string that the path permission points to
            \n Returns:
            \t A list of securicad model Objects
            """
            pattern = path.replace("*", ".*")
            potential_objects: Dict[str, Object] = {
                x: obj
                for x, obj in parser.filesystem.paths.items()
                if re.match(pattern, x)
            }
            if not potential_objects:
                log.warning(
                    f"Found no matching directories or files for path {pattern}"
                )
                return []
            if not re.match("\.[a-zA-Z0-9]+", pattern):  # type: ignore
                shortest_match = min(potential_objects.keys(), key=len)
                return [
                    obj for x, obj in potential_objects.items() if x == shortest_match
                ]
            else:
                # Files, need to return all
                return [obj for obj in potential_objects.values()]

        path_perm = parser.scad_id_to_scad_obj[self.id]  # type: ignore

        super().connect_scad_objects(parser)
        for path in self.paths:
            if path == "*":
                t_objs: List[Object] = [
                    parser.scad_id_to_scad_obj[parser.filesystem.internal_volume.id],  # type: ignore
                    parser.scad_id_to_scad_obj[parser.filesystem.external_volume.id],  # type: ignore
                ]
            else:
                t_objs = get_matching_paths(parser=parser, path=path)
            for t_obj in t_objs:
                if t_obj.asset_type in ["InternalStorage", "ExternalStorage"]:
                    s_field = "partitions"
                elif t_obj.asset_type in ["Directory", "AppSpecificDirectory"]:
                    s_field = "directories"
                else:
                    s_field = "files"
                # Association AllowsAccessToPartition
                # Association AllowsAccessToDirectory
                # Association AllowsAccessToFile
                parser.create_associaton(
                    s_obj=path_perm,
                    t_obj=t_obj,
                    s_field=s_field,
                    t_field="pathPermissions",
                )

        permissions = called_by_cp.manifest_parent.scad_permission_objs
        # Association GeneralPathPermission
        if self.permission:
            android_perm = permissions[self.permission]
            parser.create_associaton(
                s_obj=path_perm,
                t_obj=android_perm,
                s_field="permission",
                t_field="pathPermissions",
            )
        # Association PathReadPermission
        if self.read_permission:
            read_perm = permissions[self.read_permission]
            parser.create_associaton(
                s_obj=path_perm,
                t_obj=read_perm,
                s_field="readPermission",
                t_field="readPathPermissions",
            )
        # Association PathWritePermission
        if self.write_permission:
            write_perm = permissions[self.write_permission]
            parser.create_associaton(
                s_obj=path_perm,
                t_obj=write_perm,
                s_field="writePermission",
                t_field="writePathPermissions",
            )


class GrantURIPermission(Base):
    attributes: Dict[str, Any] = field(default_factory=dict)
    paths: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for path in self.create_paths():
            self.paths.append(path)

    @property  # type: ignore
    def parent(self) -> Provider:
        return self._parent

    @parent.setter  # type: ignore
    def parent(self, parent: Provider) -> None:
        self._parent = parent

    @staticmethod
    def from_xml(grant_uri_permission: Element) -> GrantURIPermission:
        """Creates a PathPermission object out of a xml grant-uri-permission tag \n
        Keyword arguments:
        \t grant-uri-permission: An grant-uri-permission Element object
        Returns:
        \t GrantURIPermission object
        """
        attribs = _xml.get_attributes(tag=grant_uri_permission)
        return GrantURIPermission(attributes=attribs)  # type: ignore

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
