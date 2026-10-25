"""Step 4. Native RBNT and WRBNT balances for every candidate at both snapshots.

Native balances come from eth_getBalance at each snapshot block. WRBNT
balances come from balanceOf on the WRBNT contract at the same blocks. RBNT
held by the WRBNT contract itself is excluded from holder totals, so each
token is counted once: a WRBNT holder is credited with the RBNT behind it.
"""

import _path  # noqa: F401


def main():
    raise SystemExit("Not built yet. See docs/METHOD.md for what this step does.")


if __name__ == "__main__":
    main()
