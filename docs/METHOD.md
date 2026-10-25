# Method and data sources

This note explains how the RBNT Holder Report is produced, so that anyone can
check this edition or produce the next one. It covers what is measured, where
every number comes from, the checks that must pass, and the exact steps to
repeat the work.

Edition 1 covers **Q3 2026**, 1 July to 30 September 2026.

## 1. What the report measures

| Question in the brief | How it is measured | Files |
| --- | --- | --- |
| How holdings are spread, and how that changed | Every wallet's holding at the quarter start, both month ends and the quarter end, in size bands; share of the largest 10, 100 and 1,000 wallets; the number of wallets that together hold half; Gini score; Lorenz curve | `04`, `05`, `05b` |
| Accumulation and selling among the largest holders, in groups | Wallets grouped by their holding at the start and followed to the end: how many added more than 1%, stayed within 1%, reduced by more than 1% or fell below 1 RBNT; net change per group; the same for rank groups (largest 10, 11 to 100, 101 to 1,000); how each group holds its RBNT (in the wallet, wrapped, staked); a band migration matrix | `06`, `06b`, `06c` |
| Staking in the two Reddex pools | Each pool's RBNT balance at the start and end (the headline, as the brief asks), split into staked RBNT (`totalStake`) and reward funds; daily balances; stakers, new stakers and stakers who left; stake, withdrawal and reward claim records; stake sizes; the 365 day pool's lock calendar | `07`, `07b`, `07c`, `07d` |
| Flows in and out of named wallets | Each reserved wallet's balance at both dates and every day between; every transfer in the quarter grouped by counterparty; exact reconciliation | `08`, `08b`, `08c` |
| Labelled exchange wallets | Public name tags on the explorer | Section 6 of the report |
| Where the supply sits | All 10 billion RBNT, by the kind of address that owns it and by the address that physically holds it; completeness against total supply | `01`, `02`, `03` |

## 2. Definitions

* **Snapshot.** The snapshot for a moment T is the highest block whose
  timestamp is earlier than T. The start is the last block before 1 July 2026
  00:00 UTC and the end is the last block before 1 October 2026 00:00 UTC, so
  the end includes the whole of 30 September.

  | Snapshot | Block | Block time (UTC) |
  | --- | --- | --- |
  | Start, end of 30 June 2026 | 3,025,809 | 2026-06-30 23:57:19 |
  | End of 31 July 2026 | 3,104,242 | 2026-07-31 23:58:45 |
  | End of 31 August 2026 | 3,161,410 | 2026-08-31 23:57:49 |
  | End, end of 30 September 2026 | 3,209,414 | 2026-09-30 23:57:35 |

  Each day of the quarter and every seventh day also have a snapshot by the
  same rule (93 daily snapshots), used for the pools, WRBNT and the reserved
  wallets.
* **Holding** of an address = native RBNT + WRBNT balance + RBNT staked in
  either Reddex pool (`userInfo(address).amount`). Wrapping or staking is
  therefore never counted as selling.
* **Counted once.** RBNT inside the WRBNT contract backs WRBNT one to one, and
  the staked RBNT inside each pool belongs to its stakers. Both are counted
  with their owners and never again at the contract. The part of a pool's
  balance above its `totalStake` is that pool's **reward funds**. Any RBNT in
  the WRBNT contract above the WRBNT supply would be shown as "WRBNT contract
  surplus"; in this edition there is none.
* **Named addresses** are the nine reserved wallets on the DAO treasury page,
  the WRBNT contract, the two Reddex RBNT pools and any address the explorer
  gives a public name. They are reported by name and address.
* **Wallet** = an address with no code at the end block. An address carrying
  only an EIP-7702 delegation marker (`0xef0100...`) is still a key-held wallet.
  **Contract** = an address with code.
* **Contract kinds** come from the contract name in the verified source on the
  explorer (for a proxy, the name of its implementation). Rules, applied in
  order to the lower case name: `vest` vesting contracts; `safe`, `multisig`,
  `gnosis` multi-signature wallets; `bridge`, `oft`, `portal`, `gateway`,
  `teleport` bridge contracts; `pair`, `pool`, `swap`, `router`, `amm`,
  `algebra`, `liquidity` trading pools; `stak`, `farm`, `reward` other staking
  contracts; no verified source: unverified contracts; anything else: other
  verified contracts. A kind with fewer than five contracts is folded into
  "Other contracts". The rules are in `config/q3-2026.json`.
* **Holder counts, bands and concentration** use wallets holding at least
  1 RBNT. Named wallets and contracts are left out, because the reserved
  wallets are large by design and one contract can hold coins for many people.
  They are shown separately in section 1 of the report.
* **Bands** (lower bounds, RBNT): 1, 100, 1,000, 10,000, 100,000, 1 million,
  10 million, 100 million. A band with fewer than five wallets at any of the
  four main snapshots is merged into the band below it.
* **Cohorts** are fixed by holding at the start and followed to the end.
  "Added" means more than 1% higher, "reduced" more than 1% lower, "within 1%"
  otherwise, "below 1 at end" means the wallet ended under 1 RBNT.

### Pool balances include reward funds

Both pools run the verified contract `ReddexRBNTLockStaker`. `stake()` adds
the RBNT sent to the caller's `userInfo.amount` and to `totalStake`;
`unstake()` subtracts it and sends it back; rewards are paid in RBNT from the
pool's own balance. A pool's RBNT balance is therefore stakes plus reward
funds. As the brief asks, the headline staking figures are the pools' RBNT
balances at the start and end. The report then splits each balance into staked
RBNT (`totalStake`) and reward funds (balance minus `totalStake`).

### Network fees and governor addresses

Redbelly blocks name the zero address as their miner, yet fees are not
destroyed: the network credits them to addresses listed in block headers
(the governor set, in `extraData`) as balance changes without a transaction.
Those addresses are collected from every block header so their balances are
read too. This is also why every balance is read directly at each snapshot
instead of being rebuilt by adding up transfers.

## 3. Privacy rules applied

* Only named addresses are ever shown with a name or an address.
* Every other address is counted only inside a group of at least five. Size
  bands, stake size bands, contract kinds and lock calendar months with fewer
  than five members are merged or shown as "<5".
* Contract kinds come from the contract's own verified code, which describes
  the program, not who controls it. No owner is inferred.
* No label is guessed. The explorer labelled no exchange wallet in this
  edition, so no address is treated as an exchange.
* The local cache that holds per-address data (`cache/`) is never published.
  `scripts/10_verify.py` scans every published file and fails if any address
  outside the named list appears, and the same scan runs in the unit tests.

## 4. Data sources

| Source | Endpoint | What is read | Used for |
| --- | --- | --- | --- |
| Redbelly mainnet RPC, chain ID 151 | `https://governors.mainnet.redbelly.network` | `eth_getBlockReceipts` and `eth_getBlockByNumber` for every block, `eth_getBalance`, `eth_call` (`balanceOf`, `totalSupply`, `totalStake`, `userInfo`, `getStakeUnlockTimes`), `eth_getCode` | Every balance and pool figure |
| Routescan API (Etherscan compatible) | `https://api.routescan.io/v2/network/mainnet/evm/151/etherscan/api` | `txlistinternal` by block range from block 0, `getsourcecode`, `getblocknobytime` | Addresses reached only by internal transfers, quarter internal transfers for named wallet flows, contract kinds, cross-check of every snapshot block |
| Routescan address list | `https://api.routescan.io/v2/network/mainnet/evm/151/addresses` | The largest addresses and their public names | Labels only. Its balances are today's and rounded, so they are never used |
| Routescan WRBNT holder list | `https://api.routescan.io/v2/network/mainnet/evm/151/erc20/<WRBNT>/holders` | Addresses holding WRBNT | Making sure every WRBNT holder is read |
| Redbelly DAO treasury page | `https://redbellydao.network/treasury/` | Names, addresses and original allocations of the nine reserved wallets, from the table in the page's script | Naming the reserved wallets. The allocations are not balances |
| Reddex staking | `https://www.reddex.io/stake` and the pools' verified code | The two RBNT pools, lock periods, how rewards are paid | Staking section |
| Task Board brand kit | `https://taskboard.redbellydao.network/brand` | Colours, type, logo rules, voice | Design of the report, charts and cards |

The date every source was read is recorded in `data/processed/q3-2026/figures.json`
(`generated_utc`) and the independent re-check date in `verification.json`.

### Named addresses used

| Name | Address | Source |
| --- | --- | --- |
| Team (Locked) | `0xbCee2DEfb7cF136480e3619Cf93E8129059977aF` | DAO treasury page |
| Governance (Locked) | `0x9a83957d3399CBBCbEf2112797B4a5B8e58C63d4` | DAO treasury page |
| Governance (Unlocked) | `0x9E678318539D7C98057e9F89c58fb8f99752FaeA` | DAO treasury page |
| USYD/CSIRO (Locked) | `0xAC27381EF74457c1258d54a808C2461eEdc56270` | DAO treasury page |
| Investors | `0xeF816D556E01BC194AE302999930EAcD6dc4e566` | DAO treasury page |
| Reserve | `0x7473fEAf836b5319D9190d8367991Dc6ef33C16d` | DAO treasury page |
| Ecosystem (Locked) | `0xC5c131572d232512973e79204B93C2c1D57c879D` | DAO treasury page |
| Ecosystem 2 (Unlocked) | `0xE0c701c40166BBD8D5f5Ec33c123F0A03E902DF7` | DAO treasury page |
| Ecosystem (Unlocked) | `0x415cAD8Fc89F75a63C5B830E06460EEcdE083C9F` | DAO treasury page |
| Wrapped RBNT (WRBNT) | `0x6ed1f491e2d31536d6561f6bdb2adc8f092a6076` | Brief; labelled "Wrapped RBNT" on the explorer |
| Reddex RBNT staking pool, no lock | `0x43A1dc107BBb06dF266278056055AE7Fc5bd2817` | Brief |
| Reddex RBNT staking pool, 365 day lock | `0x5E8040e85D0E6363D798a43BEa939C026449946d` | Brief |

## 5. Steps

Each step is a script in `scripts/` and keeps its progress in
`cache/<edition>.sqlite`, so it can be stopped and restarted.

1. **`01_snapshots.py`** finds every snapshot block (start, end, month ends,
   weekly, daily) by binary search on block timestamps from the node, checks
   that the next block is at or after the boundary, and cross-checks each with
   the explorer's `getblocknobytime`. The explorer counts a block stamped
   exactly at the boundary as "before" it; that is the only difference allowed.
2. **`02_scan_chain.py`** reads `eth_getBlockReceipts` and the header of every
   block from 0 to the end block, in batches of up to 100 blocks (a batch the
   node refuses as too large is split until it fits). It keeps every sender,
   recipient and created contract, the logs of WRBNT and the two pools, the
   20-byte addresses in each header's `extraData`, and every transaction inside
   the quarter with its value and fee.
3. **`03_internal_transfers.py`** pages through the explorer's
   `txlistinternal` by block range from block 0 to the end block. A range that
   returns the 10,000 row limit is split in half until complete. Every party to
   a successful internal transfer with value, and every contract created
   internally, joins the address list; inside the quarter the full rows are kept.
4. **`04_explorer_labels.py`** reads the explorer's address list, largest
   first, for public name tags, and the WRBNT holder list.
5. **`05_balances.py`** reads, at the snapshot blocks: native RBNT of every
   address at the start and end, and at both month ends for every address that
   was non-zero at either end or active in the quarter (any other address
   cannot have changed); native RBNT of each named wallet daily; WRBNT
   `balanceOf` of every address that ever touched WRBNT and `totalSupply`;
   `userInfo` in both pools for every address that ever staked, and each
   pool's `totalStake` and balance at every snapshot; `getStakeUnlockTimes` for
   every open stake at the end; and `eth_getCode` at the end block for every
   address that held anything.
6. **`06_contracts.py`** reads the verified contract name of every contract
   that held at least 1 RBNT (counting WRBNT and stakes) at a main snapshot.
7. **`07_analyse.py`** builds every table in `data/processed/q3-2026/` and
   `figures.json`, running the exact checks below first. It stops if any fails.
8. **`08_charts.py`** draws every chart as SVG from the CSV files.
9. **`09_build.py`** writes the web page, the PDF (printed from the same page),
   the Word file (from the same content), the workbook, the community summary,
   the X thread and the social cards. Every number in the text is read from
   `figures.json` or a CSV, never typed by hand; sentences that describe a
   direction pick their verb from the numbers.
10. **`10_verify.py`** re-reads every named wallet balance, every pool's
    `totalStake` and the WRBNT supply straight from the node, re-reads 600
    random cached balances, re-checks the snapshot boundaries, scans every
    published file for unnamed addresses, dashes, emoji, price talk and credit
    lines, and checks every X post fits in 280 characters. Results go to
    `verification.json`.

### Checks that must pass

All are exact equalities in wei (1 RBNT = 10^18 wei), at every main snapshot
unless stated.

* WRBNT `totalSupply` equals the sum of every WRBNT balance, and the WRBNT
  contract holds at least that much RBNT.
* For each pool, the stakers' `userInfo` amounts add up to `totalStake`, and
  the pool's balance covers `totalStake`.
* For each pool over the quarter, RBNT in Stake records minus RBNT in Unstake
  records equals the change in `totalStake`.
* The lock calendar of the 365 day pool adds up to its `totalStake` at the end.
* Holdings (with WRBNT and stakes moved to their owners and reward funds left
  with the pools) add up to the native RBNT read, at every snapshot.
* Group changes add up to the change in RBNT located.
* Every reported contract kind has at least five members.
* Every named wallet reconciles: start balance + RBNT in - RBNT out - fees =
  end balance, to the wei.
* The balances read cover more than 99.99% of the 10 billion supply and never
  exceed it.

### Completeness

All 10 billion RBNT existed from the network's first block. The balances read
cover the share of supply stated in `01_supply_check.csv` at each snapshot. The
remainder sits at addresses that never appear in any transaction, internal
transfer or block header the scan could see, such as addresses funded at
genesis that never moved. It changes by only a few RBNT over the quarter, so
it cannot change any trend.

## 6. How to produce the next edition

1. Install Python 3.11 or later and `pip install -r requirements.txt`.
   Chromium is needed for the PDF and the chart PNGs (any Playwright install).
2. Copy `config/q3-2026.json` to `config/q4-2026.json`. Change `edition`,
   `period` and `main_snapshots` (month end names follow
   `month_YYYY-MM-01`), and set `snapshot_blocks` to null.
3. Re-read the DAO treasury page. If a wallet was added or changed, update
   `reserved_wallets` and the date in its `source`.
4. Run `make data analyse build verify EDITION=q4-2026`. A run from an empty
   cache reads about 3.3 million blocks from public endpoints. Busy stretches
   of the chain are split automatically.
5. Read the report end to end. Text that describes a direction is generated
   from the numbers, but read each sentence against the new figures.
6. If the explorer has started labelling exchange wallets, they appear in
   `figures.json` under `labelled_exchanges` and are added to the named list
   automatically; extend section 6 with their flows.
7. Run `make check` and publish only when `verify` ends with no failures.

## 7. Limits

* The chain shows that coins moved, not who controls an address or why. A fall
  in a group's holdings may be a sale, a move between a holder's own addresses,
  or a deposit into a contract.
* One address is not one person. Counts of wallets show how widely RBNT is
  spread across addresses.
* Internal transfers come from the explorer because the public node has no
  trace interface. They are checked indirectly: every named wallet, including
  the WRBNT contract and both pools, which move RBNT almost only through
  internal transfers, reconciles to the wei.
* The explorer's address list was read for its 20,000 largest addresses. A
  public label on a smaller address would not be seen.
