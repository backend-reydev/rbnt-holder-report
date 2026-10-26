"""House rules every published file is held to (see the audit stage and the tests).

1. The only addresses allowed are the publicly named ones.
2. No em or en dashes (Task Board voice) and no emoji.
3. No price talk: no currency figures, price levels or calls to buy or sell.
4. No personal credit inside the work.
"""

import re

HEX_ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}(?![0-9a-fA-F])")
LONG_DASH = re.compile("[–—]")
PICTOGRAPH = re.compile("[\U0001F000-\U0001FAFF☀-➿]")
PRICE_TALK = re.compile(
    r"\$\s?\d|\b(usd|usdt|usdc)\b|price target|(will|going to) (rise|fall|pump|dump|moon)|buy now|sell now"
    r"|time to (buy|sell)|we recommend (buying|selling)|to the moon", re.I)
EXCUSED = re.compile(r"no price (forecasts?|predictions?)|price (forecasts?|predictions?)", re.I)
CREDIT = re.compile(r"\b(made|created|prepared|authored|written|designed) by\s+@?\w", re.I)

CHECKED_SUFFIXES = {".md", ".html", ".csv", ".json", ".txt", ".svg", ".css", ".js", ".py", ".toml", ".yml", ".yaml"}
NOT_PUBLISHED = {".git", "cache", "__pycache__", ".pytest_cache", "node_modules", ".venv"}
# Rule definitions and third-party files kept verbatim (brand tokens, font licences).
EXEMPT = {"rules.py", "test_rules.py", "tokens.css", "tokens.json"}


def problems_in(text, allowed, where="?"):
    allowed = {a.lower() for a in allowed}
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        checks = {
            "address": any(m.group(0).lower() not in allowed for m in HEX_ADDRESS.finditer(line)),
            "dash": bool(LONG_DASH.search(line)),
            "emoji": bool(PICTOGRAPH.search(line)),
            "price": bool(PRICE_TALK.search(EXCUSED.sub(" ", line))),
            "credit": bool(CREDIT.search(line)),
        }
        found += [{"rule": rule, "file": where, "line": number} for rule, hit in checks.items() if hit]
    return found


def problems_under(root, allowed):
    found = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if not path.is_file() or path.suffix.lower() not in CHECKED_SUFFIXES:
            continue
        if any(part in NOT_PUBLISHED for part in rel.parts) or path.name in EXEMPT or path.name.startswith("OFL-"):
            continue
        try:
            found += problems_in(path.read_text(), allowed, str(rel))
        except UnicodeDecodeError:
            pass
    return found
