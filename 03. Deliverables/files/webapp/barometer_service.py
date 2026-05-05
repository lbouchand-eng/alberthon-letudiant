"""Lightweight wrapper around barometer_data.json."""
import json
from pathlib import Path

JSON_PATH = Path(__file__).parent.parent / "barometer_data.json"


def load_barometer():
    with open(JSON_PATH, encoding="utf-8") as f:
        return json.load(f)
