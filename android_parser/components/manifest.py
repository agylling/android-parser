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
    Base,
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
class APILevel(Base):
    _api_level: int = field()

    @property
    def api_level(self) -> int:
        return self._api_level

    @property
    def parent(self) -> "Manifest":
        return self._parent

    @parent.setter
    def parent(self, parent: "Manifest") -> None:
        self._parent = parent

    @property
    def name(self) -> str:
        return f"API_LEVEL_{self.api_level}"

    @property
    def asset_type(self) -> str:
        return f"API_LEVEL_{self.api_level}"

    def create_scad_objects(self, parser: "AndroidParser") -> None:
        super().create_scad_objects(parser)
        parser.create_object(python_obj=self)

    def connect_scad_objects(self, parser: "AndroidParser") -> None:
        super().connect_scad_objects(parser)
        # Association RunsOn
        api_level = parser.scad_id_to_scad_obj[self.id]
        app_obj = parser.scad_id_to_scad_obj[self.parent.application.id]
        parser.create_associaton(
            s_obj=api_level,
            t_obj=app_obj,
            s_field="app",
            t_field="androidApis",
        )


@dataclass()
class Manifest:
    _parser: "AndroidParser" = field(default=None)
    application: "Application" = field(default=None)
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
    api_levels: Dict[int, "APILevel"] = field(
        default_factory=dict,
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
            self.application,
            *self.permissions,
            *self.permission_groups.values(),
            *self.permission_trees.values(),
            *self.api_levels.values(),
        ]:
            obj.parent = self
        self.application.create_app_storage()

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

        def get_sdk_versions(
            uses_sdk: Element,
        ) -> Tuple[int, int, Dict[int, "APILevel"]]:
            """Takes a uses-sdk xml tag and sets the Manifests sdk version attributes\n
            \n Keyword arguments:
            \t uses_sdk - a uses_sdk xml tag
            \n Returns:
            \t A tuple of (min_sdk, target_sdk, Dict[int, APILevels])
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
            api_levels = {}
            for i in range(min_sdk, target_sdk + 1):
                api_levels[i] = APILevel(_api_level=i)
            return (min_sdk, target_sdk, api_levels)

        # Attributes
        attribs = _xml.get_attributes(tag=manifest)
        # API level
        min_sdk, target_sdk, api_levels = get_sdk_versions(manifest.find("uses-sdk"))
        # Application uses-permissions
        uses_permissions = UsesPermission.collect_uses_permissions(tag=manifest)
        permissions = Permission.collect_permissions(tag=manifest)
        permission_groups = PermissionGroup.collect_permission_groups(tag=manifest)
        permission_trees = PermissionTree.collect_permission_trees(tag=manifest)
        uses_permissions_23 = UsesPermission23.collect_uses_permissions(tag=manifest)
        # TODO: Uses Features
        manifest.findall("uses-feature")
        # Applications
        application: List["Application"] = Application.collect_applications(
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
            api_levels=api_levels,
            application=application,
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
        for api_level in self.api_levels.values():
            api_level.create_scad_objects(parser=parser)
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
        self.application.create_scad_objects(parser=parser)

    def connect_scad_objects(self, parser: "AndroidParser") -> None:
        """Creates the associations between the created scad objects
        \n Keyword arguments:
        \t parser - the AndroidParser instance that created the securiCAD objects
        """
        if not parser:
            log.error(
                f"{__file__}: Cannot create an scad object without a valid parser"
            )
            return
        app_scad_obj = parser.scad_id_to_scad_obj[self.application]
        for api_level in self.api_levels.values():
            api_level.connect_scad_objects(parser=parser)
        # Association UsesPermission
        for uses_perm in self.get_uses_permissions():
            uses_perm_scad_obj = parser.scad_id_to_scad_obj[uses_perm.id]
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
                api_scad_obj = parser.scad_id_to_scad_obj[
                    self.api_levels[uses_perm.max_sdk_version].id
                ]
                # Association MaxSDKVersion
                parser.create_associaton(
                    s_obj=uses_perm_scad_obj,
                    t_obj=api_scad_obj,
                    s_field="apiLevels",
                    t_field="usesPermissions",
                )
        # Association ApplicationPermissions
        for permission in self.scad_permission_objs.values():
            parser.create_associaton(
                s_obj=app_scad_obj,
                t_obj=permission,
                s_field="permissions",
                t_field="app",
            )
        # Association PermissionContainers
        for permission_container in [
            *self.permission_groups.values(),
            *self.permission_trees.values(),
        ]:
            container_scad_obj = parser.scad_id_to_scad_obj[permission_container.id]
            parser.create_associaton(
                s_obj=container_scad_obj,
                t_obj=app_scad_obj,
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
