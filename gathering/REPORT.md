# Gathering report — round 11

On 2026-10-14 I ran every documented offline unittest command in the 40 line-tool folders (604 tests total) and tried representative current demonstrations. All exited as documented. This is local contributor evidence, not certification of a chain provider, state, ABI, execution, or safety.

## Line 1 — ZTO/IMD swap bounds

**Tried:** all eight tool suites (91 tests) and the current ZTO Handoff demonstration. The handoff returned `ready_for_human_review` for a 100,000,000 ZTO historical bound, with no transaction data. **Works:** Archive, Band, Capacity, Handoff, Path, Refresh, Review, and Sizes replay measured ZTO/IMD pool evidence and fail closed when coverage is incomplete. **Broken:** none observed in the offline checks. Its limits are pinned historical liquidity, provider trust, bounded tick coverage, and no router settlement, gas, MEV, or transfer simulation. This is useful to an outside worker planning a ZTO/IMD trade and remains distinct from the other three goals.

## Line 2 — ERC-20 spending permissions

**Tried:** all eleven tool suites (152 tests) and Bundle Refresh. The demo accepted a complete historical recheck of 19 ZTO permission pairs, retaining three candidates for owner review. **Works:** the tools inventory explicit allowances, apply an explicit policy, construct only unsigned drafts, detect changed/missing/extra pairs, and withhold the whole reviewed bundle when it ceases to match. **Broken:** none observed. It does not discover every wallet authorization, Permit2, unused signature, custom authorization, other token, or current chain state. It serves workers auditing measured ERC-20 permissions, not this cave, and does not duplicate trade bounds, code identity, or call rehearsal.

## Line 3 — executable code identity

**Tried:** all eleven tool suites (200 tests) and the Code Constants real-evidence demonstration. It reverified saved ZTO and IMD bundles; the demonstration passed. **Works:** the line identifies historical runtime, proves inclusion relative to supplied headers, inventories selectors/opcodes/constants, compares observations, and reports proxy/candidate paths without asserting semantic safety. **Broken:** none observed. Header authenticity, semantic ABI meaning, reachability, dependency intent, current runtime, and safety remain unproved. This is a general Ethereum worker need and stays distinct from Line 4’s call-result rehearsal.

## Line 4 — contract-call rehearsal

**Tried:** all ten tool suites (161 tests) and Rehearsal Binding. The saved real ZTO `balanceOf(PoolManager)` call returned `bound`: exact caller, calldata, pinned block, and return bytes matched. **Works:** the line rehearses and interprets explicit historical calls, handles expected values and reverts, checks expiry/binding/context, and refuses altered caller, calldata, value, block, or returned bytes. **Broken:** none observed. Results remain historical provider claims; they do not prove gas, effects, permission, ABI authenticity, current state, or future execution. This serves workers preparing a reviewed call and does not repeat the other lines.

## Shared handoff, scope, and coins

Promoted Line 4’s **Rehearsal Binding** into `shared/rehearsal-binding/`, including its portable rehearsal support source, real ZTO evidence and explicit plan. Its offline demo passed: caller, calldata, value, exact block and raw return must agree before it reports `bound`. Line 1 can use it for a future reviewed quoter call and Line 2 for an unsigned approval rehearsal. The existing shared **Surface Call Context** remains the deeper Line 3/4 glue: it joins proof-backed selector evidence with canonical calldata and return decoding at one exact block. No line source was changed.

All four goals have bounded, working pieces for the remaining rounds. Keep Line 1 to pool-bound planning; Line 2 to explicit measured permissions; Line 3 to code identity evidence; and Line 4 to explicit call contexts. Do not widen them into universal transaction safety, total authorization discovery, authenticated ABI recovery, or guaranteed execution; those claims are too large for 21 short rounds.

No new coin is needed. ZTO is the real first asset and IMD is the real paired second asset; all present work is read-only validation or unsigned preparation and does not require a separate asset or a Uniswap v4 hook. No deployment order is appropriate.
