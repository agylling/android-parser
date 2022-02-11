from __future__ import annotations

from typing import Any, Dict, Union
from xml.etree.ElementTree import Element


class ComponentNotFound(Exception):
    pass


def get_attributes(tag: Element) -> Dict[str, Union[bool, str, float, int]]:
    raw_attribs = tag.attrib
    attribs: dict[str, Any] = {}
    for key, value in raw_attribs.items():
        try:
            cleaned_key = key.split("}")[1]
            attribs[cleaned_key] = value
        except IndexError:
            attribs[key] = value
    for key, attrib in attribs.items():
        if attrib.isnumeric():
            attribs[key] = int(attrib)
        elif any(x in key for x in ["-", "."]):
            try:
                float(attrib)
                attribs[key] = float(attrib)
            except ValueError:
                pass
        elif attrib == "false":
            attribs[key] = False
        elif attrib == "true":
            attribs[key] = True
    return attribs
