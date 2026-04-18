import json
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load(name: str):
    with open(FIXTURE_DIR / f"{name}.json") as f:
        return json.load(f)
