import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rehearsal_binding as binding


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.evidence = binding.read_json(HERE / 'zto-observation.json')
        self.plan = binding.read_json(HERE / 'zto-plan.json')

    def test_real_zto_balance_binds_without_network(self):
        with patch.object(binding.core.RPC, 'call', side_effect=AssertionError('network')):
            result = binding.bind(self.evidence, self.plan)
        self.assertEqual(result['verdict'], 'bound')
        self.assertEqual(result['result']['uint256'], '285939607966355541747129965')
        self.assertEqual(result['differences'], [])

    def test_each_call_mutation_is_a_mismatch(self):
        mutations = {
            'to': '0xd34a99bc0f67ae1bbd63c660e6d0b0dd03e263b7',
            'from': '0xd34a99bc0f67ae1bbd63c660e6d0b0dd03e263b7',
            'data': self.plan['call']['data'][:-2] + '91',
            'value': '0x1',
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                proposed = copy.deepcopy(self.plan)
                proposed['call'][field] = value
                result = binding.bind(self.evidence, proposed)
                self.assertEqual(result['verdict'], 'mismatch')
                self.assertEqual(result['differences'][0]['field'], 'call.' + field)

    def test_each_block_mutation_is_a_mismatch(self):
        for field, value in {'number': '0x18f9519', 'timestamp': '0x6acec6d8',
                             'hash': '0x' + 'ab' * 32}.items():
            with self.subTest(field=field):
                proposed = copy.deepcopy(self.plan)
                proposed['block'][field] = value
                result = binding.bind(self.evidence, proposed)
                self.assertEqual(result['verdict'], 'mismatch')
                self.assertEqual(result['differences'][0]['field'], 'block.' + field)

    def test_changed_expected_return_is_a_mismatch(self):
        self.plan['expected_return'] = '0x'
        result = binding.bind(self.evidence, self.plan)
        self.assertEqual(result['verdict'], 'mismatch')
        self.assertEqual(result['differences'][0]['field'], 'expected_return')

    def test_missing_sender_is_not_defaulted(self):
        evidence = binding.read_json(HERE.parent / 'call-rehearsal' / 'zto-observation.json')
        proposed = dict(self.plan, call=dict(evidence['call'],
                        **{'from': self.plan['call']['from']}), block=evidence['block'],
                        expected_return=evidence['outcome']['result'])
        result = binding.bind(evidence, proposed)
        self.assertEqual(result['verdict'], 'inconclusive')
        self.assertIn('omitted the sender', result['reason'])

    def test_revert_refuses_even_with_expected_empty_bytes(self):
        self.evidence['outcome'] = {'error': {'code': 3, 'message': 'execution reverted', 'data': '0x'}}
        self.plan['expected_return'] = '0x'
        self.assertEqual(binding.bind(self.evidence, self.plan)['verdict'], 'mismatch')

    def test_rpc_failure_is_inconclusive(self):
        self.evidence['outcome'] = {'error': {'code': -32000, 'message': 'provider unavailable'}}
        self.assertEqual(binding.bind(self.evidence, self.plan)['verdict'], 'inconclusive')

    def test_malformed_interpretation_is_inconclusive(self):
        self.evidence['outcome'] = {'result': '0x01'}
        self.plan['expected_return'] = '0x01'
        self.assertEqual(binding.bind(self.evidence, self.plan)['verdict'], 'inconclusive')

    def test_raw_empty_success_can_bind_but_revert_cannot(self):
        self.evidence['returns'] = 'raw'
        self.evidence['outcome'] = {'result': '0x'}
        self.plan['expected_return'] = '0x'
        self.assertEqual(binding.bind(self.evidence, self.plan)['verdict'], 'bound')

    def test_bool_false_is_only_a_byte_match(self):
        raw = '0x' + '00' * 32
        self.evidence['returns'] = 'bool'
        self.evidence['outcome'] = {'result': raw}
        self.plan['expected_return'] = raw
        result = binding.bind(self.evidence, self.plan)
        self.assertEqual(result['verdict'], 'bound')
        self.assertFalse(result['result']['boolean'])
        self.assertIn('ABI false', result['limits'])

    def test_case_normalization_and_stable_plan_digest(self):
        first = binding.bind(self.evidence, self.plan)
        proposed = copy.deepcopy(self.plan)
        for field in ('from', 'to', 'data'):
            proposed['call'][field] = '0x' + proposed['call'][field][2:].upper()
        proposed['block']['hash'] = '0x' + proposed['block']['hash'][2:].upper()
        proposed['expected_return'] = '0x' + proposed['expected_return'][2:].upper()
        second = binding.bind(self.evidence, proposed)
        self.assertEqual(second['verdict'], 'bound')
        self.assertEqual(first['plan_sha256'], second['plan_sha256'])

    def test_digest_binds_evidence_and_plan_without_mutation(self):
        saved = copy.deepcopy((self.evidence, self.plan))
        first = binding.bind(self.evidence, self.plan)
        self.assertEqual((self.evidence, self.plan), saved)
        self.plan['call']['value'] = '0x1'
        second = binding.bind(self.evidence, self.plan)
        self.assertNotEqual(first['plan_sha256'], second['plan_sha256'])
        self.assertEqual(first['evidence_sha256'], second['evidence_sha256'])

    def test_relay_provenance_retained_and_forged_flags_refused(self):
        flags = {'kind': 'contributor-relay', 'source_is_attribution_only': True,
                 'independent_provider_verified': False}
        self.evidence['transport'] = flags
        result = binding.bind(self.evidence, self.plan)
        self.assertEqual(result['verdict'], 'bound')
        self.assertEqual(result['transport'], flags)
        self.assertIn('attribution only', result['limits'])
        self.evidence['transport']['independent_provider_verified'] = True
        with self.assertRaises(ValueError):
            binding.bind(self.evidence, self.plan)

    def test_plan_refuses_partial_or_extra_fields(self):
        for change in ('no_sender', 'no_value', 'gas', 'chain_bool', 'chain_other', 'block_extra'):
            with self.subTest(change=change):
                proposed = copy.deepcopy(self.plan)
                if change == 'no_sender':
                    del proposed['call']['from']
                elif change == 'no_value':
                    del proposed['call']['value']
                elif change == 'gas':
                    proposed['call']['gas'] = '0x5208'
                elif change == 'chain_bool':
                    proposed['chain_id'] = True
                elif change == 'chain_other':
                    proposed['chain_id'] = 11155111
                else:
                    proposed['block']['finalized'] = True
                with self.assertRaises(ValueError):
                    binding.bind(self.evidence, proposed)

    def test_observation_refuses_unknown_fields_and_boolean_chain(self):
        for extra in ({'secret': 'never read'}, {'chain_id': True}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                binding.bind(dict(self.evidence, **extra), self.plan)

    def test_json_refuses_duplicate_nonfinite_and_large_inputs(self):
        for raw in (b'{"chain_id":1,"chain_id":1}', b'{"x":NaN}', b' ' * (binding.LIMIT + 1)):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                binding.parse_json(raw)

    def test_input_paths_cannot_escape_workspace(self):
        with self.assertRaisesRegex(ValueError, 'within the workspace'):
            binding.read_json(Path.cwd().parent / 'outside.json')

    def test_demo_exit_and_output(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = binding.main(['demo'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stream.getvalue())['verdict'], 'bound')

    def test_cli_mismatch_and_inconclusive_exits(self):
        for mode, expected in (('mismatch', 1), ('inconclusive', 2)):
            evidence, proposed = copy.deepcopy(self.evidence), copy.deepcopy(self.plan)
            if mode == 'mismatch':
                proposed['call']['value'] = '0x1'
            else:
                evidence['outcome'] = {'error': {'code': -32000, 'message': 'unavailable'}}
            with patch.object(binding, 'read_json', side_effect=[proposed, evidence]), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(binding.main(['check', 'evidence', 'plan']), expected)

    def test_cli_invalid_input_is_structured(self):
        stream = io.StringIO()
        with patch.object(binding, 'read_json', side_effect=ValueError('duplicate JSON key')), \
                contextlib.redirect_stderr(stream):
            self.assertEqual(binding.main(['check', 'evidence', 'plan']), 2)
        self.assertEqual(json.loads(stream.getvalue())['verdict'], 'inconclusive')


if __name__ == '__main__':
    unittest.main()
