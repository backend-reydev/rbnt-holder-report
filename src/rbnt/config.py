"""Load and save the edition config in config/<edition>.json."""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EDITION = os.environ.get("RBNT_EDITION", "q3-2026")


def config_path(edition=DEFAULT_EDITION):
    return ROOT / "config" / f"{edition}.json"


def load(edition=DEFAULT_EDITION):
    with open(config_path(edition)) as f:
        return json.load(f)


def save(cfg, edition=DEFAULT_EDITION):
    with open(config_path(edition), "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")


def data_dir(kind, edition=DEFAULT_EDITION):
    """kind is "raw" or "processed". Each edition gets its own folder."""
    d = ROOT / "data" / kind / edition
    d.mkdir(parents=True, exist_ok=True)
    return d


def named_wallets(cfg):
    """Every wallet the report is allowed to name, as {lowercase address: label}."""
    named = {cfg["wrbnt"]["address"].lower(): cfg["wrbnt"]["label"]}
    for p in cfg["staking_pools"]:
        named[p["address"].lower()] = p["label"]
    for w in cfg["reserved_wallets"]["wallets"]:
        named[w["address"].lower()] = w["label"]
    for w in cfg["labelled_contracts"]["wallets"]:
        named[w["address"].lower()] = w["label"]
    return named
