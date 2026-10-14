#!/usr/bin/env python3
"""Inspect proof-backed Solidity trailer claims; optionally hash-check local JSON."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS / 'code-ancestry'))
import code_ancestry as ancestry

proof, lens = ancestry.proof, ancestry.lens
require = lens.require
MAX_TRAILER = 1024


def head(data, pos):
    require(pos < len(data), 'truncated CBOR head')
    byte = data[pos]
    major, extra = byte >> 5, byte & 31
    pos += 1
    if extra < 24:
        return major, extra, pos
    widths = {24: 1, 25: 2, 26: 4, 27: 8}
    require(extra in widths, 'indefinite/reserved CBOR form unsupported')
    width = widths[extra]
    require(pos + width <= len(data), 'truncated CBOR length')
    value = int.from_bytes(data[pos:pos + width], 'big')
    require(value >= (24 if width == 1 else 1 << (8 * (width // 2))),
            'nonminimal CBOR length')
    return major, value, pos + width


def atom(data, pos):
    major, size, pos = head(data, pos)
    if major == 7 and size in (20, 21):
        return 'bool', size == 21, pos
    require(major in (2, 3), 'only bytes, text and boolean values supported')
    require(size <= 256 and pos + size <= len(data), 'truncated/oversized CBOR string')
    raw = data[pos:pos + size]
    return ('bytes', raw, pos + size) if major == 2 else ('text', raw.decode('utf-8'), pos + size)


def parse_map(data):
    major, count, pos = head(data, 0)
    require(major == 5 and 1 <= count <= 8, 'expected a map with 1 to 8 entries')
    entries = {}
    for _ in range(count):
        kind, key, pos = atom(data, pos)
        require(kind == 'text' and 1 <= len(key) <= 32 and key.isascii(), 'invalid metadata key')
        require(key not in entries, 'duplicate metadata key')
        kind, value, pos = atom(data, pos)
        entries[key] = (kind, value)
    require(pos == len(data), 'trailing CBOR bytes')
    return entries


def base58(raw):
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    value, result = int.from_bytes(raw, 'big'), ''
    while value:
        value, digit = divmod(value, 58)
        result = alphabet[digit] + result
    return '1' * (len(raw) - len(raw.lstrip(b'\0'))) + result


def scan(code):
    require(isinstance(code, bytes) and 0 < len(code) <= lens.MAX_CODE, 'invalid runtime size/type')
    result = {'full_runtime_keccak256': lens.digest(code), 'runtime_bytes': len(code),
              'status': 'no-recognized-trailer', 'trailer': None,
              'metadata_excluded_from_identity': False}
    if len(code) < 3:
        result['reason'] = 'runtime too short for a trailer'
        return result
    size = int.from_bytes(code[-2:], 'big')
    start = len(code) - size - 2
    if not 1 <= size <= MAX_TRAILER or start < 0:
        result['reason'] = 'suffix length is outside supported bounds'
        return result
    try:
        entries = parse_map(code[start:-2])
        require(set(entries) <= {'solc', 'ipfs', 'bzzr0', 'bzzr1', 'experimental'},
                'unknown metadata key; no recognized trailer claim')
        version = entries.get('solc')
        commitments = []
        for key in ('ipfs', 'bzzr0', 'bzzr1'):
            if key not in entries:
                continue
            kind, raw = entries[key]
            require(kind == 'bytes' and len(raw) == (34 if key == 'ipfs' else 32),
                    'unsupported commitment type/length')
            item = {'kind': key, 'raw_hex': '0x' + raw.hex()}
            if key == 'ipfs':
                require(raw[:2] == b'\x12\x20', 'unsupported IPFS multihash; need sha2-256/32')
                item.update({'cid_v0': base58(raw), 'dag_pb_sha256': raw[2:].hex()})
            commitments.append(item)
        require(len(commitments) <= 1, 'multiple metadata commitment schemes')
        compiler = None
        if version is not None:
            kind, value = version
            if kind == 'bytes':
                require(len(value) == 3, 'release compiler version must be three bytes')
                compiler = {'encoding': 'release-bytes', 'claim': '.'.join(map(str, value))}
            else:
                require(kind == 'text' and 1 <= len(value) <= 128 and value.isascii()
                        and all(32 <= ord(c) < 127 for c in value), 'unsupported compiler version text')
                compiler = {'encoding': 'prerelease-text', 'claim': value}
        require(compiler is not None or commitments, 'missing compiler or commitment')
        experimental = None
        if 'experimental' in entries:
            require(entries['experimental'][0] == 'bool', 'experimental flag must be boolean')
            experimental = entries['experimental'][1]
        result.update({'status': 'recognized-trailer-claim', 'trailer': {
            'start': start, 'end_exclusive': len(code), 'cbor_bytes': size,
            'total_bytes': size + 2, 'keccak256': lens.digest(code[start:]),
            'raw_hex': '0x' + code[start:].hex(), 'compiler': compiler,
            'commitments': commitments, 'experimental': experimental,
            'prefix_keccak256_diagnostic': lens.digest(code[:start]),
            'prefix_bytes': start}})
    except (ValueError, UnicodeDecodeError) as error:
        result['reason'] = str(error)
    return result


def varint(value):
    require(type(value) is int and 0 <= value < 2**64, 'invalid protobuf varint')
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def ipfs_multihash(raw):
    """Solidity's single-chunk UnixFS File / DAG-PB encoding, not raw-file SHA256.

    Bound below the compiler's 262144-byte chunk boundary. No links, directory,
    raw-leaf codec, mode or timestamp. Larger files deliberately unsupported.
    """
    require(isinstance(raw, bytes) and len(raw) <= lens.MAX_RESPONSE,
            'IPFS metadata exceeds single-chunk supported bound')
    size = varint(len(raw))
    unixfs = b'\x08\x02' + (b'\x12' + size + raw if raw else b'') + b'\x18' + size
    block = b'\x0a' + varint(len(unixfs)) + unixfs
    return b'\x12\x20' + hashlib.sha256(block).digest()


def reject_constant(value):
    raise ValueError('nonfinite JSON value: ' + value)


def metadata_match(runtime, raw):
    """Bind exact raw JSON bytes to a supported multihash, not to compiler output."""
    require(isinstance(raw, bytes) and 0 < len(raw) <= lens.MAX_RESPONSE, 'invalid metadata JSON size/type')
    trailer = runtime['trailer']
    require(trailer is not None, 'no recognized trailer for metadata matching')
    commitments = trailer['commitments']
    require(len(commitments) == 1 and commitments[0]['kind'] == 'ipfs',
            'metadata matching supports only IPFS sha2-256, not Swarm or compiler-only trailers')
    multihash = ipfs_multihash(raw)
    require('0x' + multihash.hex() == commitments[0]['raw_hex'],
            'metadata exact-byte UnixFS/DAG-PB commitment mismatch')
    # UTF-8 is explicit: accepting UTF-16/32 auto-detection would obscure the file format.
    document = json.loads(raw.decode('utf-8'), object_pairs_hook=ancestry.no_duplicates,
                          parse_constant=reject_constant)
    require(isinstance(document, dict), 'metadata JSON must be an object')
    return {'raw_bytes': len(raw), 'raw_file_sha256': hashlib.sha256(raw).hexdigest(),
            'cid_v0': base58(multihash), 'dag_pb_sha256': multihash[2:].hex(),
            'ipfs_encoding': 'single-chunk-unixfs-file-dag-pb', 'exact_byte_commitment_matched': True,
            'json_object_validated': True, 'source_compilation_verified': False}


def inspect(bundle, anchor_hash=None, metadata_bytes=None, metadata_address=None):
    checked = proof.verify(bundle, anchor_hash)
    require((metadata_bytes is None) == (metadata_address is None),
            'metadata JSON and runtime address must be supplied together')
    selected = lens.address(metadata_address) if metadata_address is not None else None
    runtimes, seen = [], {}
    for node in bundle['observation']['nodes']:
        for item, role in ((node, 'candidate-path'), (node.get('beacon'), 'beacon')):
            if item is None:
                continue
            address = lens.address(item['address'])
            raw = lens.code_bytes(item['code'])
            if address in seen:
                require(seen[address]['full_runtime_keccak256'] == lens.digest(raw),
                        'conflicting runtime for the same address')
                if role not in seen[address]['roles']:
                    seen[address]['roles'].append(role)
                continue
            result = {'address': address, 'roles': [role], **scan(raw)}
            seen[address] = result
            runtimes.append(result)
    matched = None
    if selected is not None:
        require(selected in seen, 'metadata address is not a proved runtime in this bundle')
        matched = {'address': selected, **metadata_match(seen[selected], metadata_bytes)}
    return {'schema': 'code-metadata-result-v1', 'chain_id': 1, 'target': checked['target'],
            'code_block': ancestry.block_identity(bundle['observation']['block']),
            'proof': checked, 'runtimes': runtimes, 'metadata_match': matched,
            'source_compilation_verified': False, 'metadata_unreachable_verified': False,
            'scope': 'Trailer syntax and claims only. Full runtime remains the identity. '
                     'Compiler claims can be forged and suffix bytes can execute or be read. '
                     'An exact JSON hash match does not prove compilation, sources, routing or safety. '
                     'Supplied headers need independent trust; no current-code claim or network fetch.'}


def read_bytes(filename):
    path = Path(filename).resolve()
    require(path.is_relative_to(Path.cwd().resolve()), 'metadata input must be inside workspace')
    with path.open('rb') as stream:
        raw = stream.read(lens.MAX_RESPONSE + 1)
    require(0 < len(raw) <= lens.MAX_RESPONSE, 'metadata input exceeds bounds')
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, help='workspace-local raw Code Proof bundle')
    parser.add_argument('--anchor-hash', help='independently chosen execution block hash')
    parser.add_argument('--metadata-json', help='exact workspace-local Solidity metadata JSON bytes')
    parser.add_argument('--metadata-address', help='proved runtime whose commitment to check')
    args = parser.parse_args()
    try:
        require(bool(args.metadata_json) == bool(args.metadata_address),
                '--metadata-json and --metadata-address must be supplied together')
        result = inspect(ancestry.read_json(args.bundle), args.anchor_hash,
                         read_bytes(args.metadata_json) if args.metadata_json else None,
                         args.metadata_address)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, OverflowError, AttributeError,
            IndexError, RecursionError) as error:
        print('Code Metadata: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
