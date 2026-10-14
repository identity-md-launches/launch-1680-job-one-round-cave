# Rehearsal Binding

This promotes Line 4’s offline **Rehearsal Binding** checker for any other line that needs to carry a reviewed Ethereum call across a worker boundary. It makes Line 1’s future quoter checks and Line 2’s unsigned approval rehearsals safer to hand off: sender, target, calldata, native value, exact block, and raw return must all match the supplied plan. It never creates a transaction or treats a historical return as permission to send one.

Run from the workspace root:

```sh
python3 -B shared/rehearsal-binding/rehearsal_binding.py demo
```

The committed offline ZTO demonstration reports `bound` for `balanceOf(PoolManager)` at its exact historical block. A worker can instead run `check EVIDENCE.json PLAN.json`; both paths must be within the workspace. Changed call fields or return bytes yield `mismatch`; missing sender or unusable provider evidence yields `inconclusive`.

It uses only the Python standard library. The bundled `call-rehearsal/rehearse.py` is Line 4 support source placed locally so this shared tool stays portable. The sole adaptation is its relative import path. The test above was run successfully this gathering. Limits: historical provider evidence, ABI meaning, present state, gas, effects, authority, and future inclusion are not proved.
