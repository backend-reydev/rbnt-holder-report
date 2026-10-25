"""Rules every published file must follow, shared by the verify step and tests.

* No address appears unless it is one of the publicly named wallets.
* No em or en dashes (Task Board voice rule) and no emoji.
* No price talk: no currency amounts, no price levels, no buy or sell calls.
* No personal credit lines inside the work.
"""

import re

ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}(?![0-9a-fA-F])")
DASH = re.compile("[–—]")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿\U0001F000-\U0001F2FF]")
PRICE = re.compile(r"(\$\s?\d|\busd\b|price target|will (rise|fall|pump|moon)|\bbuy now\b|\bto the moon\b|"
                   r"\bwe recommend (buying|selling)\b|\bgood time to (buy|sell)\b)", re.I)
CREDIT = re.compile(r"(made by|created by|prepared by|authored by|written by)\s+@?\w", re.I)

TEXT_EXT = {".md", ".html", ".csv", ".json", ".txt", ".svg", ".css", ".js", ".py", ".toml", ".yml", ".yaml"}
SKIP_DIRS = {".git", "cache", "__pycache__", "node_modules", ".venv"}
# Files that define the rules themselves, or hold the brand kit as published.
SKIP_FILES = {"publish_rules.py", "test_publish_rules.py", "tokens.css", "tokens.json"}
# Phrases the rules allow because they say what the report does not do.
ALLOWED_PRICE = re.compile(r"no price (prediction|forecast)s?|not price|price predictions", re.I)


def scan_text(text, named, filename="?"):
    named = {a.lower() for a in named}
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        for m in ADDRESS.finditer(line):
            if m.group(0).lower() not in named:
                out.append({"kind": "address", "file": filename, "line": n})
        if DASH.search(line):
            out.append({"kind": "dash", "file": filename, "line": n})
        if EMOJI.search(line):
            out.append({"kind": "emoji", "file": filename, "line": n})
        if PRICE.search(ALLOWED_PRICE.sub("", line)):
            out.append({"kind": "price", "file": filename, "line": n})
        if CREDIT.search(line):
            out.append({"kind": "credit", "file": filename, "line": n})
    return out


def scan_tree(root, named):
    out = []
    for p in sorted(root.rglob("*")):
        # Third-party font licences are kept verbatim, as their licence requires.
        if not p.is_file() or any(part in SKIP_DIRS for part in p.parts) or p.name in SKIP_FILES \
                or p.name.startswith("OFL-"):
            continue
        if p.suffix.lower() not in TEXT_EXT:
            continue
        try:
            text = p.read_text()
        except UnicodeDecodeError:
            continue
        out += scan_text(text, named, str(p.relative_to(root)))
    return out
