from __future__ import annotations
from typing import Optional, Any


def validate_input(data: bytes) -> bytes:
    return data


def parse(data: bytes, metadata: Optional[dict[str, Any]] = None):
    return validate_input(data)
