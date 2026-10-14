"""Exercise receipt bounds and input refusals; mutations are test-only scenarios."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

import receipt_exposure as tool


class ExposureTests(unittest.TestCase):
    def setUp(self):
        self.inventory = tool.gate.load(tool.DEFAULT)
        self.empty = next(o for o in self.inventory['observations']
                          if int(o['raw']['allowances'][0]['result'], 16) > 0
                          and int(o['raw']['balances'][0]['result'], 16) == 0)
        self.owner = self.empty['query']['owner']

    def scenario(self, amount, owner=None, token=None):
        return {'schema': tool.RECEIPTS_SCHEMA, 'chain_id': 1,
                'token_address': token or self.empty['token_address'],
                'receipts': [{'owner': owner or self.owner, 'amount_raw': str(amount)}]}

    def row(self, result):
        return next(r for r in result['owners'] if r['owner'] == self.owner)

    def test_historical_real_evidence(self):
        report = tool.assess(self.inventory)
        self.assertEqual(report['measured_pair_count'], 19)
        self.assertEqual(sum(r['active_permission_count'] for r in report['owners']), 3)
        self.assertEqual(sum(r['active_on_empty_balance'] for r in report['owners']), 2)
        self.assertEqual(report['block']['block_number'], 26187572)
        self.assertEqual(report['mode'], 'historical_capacity_only')
        self.assertTrue(all(r['incremental_combined_exposure_raw'] == '0' for r in report['owners']))

    def test_empty_balance_receipt_is_exposed(self):
        row = self.row(tool.assess(self.inventory, self.scenario(10**18)))
        self.assertEqual(row['incremental_combined_exposure_raw'], str(10**18))
        self.assertTrue(row['active_on_empty_balance'])
        self.assertEqual(row['maximum_additional_exposure_before_receipt_raw'], str(tool.gate.lens.MAX_UINT))

    def test_zero_permission(self):
        inactive = next(o for o in self.inventory['observations']
                        if all(int(a['result'], 16) == 0 for a in o['raw']['allowances']))
        owner = inactive['query']['owner']
        result = tool.assess(self.inventory, self.scenario(123, owner))
        row = next(r for r in result['owners'] if r['owner'] == owner)
        self.assertEqual(row['incremental_combined_exposure_raw'], '0')
        self.assertEqual(row['receipt_outside_measured_combined_bound_raw'], '123')

    def test_overlap_capped_at_balance(self):
        observed = copy.deepcopy(next(o for o in self.inventory['observations']
                                     if len(o['raw']['allowances']) >= 2))
        owner = observed['query']['owner']
        observed['raw']['balances'][0]['result'] = '0x' + format(4, '064x')
        for a in observed['raw']['allowances']:
            a['result'] = '0x' + format(6, '064x')
        report = tool.assess(observed, self.scenario(6, owner))
        row = report['owners'][0]
        self.assertEqual(row['before_combined_spendable_upper_bound_raw'], '4')
        self.assertEqual(row['after_combined_spendable_upper_bound_raw'], '10')
        self.assertEqual(row['incremental_combined_exposure_raw'], '6')
        self.assertEqual(sum(int(p['after_spendable_upper_bound_raw']) for p in row['pairs']),
                         6 * len(observed['raw']['allowances']))

    def test_finite_allowance_saturates(self):
        observed = copy.deepcopy(self.empty)
        observed['raw']['allowances'][0]['result'] = '0x' + format(12, '064x')
        observed['raw']['balances'][0]['result'] = '0x' + format(5, '064x')
        row = tool.assess(observed, self.scenario(20))['owners'][0]
        self.assertEqual(row['incremental_combined_exposure_raw'], '7')
        self.assertEqual(row['receipt_outside_measured_combined_bound_raw'], '13')
        self.assertEqual(row['maximum_additional_exposure_before_receipt_raw'], '7')

    def test_uint256_boundaries(self):
        maximum = tool.gate.lens.MAX_UINT
        self.assertEqual(self.row(tool.assess(self.inventory, self.scenario(maximum)))
                         ['hypothetical_balance_raw'], str(maximum))
        observed = copy.deepcopy(self.empty)
        observed['raw']['balances'][0]['result'] = '0x' + format(1, '064x')
        with self.assertRaisesRegex(ValueError, 'balance exceeds'):
            tool.assess(observed, self.scenario(maximum))
        for amount in [-1, maximum + 1]:
            with self.assertRaises(ValueError):
                tool.assess(self.inventory, self.scenario(amount))

    def test_canonical_receipt_amounts(self):
        for amount in [True, 1, '01', '1.0', '1e18', '', ' 1']:
            scenario = self.scenario(1)
            scenario['receipts'][0]['amount_raw'] = amount
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                tool.assess(self.inventory, scenario)

    def test_unknown_owner_not_zero_evidence(self):
        # A real measured spender is not a measured owner in this inventory.
        unknown = self.empty['query']['spenders'][0]
        with self.assertRaisesRegex(ValueError, 'no measured'):
            tool.assess(self.inventory, self.scenario(1, unknown))

    def test_token_and_chain_mismatch(self):
        with self.assertRaisesRegex(ValueError, 'token differs'):
            tool.assess(self.inventory, self.scenario(1, token=tool.gate.lens.TOKENS['IMD']))
        scenario = self.scenario(1)
        scenario['chain_id'] = True
        with self.assertRaises(ValueError):
            tool.assess(self.inventory, scenario)

    def test_duplicate_and_extra_fields(self):
        scenario = self.scenario(1)
        scenario['receipts'].append(copy.deepcopy(scenario['receipts'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            tool.assess(self.inventory, scenario)
        scenario = self.scenario(1)
        scenario['receipts'][0]['send'] = True
        with self.assertRaises(ValueError):
            tool.assess(self.inventory, scenario)

    def test_missing_raw_evidence(self):
        observed = copy.deepcopy(self.empty)
        observed['raw']['allowances'] = []
        with self.assertRaisesRegex(ValueError, 'missing or extra'):
            tool.assess(observed, self.scenario(1))

    def test_order_deterministic_and_inputs_unchanged(self):
        original = copy.deepcopy(self.inventory)
        reverse = copy.deepcopy(original)
        reverse['observations'].reverse()
        a = tool.assess(original, self.scenario(3))
        b = tool.assess(reverse, self.scenario(3))
        self.assertEqual(a['owners'], b['owners'])
        self.assertNotEqual(a['input_sha256']['observation'], b['input_sha256']['observation'])
        self.assertEqual(original, self.inventory)
        self.assertNotEqual(a['input_sha256']['receipts'],
                            tool.assess(original, self.scenario(4))['input_sha256']['receipts'])

    def test_cli_and_workspace_input_guard(self):
        result = subprocess.run([sys.executable, '-B', str(Path(tool.__file__))],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['measured_pair_count'], 19)
        refused = subprocess.run([sys.executable, '-B', str(Path(tool.__file__)),
                                  '--receipts', '../outside.json'],
                                 capture_output=True, text=True, check=False)
        self.assertEqual(refused.returncode, 1)
        self.assertIn('inside the current workspace', refused.stderr)


if __name__ == '__main__':
    unittest.main()
