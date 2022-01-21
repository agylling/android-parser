from xml.etree.ElementTree import Element
from typing import List, Tuple, TYPE_CHECKING, Dict, Union
from android_parser.utilities.log import log
from dataclasses import dataclass, field
from android_parser.utilities import (
    xml as _xml,
    constants as constants,
)
import json

from android_parser.components.application import Application
from android_parser.components.android_classes import (
    Permission,
    PermissionGroup,
    UsesPermission,
    UsesPermission23,
    PermissionTree,
)

if TYPE_CHECKING:
    from android_parser.main import AndroidParser
    from securicad.model.object import Object
    from android_parser.components.filesystem import FileSystem


def collect_manifest(manifest: Element, parser: "AndroidParser") -> "Manifest":
    """Creates a Manifest object out of a manifest xml object
    \nKeyword arguments:
    \t manifest - a manifest xml Element
    \t parser - The AndroidParser initiaing the parsing of the manifest
    \nReturns:
    \t A Manifest object
    """
    return Manifest.from_xml(manifest, parser)


@dataclass()
class Manifest:
    _parser: "AndroidParser" = field(default=None)
    _target_sdk_version: int = field(default=None)
    _min_sdk_version: int = field(default=None)
    attributes: dict = field(default_factory=dict)
    permissions: List["Permission"] = field(default_factory=list)
    scad_permission_objs: Dict[str, "Object"] = field(
        default_factory=dict, init=False, repr=False
    )
    uses_permissions: List["UsesPermission"] = field(default_factory=list)
    uses_permissions_sdk_23: List["UsesPermission23"] = field(default_factory=list)
    permission_groups: Dict[str, "PermissionGroup"] = field(default_factory=dict)
    permission_trees: Dict[str, "PermissionTree"] = field(default_factory=dict)
    applications: List["Application"] = field(default_factory=list)
    _api_scad_objs: Dict[int, "Object"] = field(
        default_factory=dict, init=False, repr=False
    )
    _package: str = field(default=None, init=False)

    def __post_init__(self):
        object.__setattr__(self, "_package", self.attributes.get("package"))
        if not self._package:
            log.error("Missing package information from the manifest tag")
        else:
            del self.attributes["package"]  # Save some memory
        obj: Union["Application", "Permission", "PermissionGroup", "PermissionTree"]
        for obj in [
            *self.applications,
            *self.permissions,
            *self.permission_groups.values(),
            *self.permission_trees.values(),
        ]:
            obj.parent = self
        for application in self.applications:
            application.create_app_storage()

    def __set_api_levels(self) -> List[str]:
        """Lists API level strings for each API level between min and target sdk version"""
        return [i for i in range(self._min_sdk_version, self._target_sdk_version) + 1]

    @property
    def package(self) -> str:
        return self._package

    @package.setter
    def package(self, package: str) -> None:
        self._package = package

    @property
    def min_sdk_version(self) -> int:
        return self._min_sdk_version

    @min_sdk_version.setter
    def min_sdk_version(self, version: int) -> None:
        self._min_sdk_version = version

    @property
    def target_sdk_version(self) -> int:
        return self._target_sdk_version

    @target_sdk_version.setter
    def target_sdk_version(self, version: int) -> None:
        self._target_sdk_version = version

    @property
    def parser(self) -> "AndroidParser":
        return self._parser

    @parser.setter
    def parser(self, parser: "AndroidParser") -> None:
        self._parser = parser

    @property
    def file_system(self) -> "FileSystem":
        return self.parser.filesystem

    def get_uses_permissions(self) -> List[Union["UsesPermission", "UsesPermission23"]]:
        """Returns all UsesPermission and UsesPermission23 objects the Manifest holds"""
        return [*self.uses_permissions, *self.uses_permissions_sdk_23]

    def from_xml(manifest: Element, parser: "AndroidParser") -> "Manifest":
        """Creates an Application object out of a application tag \n
        Keyword arguments:
        \t manifest - An manifest Element object
        \t parser - The AndroidParser initiaing the parsing of the manifest
        Returns:
        \t Manifest object
        """

        def get_sdk_versions(uses_sdk: Element) -> Tuple[int, int]:
            """Takes a uses-sdk xml tag and sets the Manifests sdk version attributes\n
            Keyword arguments:
            \t uses_sdk - a uses_sdk xml tag
            """
            min_sdk = constants.MIN_SDK_VERSION
            target_sdk = constants.MAX_SDK_VERSION
            if uses_sdk == None:
                log.error(
                    f"Missing a uses-sdk tag in the manifest. Cannot determine essential API level information.\n\t Impact: Assuming lowest to highest to lowest API Level"
                )
                return (min_sdk, target_sdk)
            attribs = _xml.get_attributes(uses_sdk)
            min_sdk = attribs.get("minSdkVersion", min_sdk)
            target_sdk = attribs.get("targetSdkVersion", target_sdk)
            return (min_sdk, target_sdk)

        # Attributes
        attribs = _xml.get_attributes(tag=manifest)
        # API level
        min_sdk, target_sdk = get_sdk_versions(manifest.find("uses-sdk"))
        # Application uses-permissions
        uses_permissions = UsesPermission.collect_uses_permissions(tag=manifest)
        permissions = Permission.collect_permissions(tag=manifest)
        permission_groups = PermissionGroup.collect_permission_groups(tag=manifest)
        permission_trees = PermissionTree.collect_permission_trees(tag=manifest)
        uses_permissions_23 = UsesPermission23.collect_uses_permissions(tag=manifest)
        # TODO: Uses Features
        manifest.findall("uses-feature")
        # Applications
        applications: List["Application"] = Application.collect_applications(
            tag=manifest
        )
        manifest_obj = Manifest(
            _parser=parser,
            attributes=attribs,
            permissions=permissions,
            permission_groups=permission_groups,
            uses_permissions=uses_permissions,
            uses_permissions_sdk_23=uses_permissions_23,
            permission_trees=permission_trees,
            _min_sdk_version=min_sdk,
            _target_sdk_version=target_sdk,
            applications=applications,
        )
        """with open("manifest_objects.json", "w") as f:
            pass
            # json.dump(manifest_obj.__dict__, fp=f, indent=4, sort_keys=True)"""

        return manifest_obj

    def create_objects(self, parser: "AndroidParser") -> None:
        """Responsible for creating securicad assets within the manifest
        \nKeyword arguments:
        \n\tparser - an AndroidParser instance
        """
        if not parser:
            log.error(
                f"{__file__}: Cannot create an scad object without a valid parser"
            )
            return
        # API Levels
        for api_level in range(self.min_sdk_version, self.target_sdk_version + 1):
            name = f"API_LEVEL_{api_level}"
            api_scad_obj = parser.create_object(asset_type=name, name=name)
            if api_scad_obj:
                self._api_scad_objs[api_level] = api_scad_obj
        # Permissions
        for permission in self.permissions:
            permission.create_scad_objects(parser=parser)
        uses_permission: Union["UsesPermission", "UsesPermission23"]
        for uses_permission in self.get_uses_permissions():
            uses_permission.create_scad_objects(parser=parser)
            # The UsesPermission connects to the permission with that name
            Permission.create_scad_android_permission(
                parser=parser, name=uses_permission.name, manifest_obj=self
            )
        # Permission Groups / Permission Trees
        permission_container: Union["PermissionGroup", "PermissionTree"]
        for permission_container in [*self.permission_groups, *self.permission_trees]:
            permission_container.create_scad_objects(parser=parser)

        # TODO: Uses Feature
        for application in self.applications:
            application.create_scad_objects(parser=parser)

    def connect_scad_objects(self, parser: "AndroidParser") -> None:
        """Creates the associations between the created scad objects
        \n Keyword arguments:
        \t parser - the AndroidParser instance that created the securiCAD objects
        """
        # Association UsesPermission
        for uses_perm in self.get_uses_permissions():
            uses_perm_scad_obj = parser.scad_id_to_scad_obj[uses_perm.id]
            for app in self.applications:
                app_scad_obj = parser.scad_id_to_scad_obj[app.id]
                parser.create_associaton(
                    s_obj=uses_perm_scad_obj,
                    t_obj=app_scad_obj,
                    s_field="app",
                    t_field="usesPermissions",
                )
            # Association PermissionName
            permission_scad_obj = self.scad_permission_objs[uses_perm.name]
            parser.create_associaton(
                s_obj=uses_perm_scad_obj,
                t_obj=permission_scad_obj,
                s_field="permission",
                t_field="usesPermission",
            )
            if uses_perm.max_sdk_version:
                api_scad_obj = self._api_scad_objs[uses_perm.max_sdk_version]
                # Association MaxSDKVersion
                parser.create_associaton(
                    s_obj=uses_perm_scad_obj,
                    t_obj=api_scad_obj,
                    s_field="apiLevels",
                    t_field="usesPermissions",
                )
        # Association PermissionContainers
        for permission_container in [
            *self.permission_groups.values(),
            *self.permission_trees.values(),
        ]:
            container_scad_obj = parser.scad_id_to_scad_obj[permission_container.id]
            for app in self.applications:
                application_scad_obj = parser.scad_id_to_scad_obj[app.id]
                parser.create_associaton(
                    s_obj=container_scad_obj,
                    t_obj=application_scad_obj,
                    s_field="apps",
                    t_field="permissionContainers",
                )
        # Association ContainedIn
        for permission in self.permissions:
            if permission.permission_group:
                pass
        for permission_tree in self.permission_trees.values():
            domain = permission_tree.name
            permissions = [
                scad_obj
                for (x, scad_obj) in self.scad_permission_objs.items()
                if domain in x.name
            ]
            permission_tree_scad_obj = parser.scad_id_to_scad_obj[permission_tree.id]
            for permission in permissions:
                parser.create_associaton(
                    s_obj=permission_tree_scad_obj,
                    t_obj=permission,
                    s_field="permissions",
                    t_field="permissionContainer",
                )
