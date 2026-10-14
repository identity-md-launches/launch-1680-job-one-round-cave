# Code Metadata

Inspect the compiler/version and content-hash claims in a contract's historical runtime before looking for its source. Every run first re-verifies the raw Ethereum account, storage and header proofs. An optional local JSON check binds the exact file bytes to a supported IPFS commitment. Python 3.9+ and the standard library only; no installation or network is needed.

One command from the repository root shows it working on **real saved ZTO first, then IMD evidence**:

```sh
python3 -B line-3/tools/code-metadata/demo.py
```

Expected: `demonstration_passed: true`. Keep the committed sibling Code Ancestry, Code Proof, Code Lens (including Keccak), and Code Delta's saved evidence files. The demo does not import a saved verdict or invent an independent block anchor.

## What happened when tried

Both raw proof bundles at Ethereum block **26,187,032** reverified. These are earlier contributors' actual read-only observations, replayed offline in this round; no new live observation is claimed. Public attribution is Ethereum PublicNode, with the inherited relay provenance explicitly attribution-only. The header remains `unanchored-rpc-header`.

| Runtime | Full bytes | Trailer range, half-open | Compiler claim | Source commitment claim |
| --- | ---: | --- | --- | --- |
| ZTO | 1,287 | [1275, 1287), 12 bytes | 0.8.26 | None in this supported trailer |
| IMD | 22,990 | [22937, 22990), 53 bytes | 0.8.26 | IPFS CIDv0 `QmbeUgrzSGcxFDjsbhXyXzpvxuwqguRFsuPftmxTbkV3P6` |

ZTO's compiler-only trailer supplies no metadata content hash to verify. IMD's commitment is reported, but its metadata JSON has **not** been fetched or checked. `demo-result.json` records the complete replay. The original full runtime Keccak identities are retained, including the trailer; prefix hashes are diagnostics only.

The 23 tests passed, covering both real proof replays, corrupted proofs and consistent-looking bytecode forgeries, malformed/duplicate/unknown CBOR fields, all truncations, version encodings, experimental flags, old Swarm claims, IPFS bounds and published CID vectors, exact-byte changes, nonfinite/duplicate/invalid JSON, metadata-address membership, role deduplication/conflicts, 500 deterministic hostile byte strings, workspace boundaries and CLI failure with empty stdout. Synthetic runtimes and mocked proof joins are explicitly test fixtures, never saved chain evidence. A direct SHA-256-of-JSON implementation error was caught and repaired before delivery; the final matcher encodes Solidity's UnixFS/DAG-PB single-chunk file format.

## Inspect another bundle

```sh
python3 -B line-3/tools/code-metadata/code_metadata.py --bundle line-3/tools/code-delta/imd-later-proof.json
```

To check a metadata file you already possess, supply `--metadata-json` with its workspace-local path and `--metadata-address` with the observed runtime address. For the IMD example that address is `0xd34a99bc0f67ae1bbd63c660e6d0b0dd03e263b7`. The address must occur in the proved candidate path or beacon runtime inventory. No default address or unknown file is substituted. The matcher requires a UTF-8 JSON object with no duplicate keys or nonfinite numbers; it does not validate the Solidity metadata document schema.

File bytes, whitespace and line endings all matter. The tool reconstructs a **single-chunk UnixFS File in DAG-PB**, then compares its SHA-256 multihash to the observed `ipfs` value. It also reports the raw file SHA-256 separately. Raw-file SHA-256 alone does not implement a Solidity CIDv0 check. Files are limited to 100,000 bytes, below the compiler's chunk boundary; multichunk files, alternative importer parameters, Swarm payload verification and other multihash algorithms are unsupported. Nothing is downloaded, signed, sent, posted, paid or deployed. The tool reads no environment variables, wallets or secrets, and only explicitly requested files inside the current workspace.

Optional `--anchor-hash` checks equality against a caller-supplied execution block hash. Obtain its authenticity independently; copying the bundle's hash does not create trust. A hash match still does not certify consensus or finality.

Exit 0 means inspection completed, including a diagnostic `no-recognized-trailer` when syntax is absent, unknown or outside bounds. Invalid proof/file/anchor, unproved selected address, unsupported payload commitment, JSON error or hash mismatch exits 1 with no JSON on stdout. CLI syntax errors exit 2. The tool writes no files itself.

## Recognition and limits

The final two bytes are interpreted as a big-endian CBOR byte length. The supported definite map has 1–8 entries, at most 1,024 CBOR bytes, unique ASCII keys, minimally encoded lengths, and bounded text/byte-string/boolean values. Supported keys are `solc`, `ipfs`, `bzzr0`, `bzzr1` and `experimental`. Release versions use three bytes; prerelease text is displayed as an unverified claim. Swarm commitments must be 32 bytes. IPFS commitments must be the supported 34-byte sha2-256 multihash. Unknown fields, nested structures, tags, indefinite forms, oversized values and multiple commitment schemes produce a diagnostic rather than a guessed interpretation. Old Swarm-only claims can be inventoried without a compiler version.

Anyone can append a plausible trailer or encode a false compiler claim. Suffix bytes can be executed, copied or inspected by the contract. **No bytes are discarded from code identity.** A matching metadata commitment binds that JSON to those runtime bits relative to the supplied header; it does not prove that a compiler produced the runtime from those sources. No source fetching, recompilation, source-file integrity, custom proxy routing, ABI meaning, code safety, current code, continuous stability or anchor authenticity is certified. Beacon call results retain the inherited unproven warning.

Run the focused checks:

```sh
python3 -B -m unittest discover -s line-3/tools/code-metadata -p 'test_*.py' -v
```

Format references: [Solidity metadata](https://docs.soliditylang.org/en/v0.8.28/metadata.html), [Solidity 0.8.26 IPFS encoding](https://raw.githubusercontent.com/ethereum/solidity/v0.8.26/libsolutil/IpfsHash.cpp), [UnixFS specification](https://specs.ipfs.tech/unixfs/), and [published CID vector](https://specs.ipfs.tech/ipips/ipip-0499/).

The mark's meaning: **Pepe looks beneath the skin of a code stone.**
