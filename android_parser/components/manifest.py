from xml.etree.ElementTree import Element
from typing import List, Tuple, TYPE_CHECKING, Dict
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
    PermissionTree,
)

if TYPE_CHECKING:
    from android_parser.main import AndroidParser
    from securicad.model.object import Object


def collect_manifest(manifest: Element) -> "Manifest":
    """Creates a Manifest object out of a manifest xml object
    \nKeyword arguments:
    \t manifest - a manifest xml Element
    \nReturns:
    \t A Manifest object
    """
    return Manifest.from_xml(manifest)


@dataclass()
class Manifest:
    attributes: dict = field(default_factory=dict)
    permissions: List[Permission] = field(default_factory=list)
    scad_permission_objs: Dict[str, "Object"] = field(default_factory=dict, init=False)
    uses_permissions: List[UsesPermission] = field(default_factory=list)
    uses_permissions_sdk_23: List[UsesPermission] = field(default_factory=list)
    permission_groups: List[UsesPermission] = field(default_factory=list)
    permission_trees: List[PermissionTree] = field(default_factory=list)
    applications: List["Application"] = field(default_factory=list)
    _target_sdk_version: int = field(default=None)
    _min_sdk_version: int = field(default=None)
    _package: str = field(default=None, init=False)

    def __post_init__(self):
        object.__setattr__(self, "_package", self.attributes.get("package"))
        if not self._package:
            log.error("Missing package information from the manifest tag")
        else:
            del self.attributes["package"]  # Save some memory
        for obj in [
            *self.applications,
            *self.permissions,
            *self.permission_groups,
            *self.permission_trees,
        ]:
            obj.parent = self

    def __set_api_levels(self) -> List[str]:
        """Lists API level strings for each API level between min and target sdk version"""
        return [i for i in range(self._min_sdk_version, self._target_sdk_version) + 1]

    @property
    def package(self) -> str:
        return self._package

    @property
    def min_sdk_version(self) -> int:
        return self._min_sdk_version

    @property
    def target_sdk_version(self) -> int:
        return self._target_sdk_version

    def from_xml(manifest: Element) -> "Manifest":
        """Creates an Application object out of a application tag \n
        Keyword arguments:
        \t manifest: An manifest Element object
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
        # TODO
        # uses_permissions_sdk_23 = uses-permission-sdk-23
        # Uses Features
        manifest.findall("uses-feature")
        # Applications
        applications: List["Application"] = Application.collect_applications(
            tag=manifest
        )
        manifest_obj = Manifest(
            attributes=attribs,
            permissions=permissions,
            permission_groups=permission_groups,
            uses_permissions=uses_permissions,
            permission_trees=permission_trees,
            _min_sdk_version=min_sdk,
            _target_sdk_version=target_sdk,
            applications=applications,
        )
        with open("manifest_objects.json", "w") as f:
            pass
            # json.dump(manifest_obj.__dict__, fp=f, indent=4, sort_keys=True)

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
            parser.create_object(asset_type=name, name=name)
        # Permissions
        for permission in self.permissions:
            permission.create_scad_objects(parser=parser)
        for uses_permission in self.uses_permissions:
            parser.create_object(
                asset_type="PermissionTree", python_obj=uses_permission
            )
        for uses_permission in self.uses_permissions_sdk_23:
            # TODO
            pass
        # Permission Groups
        for permission_group in self.permission_groups:
            parser.create_object(
                asset_type="PermissionGroup", python_obj=permission_group
            )
        # Permission Trees
        for permission_tree in self.permission_trees:
            parser.create_object(
                asset_type="PermissionTree", python_obj=permission_tree
            )
        # TODO: Uses Feature
        for application in self.applications:
            application.create_scad_objects(parser=parser)
