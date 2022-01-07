import argparse
import datetime
from pathlib import Path
from . import android_manifest_parser
from .main import app
from android_parser.utilities.log import log
from typing import List

if __name__ == "__main__":
    app(prog_name="android_parser")
