"""Real proof replay plus explicitly synthetic hostile CBOR/JSON fixtures."""
import copy
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest
from unittest.mock import patch
import code_metadata as m

FOLDER = Path(__file__).resolve().parent
SCRATCH = Path.cwd() / 'test/scratch/code-metadata'


def evidence(token='zto'):
    return m.ancestry.read_json(FOLDER.parent / 'code-delta' / (token + '-later-proof.json'))


def trailer(cbor, prefix=b'\x00\xfe'):
    return prefix + cbor + len(cbor).to_bytes(2, 'big')


def string(value, text=False):
    raw = value.encode() if text else value
    major = 0x60 if text else 0x40
    return (bytes([major + len(raw)]) if len(raw) < 24 else bytes([major + 24, len(raw)])) + raw


def mapping(pairs):
    return bytes([0xa0 + len(pairs)]) + b''.join(string(key, True) + value for key, value in pairs)


SOLC = string(bytes([0, 8, 26]))


def ipfs_runtime(raw):
    return m.scan(trailer(mapping([('ipfs', string(m.ipfs_multihash(raw))),
                                  ('solc', SOLC)])))


class MetadataTests(unittest.TestCase):
    def test_real_proofs_and_exact_identity(self):
        for token, start, size in [('zto', 1275, 12), ('imd', 22937, 53)]:
            bundle = evidence(token)
            result = m.inspect(bundle)
            runtime = result['runtimes'][0]
            self.assertEqual(runtime['full_runtime_keccak256'], bundle['observation']['nodes'][0]['code_hash'])
            self.assertEqual(runtime['trailer']['start'], start)
            self.assertEqual(runtime['trailer']['total_bytes'], size)
            self.assertEqual(runtime['trailer']['compiler']['claim'], '0.8.26')
            self.assertFalse(runtime['metadata_excluded_from_identity'])
            self.assertFalse(result['metadata_unreachable_verified'])
            self.assertFalse(result['source_compilation_verified'])
            self.assertEqual(result['proof']['anchor'], 'unanchored-rpc-header')
            self.assertTrue(result['proof']['state_inclusion_verified'])

    def test_known_base58_and_real_multihash(self):
        self.assertEqual(m.base58(b'\x00\x00\x01'), '112')
        self.assertEqual(m.base58(b'hello world'), 'StV1DL6CwTryKyV')
        result = m.inspect(evidence('imd'))['runtimes'][0]['trailer']['commitments'][0]
        self.assertEqual(result['raw_hex'], '0x1220c5b90da65cf00d90c56d2e172bbb6442c6881e0755c799a13ebb411adf53f299')
        self.assertTrue(result['cid_v0'].startswith('Qm'))

    def test_order_independent_and_experimental(self):
        for pairs in [[('solc', SOLC), ('experimental', b'\xf5')],
                      [('experimental', b'\xf4'), ('solc', SOLC)]]:
            result = m.scan(trailer(mapping(pairs)))
            self.assertEqual(result['status'], 'recognized-trailer-claim')
            self.assertEqual(result['trailer']['experimental'], pairs[0][0] == 'solc')

    def test_prerelease_version_text(self):
        claim = '0.8.26-nightly.2024.4.1+commit.abc12345'
        result = m.scan(trailer(mapping([('solc', string(claim, True))])))
        self.assertEqual(result['trailer']['compiler'], {'encoding': 'prerelease-text', 'claim': claim})

    def test_old_swarm_claim_without_version(self):
        for key in ('bzzr0', 'bzzr1'):
            result = m.scan(trailer(mapping([(key, string(bytes(32)))])))
            self.assertEqual(result['status'], 'recognized-trailer-claim')
            self.assertIsNone(result['trailer']['compiler'])
            with self.assertRaisesRegex(ValueError, 'only IPFS'):
                m.metadata_match(result, b'{}')

    def test_compiler_only_has_no_source_commitment(self):
        runtime = m.scan(trailer(mapping([('solc', SOLC)])))
        with self.assertRaisesRegex(ValueError, 'only IPFS'):
            m.metadata_match(runtime, b'{}')

    def test_unknown_key_duplicate_trailing_refused(self):
        for raw in [mapping([('solc', SOLC), ('evil', string(b'x'))]),
                    mapping([('solc', SOLC), ('solc', SOLC)]),
                    mapping([('solc', SOLC)]) + b'\x00']:
            self.assertEqual(m.scan(trailer(raw))['status'], 'no-recognized-trailer')

    def test_wrong_types_lengths_and_missing_fields(self):
        fixtures = [[('solc', b'\xf5')], [('solc', string(b'\x00\x08'))],
                    [('solc', string('', True))], [('solc', string('a\n', True))],
                    [('ipfs', string(bytes(34)))], [('ipfs', string(bytes(33)))],
                    [('bzzr1', string(bytes(31)))], [('experimental', b'\xf5')],
                    [('solc', SOLC), ('experimental', string(b'true'))],
                    [('solc', SOLC), ('ipfs', string('text', True))],
                    [('bzzr0', string(bytes(32))), ('bzzr1', string(bytes(32)))]]
        for pairs in fixtures:
            self.assertEqual(m.scan(trailer(mapping(pairs)))['status'], 'no-recognized-trailer', pairs)

    def test_nonminimal_indefinite_tag_array_integer(self):
        for raw in [b'\xbf\xff', b'\xa0', b'\x98\x01\x00', b'\xc0\xa1',
                    b'\xb8\x01' + mapping([('solc', SOLC)])[1:],
                    b'\xa1\x78\x04solc' + SOLC,
                    b'\xa1\x64solc\x58\x03\x00\x08\x1a',
                    b'\xa1\x64solc\x01', b'\xa1\x64solc\x81\x01']:
            self.assertEqual(m.scan(trailer(raw))['status'], 'no-recognized-trailer')

    def test_all_truncations_and_suffix_length_bounds(self):
        cbor = mapping([('solc', SOLC), ('ipfs', string(b'\x12\x20' + bytes(32)))])
        for index in range(len(cbor)):
            self.assertEqual(m.scan(trailer(cbor[:index]))['status'], 'no-recognized-trailer')
        for code in (b'\x00', b'\x00\x00', b'\x00\x00\x00', b'\x00\xff\xff',
                     b'\x00' * 1100 + (1025).to_bytes(2, 'big')):
            self.assertEqual(m.scan(code)['status'], 'no-recognized-trailer')

    def test_same_prefix_never_same_full_identity(self):
        first = m.scan(trailer(mapping([('solc', SOLC)])))
        second = m.scan(trailer(mapping([('solc', string(bytes([0, 8, 27])))])))
        self.assertEqual(first['trailer']['prefix_keccak256_diagnostic'], second['trailer']['prefix_keccak256_diagnostic'])
        self.assertNotEqual(first['full_runtime_keccak256'], second['full_runtime_keccak256'])
        self.assertFalse(first['metadata_excluded_from_identity'])

    def test_synthetic_exact_json_match_not_source_certificate(self):
        raw = b'{"compiler":{"version":"0.8.26"}}\n'
        result = m.metadata_match(ipfs_runtime(raw), raw)
        self.assertTrue(result['exact_byte_commitment_matched'])
        self.assertFalse(result['source_compilation_verified'])
        for changed in (raw.rstrip(), raw.replace(b'26', b'27'), b' ' + raw):
            with self.assertRaisesRegex(ValueError, 'commitment mismatch'):
                m.metadata_match(ipfs_runtime(raw), changed)

    def test_matching_digest_still_requires_valid_json_object(self):
        for raw in (b'[]', b'{', b'{"a":1,"a":2}', b'{"a":NaN}', b'\xff', b'null'):
            with self.assertRaises((ValueError, UnicodeDecodeError)):
                m.metadata_match(ipfs_runtime(raw), raw)

    def test_proof_corruption_and_consistent_code_forgery(self):
        for field in ('header', 'runtime'):
            bundle = evidence()
            if field == 'header':
                bundle['header_rlp'] = bundle['header_rlp'][:-2] + '00'
            else:
                node = bundle['observation']['nodes'][0]
                node['code'] = '0x00' + node['code'][4:]
                node['code_hash'] = m.lens.digest(m.lens.code_bytes(node['code']))
                bundle['observation']['effective_code_hash'] = node['code_hash']
            with self.assertRaises(ValueError):
                m.inspect(bundle)

    def test_anchor_mismatch_and_observed_hash_equality(self):
        bundle = evidence()
        with self.assertRaises(ValueError):
            m.inspect(bundle, '0x' + '11' * 32)
        # Tests matching mechanics only; this value is not independently trusted.
        result = m.inspect(bundle, bundle['observation']['block']['hash'])
        self.assertEqual(result['proof']['anchor'], 'caller-supplied-block-hash')

    def test_metadata_address_pair_and_membership(self):
        for kwargs in ({'metadata_bytes': b'{}'}, {'metadata_address': m.lens.ZTO},
                       {'metadata_bytes': b'{}', 'metadata_address': m.lens.IMD},
                       {'metadata_bytes': b'{}', 'metadata_address': m.lens.ZTO}):
            with self.assertRaises(ValueError):
                m.inspect(evidence(), **kwargs)

    def test_synthetic_beacon_deduplication(self):
        # Proof verification is intentionally mocked for role bookkeeping only.
        bundle = evidence()
        node = copy.deepcopy(bundle['observation']['nodes'][0])
        node['beacon'] = {'address': node['address'], 'code': node['code']}
        bundle['observation']['nodes'] = [node, copy.deepcopy(node)]
        with patch.object(m.proof, 'verify', return_value=m.proof.verify(evidence())):
            result = m.inspect(bundle)
        self.assertEqual(len(result['runtimes']), 1)
        self.assertEqual(result['runtimes'][0]['roles'], ['candidate-path', 'beacon'])

    def test_runtime_bounds_and_hostile_bytes(self):
        for raw in (b'', bytes(m.lens.MAX_CODE + 1), bytearray(b'\x00')):
            with self.assertRaises(ValueError):
                m.scan(raw)
        self.assertLess(len(json.dumps(m.scan(bytes(m.lens.MAX_CODE)))), 2000)
        rng = random.Random(737)
        for _ in range(500):
            raw = bytes(rng.randrange(256) for _ in range(rng.randrange(1, 150)))
            result = m.scan(raw)
            self.assertEqual(result['full_runtime_keccak256'], m.lens.digest(raw))

    def test_workspace_file_boundaries_and_limits(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        path = SCRATCH / 'metadata.json'
        for raw in (b'', bytes(100001)):
            path.write_bytes(raw)
            with self.assertRaises(ValueError):
                m.read_bytes(path)
        path.write_bytes(b'{}')
        self.assertEqual(m.read_bytes(path), b'{}')
        with self.assertRaises(ValueError):
            m.read_bytes(Path.cwd().parent / 'outside.json')
        link = SCRATCH / 'outside-link.json'
        link.unlink(missing_ok=True)
        link.symlink_to(Path.cwd().parent / 'outside.json')
        with self.assertRaises(ValueError):
            m.read_bytes(link)

    def test_unixfs_published_cid_vector_and_raw_hash_refusal(self):
        # IPFS IPIP-0499's hello-world dag-pb-wrapped leaf vector, without newline.
        self.assertEqual(m.base58(m.ipfs_multihash(b'hello world')),
                         'Qmf412jQZiuVUtdgnB36FXFX7xg5V6KEbSJ4dpQuhkLyfD')
        raw = b'{}'
        direct_hash_runtime = m.scan(trailer(mapping([
            ('ipfs', string(b'\x12\x20' + hashlib.sha256(raw).digest())), ('solc', SOLC)])))
        with self.assertRaisesRegex(ValueError, 'commitment mismatch'):
            m.metadata_match(direct_hash_runtime, raw)

    def test_varint_and_single_chunk_boundaries(self):
        for value, expected in [(0, '00'), (127, '7f'), (128, '8001'), (16383, 'ff7f'),
                                (16384, '808001'), (100000, 'a08d06')]:
            self.assertEqual(m.varint(value).hex(), expected)
        for value in (-1, 2**64, True, '1'):
            with self.assertRaises(ValueError):
                m.varint(value)
        self.assertEqual(len(m.ipfs_multihash(bytes(100000))), 34)
        with self.assertRaises(ValueError):
            m.ipfs_multihash(bytes(100001))

    def test_synthetic_metadata_join_and_role_conflict(self):
        bundle = evidence()
        raw = b'{"compiler":{"version":"0.8.26"}}'
        code = trailer(mapping([('ipfs', string(m.ipfs_multihash(raw))), ('solc', SOLC)]))
        node = bundle['observation']['nodes'][0]
        node['code'] = '0x' + code.hex()
        # Deliberately mock proof check to test the new join only, not chain inclusion.
        with patch.object(m.proof, 'verify', return_value=m.proof.verify(evidence())):
            result = m.inspect(bundle, metadata_bytes=raw, metadata_address=m.lens.ZTO)
            self.assertTrue(result['metadata_match']['exact_byte_commitment_matched'])
            with self.assertRaises(ValueError):
                m.inspect(bundle, metadata_bytes=raw + b' ', metadata_address=m.lens.ZTO)
            node['beacon'] = {'address': node['address'], 'code': '0x00'}
            with self.assertRaisesRegex(ValueError, 'conflicting runtime'):
                m.inspect(bundle)

    def test_cli_success_and_failures_no_partial_json(self):
        tool = str(FOLDER / 'code_metadata.py')
        source = str(FOLDER.parent / 'code-delta/zto-later-proof.json')
        good = subprocess.run([sys.executable, '-B', tool, '--bundle', source], capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(json.loads(good.stdout)['schema'], 'code-metadata-result-v1')
        SCRATCH.mkdir(parents=True, exist_ok=True)
        malformed = SCRATCH / 'bad-bundle.json'
        malformed.write_text('{"schema":"one","schema":"two"}')
        for args in (['--bundle', str(malformed)], ['--bundle', source, '--metadata-address', m.lens.ZTO],
                     ['--bundle', source, '--anchor-hash', '0x' + '11' * 32]):
            bad = subprocess.run([sys.executable, '-B', tool, *args], capture_output=True, text=True)
            self.assertEqual(bad.returncode, 1)
            self.assertEqual(bad.stdout, '')
            self.assertIn('Code Metadata:', bad.stderr)


if __name__ == '__main__':
    unittest.main()
