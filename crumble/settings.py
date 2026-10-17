# SPDX-License-Identifier: Apache-2.0
import json

from .smv import EMPTY_LIBRARY, validate_library
from .util import atomic, canonical


def initialise(store, encoder="demo", device="cpu"):
    path = store.root / "settings.json"
    if path.exists():
        return json.loads(path.read_text())
    value = {"encoder": encoder, "device": device, "schema": 1}
    atomic(path, canonical(value).encode())
    return value


def library(store):
    path = store.root / "operations.json"
    return validate_library(json.loads(path.read_text())) if path.exists() else EMPTY_LIBRARY
