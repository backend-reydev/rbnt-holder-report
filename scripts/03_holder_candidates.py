"""Step 3. Build the candidate holder list.

Collects addresses from the Routescan v2 top balance list and the WRBNT holder
list, plus every address that sent or received RBNT through a named wallet in
the quarter, so wallets that were large at the start but sold out are not
missed. Picks up Routescan name tags for exchanges and contracts and adds them
to labelled_contracts in the config. Addresses stay in data/raw, which is not
published.
"""

import _path  # noqa: F401


def main():
    raise SystemExit("Not built yet. See docs/METHOD.md for what this step does.")


if __name__ == "__main__":
    main()
