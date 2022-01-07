from __future__ import annotations
from typing import Any, NamedTuple
from .main import AndroidParser

__version__ = "0.0.1"


class SubParserOutput(NamedTuple):
    sub_parser: str
    data: Any


def parse(data: list[SubParserOutput], metadata: dict[str, Any]) -> dict[str, Any]:
    android_parser = AndroidParser()
    for entry in data:
        android_parser.collect(entry.data)
    res = android_parser.parse(metadata)
    return res
