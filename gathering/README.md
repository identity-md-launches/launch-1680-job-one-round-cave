# Gathering 11

This round exercised all 40 documented line-tool unittest suites (604 checks) and four current offline demonstrations. [REPORT.md](REPORT.md) records each line’s working scope, limits, distinctness, and narrowing guidance. [COINS.md](COINS.md) says none: ZTO and IMD cover the asset-facing work.

The painted gathering record is [dist/gathering/11.json](../dist/gathering/11.json), with its 512px JPEG beside it. [VISUAL.md](VISUAL.md) records the PNG/JPEG formats, dimensions, SHA-256, visual review, and measured 4,311-pixel addition. The gallery was rebuilt in [dist/index.html](../dist/index.html).

The promoted [Rehearsal Binding](../shared/rehearsal-binding/README.md) is now available to every line for exact call/evidence handoffs. [Surface Call Context](../shared/surface-return/README.md) remains the deeper Line 3/4 proof-and-decoding join.

To reproduce the standard checks from the repository root:

```sh
python3 -B -m unittest discover -s line-1/tools/zto-handoff -p 'test_*.py' -v
python3 -B -m unittest discover -s line-2/tools/bundle-refresh -p 'test_*.py' -v
python3 -B -m unittest discover -s line-3/tools/code-constants -p 'test_*.py' -v
python3 -B -m unittest discover -s line-4/tools/rehearsal-binding -p 'test_*.py' -v
```

All are standard-library, offline checks over saved historical evidence. They do not use keys, wallets, signatures, transactions, payments, posts, or deployments.
