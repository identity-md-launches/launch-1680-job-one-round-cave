"""Offline tests for the bounded ZTO/IMD planning handoff."""
import contextlib
import copy
import io
import json
import unittest
from unittest.mock import patch

import zto_handoff as h


class HandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.observation = h.review.read_json(h.review.DEFAULT_SNAPSHOT)
        cls.report = h.review.read_json(h.review.DEFAULT_REPORT)
        cls.policy = h.review.read_json(h.review.HERE / 'demo-policy.json')

    def test_real_evidence_makes_one_complete_zto_handoff(self):
        result = h.handoff(self.observation, self.report, self.policy, '100000000')
        self.assertEqual(result['status'], 'ready_for_human_review')
        self.assertEqual(result['requested_input_raw'], str(10**26))
        self.assertEqual(result['minimum_output_raw'], '1184169088029408336486')
        self.assertEqual(result['settlement'], 'unspecified')
        self.assertIsNone(result['transaction'])
        self.assertEqual(result['handoff_sha256'], h.review.digest(
            {key: value for key, value in result.items() if key != 'handoff_sha256'}))
        self.assertEqual(h.verify_handoff(result)['status'], 'accepted')

    def test_verifier_refuses_tampering_and_settlement_fields(self):
        result = h.handoff(self.observation, self.report, self.policy, '100000000')
        changed = copy.deepcopy(result)
        changed['minimum_output_raw'] = '1'
        with self.assertRaisesRegex(ValueError, 'display disagrees'):
            h.verify_handoff(changed)
        changed = copy.deepcopy(result)
        changed['transaction'] = {'to': 'anything'}
        with self.assertRaisesRegex(ValueError, 'settlement'):
            h.verify_handoff(changed)
        changed = copy.deepcopy(result)
        changed['handoff_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            h.verify_handoff(changed)

    def test_unreviewed_or_partial_amount_refused(self):
        for amount in ('1000000000', '2'):
            with self.assertRaises(ValueError):
                h.handoff(self.observation, self.report, self.policy, amount)

    def test_review_mismatch_is_not_handed_off(self):
        changed = copy.deepcopy(self.report)
        changed['candidates'][1]['minimum_output_raw'] = '1'
        with self.assertRaisesRegex(ValueError, 'review did not accept'):
            h.handoff(self.observation, changed, self.policy, '100000000')

    def test_cli_is_offline_and_uses_exact_decimal(self):
        with patch.object(h.review.sizes.path.z, 'RPC', side_effect=AssertionError('network forbidden')):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(h.main(['--demo', '--amount', '100000000']), 0)
        self.assertEqual(json.loads(output.getvalue())['input_token'], 'ZTO')
        with contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(h.main(['--demo', '--amount', '3']), 1)
        self.assertIn('error', json.loads(error.getvalue()))

    def test_verify_cli_uses_workspace_json_reader(self):
        result = h.handoff(self.observation, self.report, self.policy, '100000000', 'historical_demo')
        with patch.object(h.review, 'read_json', return_value=result) as read_json:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(h.main(['--verify', 'line-1/tools/zto-handoff/example.json']), 0)
        self.assertEqual(read_json.call_count, 1)
        self.assertEqual(json.loads(output.getvalue())['status'], 'accepted')

    def test_evidence_verifier_rebuilds_the_handoff(self):
        result = h.handoff(self.observation, self.report, self.policy, '100000000', 'historical_demo')
        accepted = h.verify_evidence(result, self.observation, self.report, self.policy)
        self.assertEqual(accepted['status'], 'accepted')
        changed = copy.deepcopy(result)
        changed['limitations'][0] = 'A different claim.'
        changed['handoff_sha256'] = h.review.digest(
            {key: value for key, value in changed.items() if key != 'handoff_sha256'})
        with self.assertRaisesRegex(ValueError, 'exactly match'):
            h.verify_evidence(changed, self.observation, self.report, self.policy)

    def test_evidence_cli_is_offline_and_requires_complete_inputs(self):
        with patch.object(h.review.sizes.path.z, 'RPC', side_effect=AssertionError('network forbidden')):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(h.main(['--demo', '--verify-evidence',
                                         str(h.HERE / 'demo-handoff.json')]), 0)
        self.assertEqual(json.loads(output.getvalue())['status'], 'accepted')
        with contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(h.main(['--verify-evidence', str(h.HERE / 'demo-handoff.json')]), 1)
        self.assertIn('error', json.loads(error.getvalue()))

    def test_cli_can_save_only_a_newly_reviewed_handoff(self):
        with patch.object(h.review.sizes.path, 'save_json') as save_json:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(h.main(['--demo', '--amount', '100000000',
                                         '--save', 'test/scratch/handoff.json']), 0)
        saved_path, saved_value = save_json.call_args.args
        self.assertEqual(saved_path, 'test/scratch/handoff.json')
        self.assertEqual(saved_value['status'], 'ready_for_human_review')
        self.assertEqual(json.loads(output.getvalue())['handoff_sha256'],
                         saved_value['handoff_sha256'])

    def test_cli_refuses_save_on_a_verification_result(self):
        with contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(h.main(['--verify', str(h.HERE / 'demo-handoff.json'),
                                     '--save', 'test/scratch/verification.json']), 1)
        self.assertIn('--save is available only', json.loads(error.getvalue())['error'])


if __name__ == '__main__':
    unittest.main()
