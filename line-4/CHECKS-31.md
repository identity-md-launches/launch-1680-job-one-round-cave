# Rehearsal Binding — checks

On 2026-10-14 the offline demo printed `bound` and exited 0 for the real
historical ZTO/PoolManager balance query. Its result was
285939607966355541747129965 base units at block 26,187,032. The saved demo plan
was derived from the observation to demonstrate the binding; it does not prove
an independently predicted balance or a current balance. No new chain request
or transaction was made.

The 20 focused tests passed. They exercise exact context and result checks,
changed sender/target/calldata/value, all three block fields, absent sender,
revert/RPC errors, malformed returns, empty-success versus empty-revert,
explicit ABI false, strict schemas, relay-provenance preservation, fingerprints,
input containment/size/duplicate keys and CLI exit codes.

All 141 inherited Line 4 tests also passed, **161 tests total**. Per-tool results
are in `test-results-31.json`. These local tests are evidence of the tested
behavior, not independent verification, provider authentication or future
transaction success.

`GOAL.md` and every older numbered record/tool are unchanged. The new record is
31 because there were 30 numbered JSON records before this task. The record's
artifact hash equals both final PNGs; its thumbnail is 512 × 512 and below
100 KB. Both PNG output paths remain untracked for the upload daemon. Only the
new numbered record/thumbnail and Line 4 source/notes are source deliverables.
The finished image and visual limitations are described in `VISUAL-31.md`;
measured preservation and hashes are in `delivery-checks-31.json`.

Final worktree checks passed: allowed path scope, all new non-artifact files
below 100 KB, byte-identical GOAL.md and older JSON/JPEG records, exact new
record shape/count and image hash, identical final PNGs, and local runtime
source availability. Git staging/commit could not run because `.git/index.lock`
is on a read-only filesystem. All deliverables remain present as ordinary
workspace files for the network's collection; no dependency was installed and
no submodule was introduced.
