from __future__ import annotations
import sys
import typer
import datetime
import xml.etree.ElementTree as ET
import configparser
import glob
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Dict, List, Optional, Any, Tuple
from android_parser.utilities import constants as constants
from android_parser.components import (
    manifest as manifest,
    application as application,
    intent_filter as intent_filter,
)
from android_parser.utilities.log import log
from securicad.model import Model, json_serializer, es_serializer, scad_serializer
from securicad.model.exceptions import (
    InvalidAssetException,
    DuplicateAssociationException,
)
from securicad.langspec import Lang

# import tqdm  # alternative progressbar
@dataclass()
class AndroidParser:
    activities: Dict[str, "Activity"] = field(default_factory=dict)
    manifests: Dict[str, "Manifest"] = field(default_factory=dict)
    model: Model = field(default=None)
    providers: Dict[str, "Provider"] = field(default_factory=dict)
    receivers: Dict[str, "Receiver"] = field(default_factory=dict)
    services: Dict[str, "Service"] = field(default_factory=dict)
    pass

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
            scad_serializer.serialize_model(self.model, output_path)

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
        # connect scad objects
        # generate default views
        return
        # TODO:  NotImplemented

    def collect(self, input: BinaryIO) -> None:
        """Collects information of an AndroidManifest file wrapped in a Manifest object"""
        xml_data = ET.parse(input)
        root = xml_data.getroot()
        manifest_obj = manifest.collect_manifest(root)
        self.manifests[manifest_obj.package] = manifest_obj


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
