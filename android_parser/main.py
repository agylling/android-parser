from __future__ import annotations
from aifc import Error
from mimetypes import init
import sys
import typer
import datetime
import xml.etree.ElementTree as ET
import configparser
import glob
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO, Dict, List, Optional, Any, Tuple, Union

from typer.models import DefaultType
from android_parser.utilities import constants as constants
from android_parser.components import (
    filesystem as filesystem,
    manifest as manifest,
    hardware as hardware,
)
from android_parser.utilities.log import log
from android_parser.utilities import attacker as attacker
from android_parser.utilities.malicious_application import MaliciousApp

from securicad.model import (
    Model,
    json_serializer,
    es_serializer,
    scad_serializer,
    object,
)
from securicad.model.exceptions import (
    InvalidAssetException,
    DuplicateAssociationException,
)
from securicad.langspec import Lang
from securicad.model.object import Object

if TYPE_CHECKING:
    from android_parser.components.application import Application
    from android_parser.components.filesystem import FileSystem
    from android_parser.components.hardware import Device
    from android_parser.components.manifest import Manifest
    from android_parser.components.provider import Provider
    from android_parser.components.activity import Activity
    from android_parser.components.service import Service
    from android_parser.components.receiver import Receiver
    from android_parser.components.android_classes import (
        PermissionTree,
        PermissionGroup,
        Permission,
    )

    AnyClass = Union[
        Object,
        Application,
        Provider,
        Activity,
        Service,
        Receiver,
        PermissionTree,
        PermissionGroup,
        Permission,
    ]


class MissingAttributes(Exception):
    pass


# import tqdm  # alternative progressbar
@dataclass()
class AndroidParser:
    model: Model = field(default=None, init=False)
    manifests: Dict[str, "Manifest"] = field(default_factory=dict, init=False)
    filesystem: "FileSystem" = field(default=None, init=False)
    device: "Device" = field(default=None, init=False)
    malicious_application: "MaliciousApp" = field(default=None, init=False)
    _attacker: "Object" = field(default=None, init=False)
    scad_id_to_scad_obj: Dict[int, Object] = field(default_factory=dict, init=False)
    # An incremental id variable for objects
    object_id: int = field(default=0, init=False)

    @property
    def attacker(self) -> "Object":
        return self._attacker

    @attacker.setter
    def attacker(self, attacker: "Object") -> None:
        self._attacker = attacker

    def write_model_file(
        self, output_path: Path, mar_path: Optional[Path] = None
    ) -> None:
        def get_credentials() -> Tuple[Optional[str], Optional[str], Optional[str]]:
            config = configparser.ConfigParser()
            config.read(get_configpath())
            if "AUTH" not in config:
                return None, None, None
            return (
                config["AUTH"].get("username"),
                config["AUTH"].get("password"),
                config["AUTH"].get("organization"),
            )

        def get_name() -> str:
            name = output_path.name
            if name.lower().endswith(".scad"):
                name = name[: -len(".scad")]
            return name

        def get_outputpath() -> str:
            return str(output_path.resolve().parent)

        def get_configpath() -> str:
            return str(
                Path(__file__).resolve().parent.parent.joinpath("lib", "conf.ini")
            )

        def get_mar() -> str:
            if mar_path:
                return mar_path
            config = configparser.ConfigParser()
            config.read(get_configpath())
            if "MAR" not in config:
                return None
            return config["MAR"].get("marpath")

        mar_path = get_mar()
        if not mar_path:
            log.warning(
                f"No .mar file found for validating the model. Assuming language: {constants.LANG_ID} version {constants.REQUIRED_LANGUAGE_VERSION}"
            )

        open_mar = None
        if mar_path:
            if "*" in str(mar_path):
                try:
                    open_mar = next(iter(glob.glob(mar_path)))
                except StopIteration:
                    pass
            else:
                open_mar = mar_path
        if not open_mar:
            self.model = Model(
                get_name(),
                lang_id=constants.LANG_ID,
                lang_version=constants.REQUIRED_LANGUAGE_VERSION,
            )
        else:
            with open(open_mar, mode="rb") as f:
                self.lang = Lang(f)
                self.model = Model(get_name(), lang=self.lang)
        self._parse()

        # Validate model
        self.model.validate()

        # Save model to file
        if ".json" in output_path.suffix.lower():
            json_model = json_serializer.serialize_model(self.model)
            # default to json
            output_path = output_path.with_suffix(".json")  # making sure correct suffix
            with open(output_path, "w") as f:
                json.dump(json_model, f, indent=4, sort_keys=True)
        else:
            output_path = output_path.with_suffix(".sCAD")  # making sure correct suffix
            # scad_serializer.serialize_model(self.model, output_path)

        if not output_path:
            sys.exit(1)

    def parse(self, metadata: dict[str, Any]) -> Dict[str, Any]:
        try:
            with next(
                iter(Path(__file__).parent.glob("org.foreseeti.androidLang-*.mar"))
            ).open(mode="rb") as f:
                self.lang = Lang(f)
            lang_version = f.name.split("-")[-1].replace(".mar", "")
            log.info(f"creating a model with language version: {lang_version}")
            self.model = Model(lang=self.lang)
        except StopIteration:
            log.warning(
                "No .mar file found for validating the model. Using default language {constants.LANG_ID} version {constants.REQUIRED_LANGUAGE}"
            )
            self.model = Model(
                lang_id=constants.LANG_ID, lang_version=constants.REQUIRED_LANGUAGE
            )

        self.__parse()
        return es_serializer.serialize_model(self.model)

    def _parse(self) -> None:
        # create scad objects
        self._create_scad_objects()
        # connect scad objects
        self._connect_scad_objects()
        # generate default views
        return
        # TODO:  NotImplemented

    def collect(self, input: BinaryIO) -> None:
        """Collects information of an AndroidManifest file wrapped in a Manifest object"""
        self.filesystem = filesystem.collect_filesystem()
        # DEPENDENCY: Filesystem needs to be created before hardware
        self.device = hardware.Device()
        for sys_app in self.device.system_apps.values():
            self.filesystem.create_app_storage(app=sys_app)
        xml_data = ET.parse(input)
        root = xml_data.getroot()
        manifest_obj = manifest.collect_manifest(root, self)
        self.manifests[manifest_obj.package] = manifest_obj
        # Malicious app (attacker's application)
        self.malicious_application = MaliciousApp()
        self.filesystem.create_app_storage(app=self.malicious_application)

    def _create_scad_objects(self) -> None:
        """Creates the securiCAD asset objects within our model from the manifest data collected"""
        self.filesystem.create_scad_objects(parser=self)
        self.device.create_scad_objects(parser=self)
        for manifest in self.manifests.values():
            manifest.create_objects(parser=self)
        attacker.create_attacker(parser=self)
        self.malicious_application.create_scad_objects(parser=self)

    def _connect_scad_objects(self) -> None:
        """Connects the created securiCAD objects"""
        self.filesystem.connect_scad_objects(parser=self)
        self.device.connect_scad_objects(parser=self)
        for manifest in self.manifests.values():
            manifest.connect_scad_objects(parser=self)
        self.malicious_application.connect_scad_objects(parser=self)
        attacker.connect_attacker(parser=self)

    def create_associaton(
        self, s_obj: "Object", t_obj: "Object", s_field: str, t_field: str
    ) -> None:
        """Creates an association between two securicad Objects
        \n Keyword arguments:
        \t s_obj - the source model Object
        \t t_obj - the target/destination model Object
        \t s_field - the s_obj's field name
        \t t_field - thi t_obj's field name
        """
        if not any([s_obj, t_obj]):
            log.error(f"Trying to connect one or more None objects")
            return
        if s_obj == t_obj:
            return
        if not all(isinstance(x, Object) for x in [s_obj, t_obj]):
            log.error(
                f"One or more invalid object types. got {type(s_obj)}, {type(t_obj)}, expected <Object>, <Object>"
            )
        try:
            s_obj.field(s_field).connect(t_obj.field(t_field))
        except DuplicateAssociationException:
            pass
        except InvalidAssetException as e:
            log.error(e)

    def create_object(
        self,
        python_obj: Optional[AnyClass] = None,
        asset_type: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Object]:
        """Helper function for creating an scad object. Functionality that is shared whenever creating an asset.
        \n Keyword arguments:
        \t python_obj - the python class object containing that maps to the created scad object
        \t asset_type - the androidLang asset to create (takes precedence over python_obj.asset_type)
        \t name - the name of the object if python_obj isn't provided
        \n asset_type and name can be ignored if python_obj has the corresponding attribute
        \n Returns:
        \t An scad object or None
        """
        if not any([python_obj, name]):
            log.error(
                f"{__file__}: To create an scad object, provider either a python_obj or name. Trying to create an {asset_type} object"
            )
            return
        if not any([hasattr(python_obj, "asset_type"), asset_type]):
            raise MissingAttributes(
                "To create an scad object, the provided python_obj must have an asset_type property."
            )
        if hasattr(python_obj, "asset_type") and not asset_type:
            asset_type = python_obj.asset_type
        if hasattr(python_obj, "name"):
            name = python_obj.name.split(".")[-1]
        try:
            scad_obj = self.model.create_object(asset_type=asset_type, name=name)
            self.scad_id_to_scad_obj[scad_obj.id] = scad_obj
            if python_obj:
                python_obj.id = scad_obj.id
            # self.object_id += 1
            return scad_obj
        except InvalidAssetException as e:
            log.warning(e)


app = typer.Typer(
    name="android_parser",
    help="Parses android manifest files and converts that to a securiCAD compatible model",
)


@app.command()
def main(
    input: Path = typer.Argument(
        ...,
        help="Path to the android manifest for which to create a model for",
        exists=True,
        file_okay=True,
        dir_okay=False,
        allow_dash=True,
        resolve_path=True,
        writable=False,
        readable=True,
    ),
    output: Path = typer.Option(
        Path(f"{datetime.datetime.today().strftime('%Y-%m-%d_%H_%M')}.sCAD"),
        "--output",
        "-o",
        help="The output path for which to save the final .sCAD model",
        file_okay=True,
        dir_okay=False,
        writable=True,
        readable=False,
        allow_dash=True,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        show_default=False,
        help="Only print warnings and errors",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        show_default=False,
        help="Prints debug information",
    ),
    mar: Path = typer.Option(
        None,
        "-m",
        "--mar",
        file_okay=True,
        dir_okay=False,
        writable=False,
        readable=True,
        allow_dash=True,
        resolve_path=True,
        help="Meta Attack Language .mar file to validate the model with",
    ),
) -> None:
    android_parser = AndroidParser()
    with open(input.absolute(), mode="rb") as f:
        android_parser.collect(f)
    android_parser.write_model_file(output_path=output, mar_path=mar)
    # android_parser.collect(android_manifest_parser.parse(data))
    # android_parser.write_model_file(output, mar)
