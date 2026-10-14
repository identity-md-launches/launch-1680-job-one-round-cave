# Rehearsal Binding

Check that a proposed Ethereum call still has the exact sender, target, calldata,
native value, reviewed block and expected return bytes of its saved rehearsal.
This catches a changed proposal before someone considers sending it. Python
3.9+ standard library only; no installation, wallet or network access is needed.

Run from the repository root:

```sh
python3 -B line-4/tools/rehearsal-binding/rehearsal_binding.py demo
```

When tried on 2026-10-14, this printed `bound` for the real saved ZTO
`balanceOf(address)` query at Ethereum block **26,187,032**. Its explicit simulated
caller and queried account are the assignment's real Uniswap v4 PoolManager,
`0x000000000004444c5dc75cb358380d2e3de08a90`. It returned
**285939607966355541747129965** raw ZTO units. This is the PoolManager's overall
ZTO balance, not the assigned pool's balance, liquidity or spendable amount.
The raw evidence was copied unchanged from the gathering's actual public-chain
trial, attributed to https://ethereum-rpc.publicnode.com. The demonstration plan
was derived from that historical observation: it shows binding mechanics, not
an independently predicted balance. No new live call is made by this tool.

For your own reviewed plan and saved Call Rehearsal evidence:

```sh
python3 -B line-4/tools/rehearsal-binding/rehearsal_binding.py check path/to/observation.json path/to/plan.json
```

`zto-plan.json` is a complete example. The plan has exactly these fields:

- `schema`: `rehearsal-binding-v1`.
- `chain_id`: integer `1`, Ethereum mainnet.
- `call`: exactly `from`, `to`, `data`, `value`; addresses are nonzero 20-byte
  hex strings, data is even-length hex, value is a canonical RPC hex quantity
  in native ETH wei. A sender is mandatory even for a read-only call.
- `block`: exactly `number`, `hash`, `timestamp`, taken from the reviewed
  rehearsal. Number and timestamp are canonical RPC hex quantities, hash is
  32-byte hex. Latest block names are not accepted.
- `expected_return`: exact even-length hexadecimal return bytes.

Use the actual intended caller and the reviewed proposal, not values invented
by the tool. Never add keys or secrets. Contract callers are legitimate simulation
contexts but may be impossible to use as a directly originating transaction.
The plan is a call description, not a signed or broadcastable transaction.
Nonce, gas, fees, access lists and wallet wrappers are deliberately unsupported;
extra fields are rejected rather than silently dropped. To review a wallet's
wrapped transaction, rehearse its actual outer call separately.

`bound` exits 0 only when the explicit caller, all call bytes, all three block
fields and expected successful return bytes match. `mismatch` exits 1 and lists
changed fields, or explains a reported revert. `inconclusive` exits 2 for invalid
input, absent sender evidence, RPC failure or a malformed selected return type.
Hex letter case is normalized; absent sender evidence is never defaulted to zero
or inferred from context. A successful empty raw return is distinct from an empty
revert. A canonical ABI `false` can be bound if those were the expected bytes:
byte agreement does not imply the application's success condition.

The report includes normalized context, the provider's reinterpreted outcome,
field differences, a SHA-256 of the normalized plan and a SHA-256 of the original
parsed evidence (sorted compact ASCII JSON). These are content fingerprints,
not signatures or provider authentication. Updated Call Rehearsal's optional
contributor-relay provenance is retained, including its attribution and
independence limitations. Forged flags and unknown observation fields are refused.
Inputs must resolve inside the current workspace, are limited to 95 KB each,
and reject duplicate keys and non-finite JSON numbers.

Focused checks:

```sh
python3 -B -m unittest discover -s line-4/tools/rehearsal-binding -p 'test_*.py' -v
```

All 20 tests passed. They cover the real historical query, each call/block
mutation, changed return bytes, missing caller evidence, revert versus empty
success, provider errors, malformed ABI returns, explicit false returns,
provenance, normalized fingerprints, strict input fields, bounded JSON,
workspace containment and all CLI exit categories. Mutated observations in the
tests are synthetic refusal fixtures, not chain observations.

Keep this folder and its sibling `call-rehearsal/` together when copying the
piece. It loads that reviewed standard-library core without modifying it, uses
its input validators and return interpreter, and never calls its collector.
Neither the checker nor the demo reads environment variables, wallets, keys or
files outside the workspace, signs, sends, pays, posts or deploys anything.
A bound result remains a historical provider claim, not a state-effect proof,
a gas estimate, ABI authentication, current-state check or future execution promise.
