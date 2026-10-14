"""Replay real historical ZTO then IMD proofs; no network or invented anchor."""
import json
from pathlib import Path
import code_metadata as metadata


def main():
    folder = Path(__file__).resolve().parent
    results = []
    for token in ('zto', 'imd'):
        bundle = metadata.ancestry.read_json(folder.parent / 'code-delta' / (token + '-later-proof.json'))
        results.append({'token': token.upper(), **metadata.inspect(bundle)})
    zto, imd = [result['runtimes'][0] for result in results]
    passed = (all(r['proof']['anchor'] == 'unanchored-rpc-header' for r in results)
              and all(r['trailer']['compiler']['claim'] == '0.8.26' for r in (zto, imd))
              and zto['trailer']['total_bytes'] == 12 and zto['trailer']['commitments'] == []
              and imd['trailer']['total_bytes'] == 53
              and imd['trailer']['commitments'][0]['dag_pb_sha256']
              == 'c5b90da65cf00d90c56d2e172bbb6442c6881e0755c799a13ebb411adf53f299'
              and all(not r['source_compilation_verified'] for r in results))
    return {'demonstration_passed': passed, 'results': results,
            'scope': 'Real historical proof replay. No metadata file fetched or compilation certified.'}


if __name__ == '__main__':
    result = main()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['demonstration_passed'] else 1)
