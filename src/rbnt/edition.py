"""Edition settings live in config/<edition>.json. This module reads and writes
them and knows where each edition's files go."""

import json
import os
from pathlib import Path

HOME = Path(__file__).resolve().parents[2]
EDITION = os.environ.get("RBNT_EDITION", "q3-2026")


def settings_file(edition=EDITION):
    return HOME / "config" / f"{edition}.json"


def read(edition=EDITION):
    return json.loads(settings_file(edition).read_text())


def write(cfg, edition=EDITION):
    settings_file(edition).write_text(json.dumps(cfg, indent=2) + "\n")


def out_dir(edition=EDITION):
    """Published tables for one edition: data/<edition>/."""
    d = HOME / "data" / edition
    d.mkdir(parents=True, exist_ok=True)
    return d


def public_names(cfg):
    """{lower-case address: name} for every address the report may name."""
    names = {cfg["wrbnt"]["address"].lower(): cfg["wrbnt"]["label"]}
    names.update({p["address"].lower(): p["label"] for p in cfg["staking_pools"]})
    names.update({w["address"].lower(): w["label"] for w in cfg["reserved_wallets"]["wallets"]})
    names.update({w["address"].lower(): w["label"] for w in cfg["labelled_contracts"]["wallets"]})
    return names
