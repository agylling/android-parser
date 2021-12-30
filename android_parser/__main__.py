import argparse
import typer
import datetime
from pathlib import Path
from . import android_manifest_parser
from .main import AndroidParser
from android_parser.utilities.log import log
from typing import List

app = typer.Typer(
    help="Parses android manifest files and converts that to a securiCAD compatible model"
)


@app.command()
def main(
    input: Path = typer.Argument(
        "--manifest",
        "-m",
        help="Path to the android manifest for which to create a model for",
        exists=True,
        file_okay=True,
        dir_okay=False,
        writeable=False,
        readable=True,
        allow_dash=True,
        resolve_path=True,
    ),
    output: Path = typer.Option(
        Path(f"{datetime.datetime.today().strftime('%Y-%m-%d_%H_%M')}.sCAD"),
        "--output",
        "-o"
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
        False, "--quiet", "-q", show_default=False, help="Prints debug information",
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
    )
) -> None:
    android_parser = AndroidParser()
    with open(input, mode="rb") as f:
        data = f.read()
    android_parser.collect(android_manifest_parser.parse(data))
    android_parser.write_model_file(output, mar)


if __name__ == "__main__":
    main()
