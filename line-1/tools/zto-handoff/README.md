# ZTO Handoff

Turn one exact, already reviewed ZTO/IMD planning bound into a compact handoff a
human or another worker can inspect. It first reruns `ZTO Review` against the
snapshot, report, and policy, then accepts only one amount that exactly matches
a complete reviewed candidate. The output binds the source digests, pinned
block, requested input, and minimum output with its own canonical digest.

It never prepares settlement: the output has no recipient, router, calldata,
gas choice, signature, key, or transaction. It is deliberately a handoff for
human review rather than something that can spend or send.

This round also adds an offline verifier for a handoff that has crossed a file
or worker boundary. It checks the exact schema, pinned pool, token direction,
canonical source digests, raw/display unit agreement, self-digest, and the
absence of settlement data. It checks the handoff itself, not the original
evidence; use the normal handoff command to re-review a snapshot/report/policy.

## One command to see it working

From the repository root, with Python 3.10+ and no installation or network:

```sh
python3 -B line-1/tools/zto-handoff/zto_handoff.py --demo --amount 100000000
```

The bundled offline demonstration uses real historical ZTO/IMD pool evidence at
Ethereum block 26,184,260. It returns `ready_for_human_review` for exactly
100,000,000 ZTO and a 1%-tolerance minimum of
1,184.169088029408336486 IMD. `--policy POLICY --snapshot SNAPSHOT --report
REPORT --amount AMOUNT` accepts caller-supplied workspace JSON and repeats the
same review before making a handoff.

To verify a saved handoff after transfer, run:

```sh
python3 -B line-1/tools/zto-handoff/zto_handoff.py --verify line-1/tools/zto-handoff/demo-handoff.json
```

The file path must be inside this workspace, is capped at 100 KB, and no
network call is made. An accepted result is integrity checking only: it is not
an execution approval or a fresh quote.

When the receiver also has the snapshot, report, and review policy, use the
stronger evidence check. It reruns the review, binds all three canonical source
digests to those supplied files, and rebuilds the exact handoff before
accepting it:

```sh
python3 -B line-1/tools/zto-handoff/zto_handoff.py --demo --verify-evidence line-1/tools/zto-handoff/demo-handoff.json
```

For caller evidence, replace `--demo` with `--policy POLICY --snapshot
SNAPSHOT --report REPORT`. This remains offline. It validates supplied
historical evidence only; it neither obtains a current quote nor prepares a
transaction.

To retain the reviewed, non-sending handoff for another worker, add a
workspace-local destination. The write happens only after the evidence review
and exact candidate selection succeed; the saved JSON is capped at 100 KB and
has no recipient, calldata, signature, or transaction data:

```sh
python3 -B line-1/tools/zto-handoff/zto_handoff.py --demo --amount 100000000 --save test/scratch/zto-handoff.json
```

`--save` is deliberately refused with `--verify` and `--verify-evidence`, so a
verification receipt cannot be mistaken for a newly reviewed planning handoff.

## What happened when tried

The demonstration succeeded offline and tests covered the accepted historical
candidate, rejection of an unreviewed or partial amount, report tampering,
handoff digest/unit/transaction tampering, and the no-network CLI path:

```sh
python3 -B -m unittest discover -s line-1/tools/zto-handoff -p 'test_*.py' -v
```

When tried this round, all ten focused tests passed. The committed
`demo-handoff.json` passed both the self-contained and evidence-backed
verifiers offline, and the new save command wrote the same self-digested
review handoff that it printed.

The output is a planning bound from a historical snapshot, not a current quote,
execution promise, state proof, router simulation, or MEV/gas/transfer model.
The caller supplies policy and tolerance; a changed pool can make a future
execution differ. It uses only standard-library Python plus committed sibling
Line 1 sources and never reads secrets or environment variables.
