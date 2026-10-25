# Processed data

CSV files behind every chart and table in the report, one folder per edition.
Each file holds named wallets or groups only. No unlabelled address appears
here.

| File | Built by | Contents |
| --- | --- | --- |
| `q3-2026/named_wallets.csv` | `scripts/02_named_wallets.py` | Balance of each named wallet at the start and end blocks, and the change |

All balances are in RBNT (18 decimals, shown to 6 places), read with
`eth_getBalance` from the Redbelly mainnet RPC at the snapshot blocks listed
in `config/q3-2026.json`.
