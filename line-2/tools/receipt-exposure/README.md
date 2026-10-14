# Receipt Exposure

Before funding an owner with ZTO or IMD, calculate how a hypothetical net receipt can increase the amount already measured spenders could move. Empty balance never hides an active allowance. This is Python 3.10+ using only the standard library and existing sibling sources; no network or installation is needed.

From the repository root, one command shows it working:

```sh
python3 -B line-2/tools/receipt-exposure/receipt_exposure.py
```

This revalidates Bundle Refresh's saved **real ZTO** raw evidence at Ethereum block **26,187,572**, hash `0xfbdf6fb511bd7ee2e74dd1b2bd8982e05e2d4cf8d10e495e6b9789bc50e7997f`. It reports 19 pairs across 16 owners and three active permissions, two on empty balances. No receipt is assumed by this default command: `mode` is `historical_capacity_only`, every hypothetical receipt and incremental exposure is zero, and `maximum_additional_exposure_before_receipt_raw` shows remaining capacity under fixed measured allowances. These are historical provider claims, not newly fetched state.

## What happened when tried

On 2026-10-14, the default command reproduced that real inventory. The bundled `hypothetical-one-zto.json` explicitly assumes a **net receipt of one ZTO** to a real owner from the inventory whose historical balance was zero and allowance was uint256 maximum. Replaying this hypothetical scenario reported `incremental_combined_exposure_raw: "1000000000000000000"`; the entire assumed receipt fits under that existing allowance. This scenario is neither a real transfer nor an owner instruction. Its address comes from the actual raw evidence and is not a substitute for a user's recipient.

```sh
python3 -B line-2/tools/receipt-exposure/receipt_exposure.py --receipts line-2/tools/receipt-exposure/hypothetical-one-zto.json
```

Thirteen focused tests passed: real evidence replay, empty-balance receipts, zero permissions, overlapping allowances, finite ceilings, uint256 boundary/overflow, canonical decimal amounts, unmeasured owners, mismatched chain/token, duplicates/extra fields, missing raw reads, order independence/input immutability/digest binding, and CLI/workspace confinement. Synthetic state mutations stay in tests. `example-report.json` is the computed hypothetical result, clearly labelled as such; it is not raw chain evidence.

## Use your measured inventory and explicit scenario

Supply `--observation` with raw Allowance Lens or Allowance Changes evidence and optionally `--receipts` with an object following `hypothetical-one-zto.json`. All inputs must resolve inside the current workspace, be at most 96 KiB, and contain no duplicate JSON keys. All receipt entries have exactly `owner` and `amount_raw`; amounts are canonical decimal uint256 strings of **net balance increase**, in token base units. A decimal token amount, transfer fees, token price, or sender balance is not inferred. Chain ID must be integer 1 and the token must match the real ZTO/IMD evidence. Each listed owner must have measured permission evidence. Duplicate owners, unknown owners and balance overflow are refused. Omitted measured owners have explicitly labelled zero scenario receipts. No owner address is guessed.

For owner balance `B`, net receipt `R`, and sum of measured allowances `A`, the combined upper bound changes from `min(B,A)` to `min(B+R,A)`. Their difference is incremental combined exposure. Per-spender bounds use each individual allowance, overlap, and must not be added as an owner total. Maximum additional exposure is `min(uint256_max,A) - min(B,A)`, measured before the scenario. It is theoretical capacity, not a prediction of receipts or an executable amount. All arithmetic is integer-only, including sums above uint256 for multiple distinct permissions; hypothetical owner balance remains uint256-bounded.

`receipt_outside_measured_combined_bound_raw` is merely the assumed receipt minus incremental measured exposure. It **does not certify those units safe**: unknown spenders and other authorizations may still reach them. Allowances stay fixed in this model; spending, revocation, new grants, rebase, fees and nonstandard token behavior can invalidate it. No policy pass, revoke advice, wallet-wide safety claim, freshness check or transaction authority is returned. Unknown spenders, Permit2, unused signatures, custom authorizations, other tokens and chains remain outside coverage. Evidence and headers are trusted RPC claims, not state proofs. SHA-256 binds parsed input objects but does not authenticate them.

Exit 0 prints a valid bounded assessment; exit 1 refuses malformed or inconsistent inputs. The tool prints JSON and writes nothing. It never opens a key or wallet, reads environment variables, contacts a network, builds/simulates/signs/sends a transaction, pays, posts or deploys.

```sh
python3 -B -m unittest discover -s line-2/tools/receipt-exposure -p 'test_*.py' -v
```
