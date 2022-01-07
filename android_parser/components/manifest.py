from xml.etree.ElementTree import Element
from typing import List, Tuple, TYPE_CHECKING
from android_parser.utilities.log import log
from dataclasses import dataclass, field
from android_parser.utilities import (
    xml as _xml,
    constants as constants,
)
import json

from android_parser.components.application import Application


def collect_manifest(manifest: Element) -> "Manifest":
    # TODO gather more attributes from manifest
    return Manifest.from_xml(manifest)


@dataclass(frozen=True)
class PermissionGroup:
    attributes: dict = field(default_factory=dict)

    @property
    def name(self) -> int:
        return self.attributes.get("name")

    @property
    def description(self) -> str:
        """The name for a logical grouping of related permissions that permission objects join to"""
        return self.attributes.get("description")

    def from_xml(permission_group: Element) -> "PermissionGroup":
        """Creates an PermissionGroup object out of a permission_group tag \n
        Keyword arguments:
        \t permission_group: An permission-group Element object
        Returns:
        \t PermissionGroup object
        """
        attribs = _xml.get_attributes(tag=permission_group)
        return PermissionGroup(attributes=attribs)


@dataclass(frozen=True, unsafe_hash=True)
class Permission:
    attributes: dict = field(default_factory=dict)

    @property
    def name(self) -> int:
        return self.attributes.get("name")

    @property
    def permission_group(self) -> str:
        return self.attributes.get("permissionGroup")

    @property
    def protection_level(self) -> str:
        return self.attributes.get("protectionLevel")

    def from_xml(permission: Element) -> "Permission":
        """Creates an Permission object out of a permission tag \n
        Keyword arguments:
        \t permission: An permission Element object
        Returns:
        \t Permission object
        """
        attribs = _xml.get_attributes(tag=permission)
        return Permission(attributes=attribs)


@dataclass(frozen=True, unsafe_hash=True)
class UsesPermission:
    attributes: dict = field(default_factory=dict)

    @property
    def max_sdk_version(self) -> int:
        return self.attributes.get("maxSdkVersion")

    @property
    def name(self) -> int:
        return self.attributes.get("name")

    def from_xml(uses_permission: Element) -> "UsesPermission":
        """Creates an UsesPermission object out of a uses-permission tag \n
        Keyword arguments:
        \t uses-permission: An uses-permission Element object
        Returns:
        \t UsesPermission object
        """
        attribs = _xml.get_attributes(tag=uses_permission)
        return UsesPermission(attributes=attribs)


@dataclass(frozen=True, unsafe_hash=True)
class Manifest:
    attributes: dict = field(default_factory=dict)
    permissions: List[Permission] = field(default_factory=list)
    uses_permissions: List[UsesPermission] = field(default_factory=list)
    permission_groups: List[UsesPermission] = field(default_factory=list)
    applications: List["Application"] = field(default_factory=list)
    _target_sdk_version: int = field(default=None)
    _min_sdk_version: int = field(default=None)
    __package: str = field(default=None, init=False)

    def __post_init__(self):
        object.__setattr__(self, "__package", self.attributes.get("package"))
        if not self.__package:
            log.error("Missing package information from the manifest tag")
        else:
            del self.attributes["package"]  # Save some memory

    def __set_api_levels(self) -> List[str]:
        """Lists API level strings for each API level between min and target sdk version"""
        return [i for i in range(self._min_sdk_version, self._target_sdk_version) + 1]

    @property
    def package(self) -> str:
        return self.__package

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
            if not uses_sdk:
                log.error(
                    """
                    Missing a uses-sdk tag in the manifest. Cannot determine essential API level information.
                    \t Impact: Assuming lowest to highest to lowest API Level
                    """
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
        uses_permissions = []
        for uses_permission in manifest.findall("uses-permission"):
            uses_permissions.append(
                UsesPermission.from_xml(uses_permission=uses_permission)
            )
        permissions = []
        for permission in manifest.findall("permission"):
            permissions.append(Permission.from_xml(permission=permission))
        permission_groups = []
        for permission_grp in manifest.findall("permission-group"):
            permission_groups.append(
                PermissionGroup.from_xml(permission_grou=permission_grp)
            )

        # TODO
        # Uses Features
        manifest.findall("uses-feature")
        # Applications
        applications: List["Application"] = []
        for app_tag in manifest.findall("application"):
            applications.append(
                Application.from_xml(application=app_tag, parent_type=manifest.tag)
            )
        manifest_obj = Manifest(
            attributes=attribs,
            permissions=permissions,
            permission_groups=permission_groups,
            uses_permissions=uses_permissions,
            _min_sdk_version=min_sdk,
            _target_sdk_version=target_sdk,
            applications=applications,
        )
        with open("manifest_objects.json", "w") as f:
            pass
            # json.dump(manifest_obj.__dict__, fp=f, indent=4, sort_keys=True)

        for application_obj in applications:
            application_obj.manifest_parent = manifest_obj
        return manifest_obj
