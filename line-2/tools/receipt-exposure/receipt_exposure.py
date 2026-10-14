#!/usr/bin/env python3
"""Estimate how explicit hypothetical receipts expose tokens to measured allowances."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'permission-gate'))
import permission_gate as gate

DEFAULT = HERE.parent / 'bundle-refresh' / 'live-after.json'
RECEIPTS_SCHEMA = 'permission-hypothetical-receipts-v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def parse_receipts(value):
    gate.exact_keys(value, ('schema', 'chain_id', 'token_address', 'receipts'), 'receipts')
    gate.lens.require(value['schema'] == RECEIPTS_SCHEMA, 'unsupported receipts schema')
    gate.lens.require(type(value['chain_id']) is int and value['chain_id'] == 1,
                      'receipts must select Ethereum chain 1')
    token = gate.lens.address(value['token_address'])
    gate.lens.require(token in gate.lens.TOKENS.values(), 'receipts require real ZTO or IMD')
    entries = value['receipts']
    gate.lens.require(isinstance(entries, list) and len(entries) <= gate.lens.MAX_PAIRS,
                      'receipts must list at most 64 owners')
    result = {}
    for entry in entries:
        gate.exact_keys(entry, ('owner', 'amount_raw'), 'receipt')
        owner = gate.lens.address(entry['owner'])
        gate.lens.require(owner not in result, 'duplicate receipt owner')
        result[owner] = gate.raw_uint(entry['amount_raw'])
    return token, result


def assess(observation, receipts=None):
    measured = gate.changes.flatten(observation)
    gate.lens.require(bool(measured['pairs']), 'empty evidence cannot assess receipt exposure')
    if receipts is None:
        amounts = {}
    else:
        token, amounts = parse_receipts(receipts)
        gate.lens.require(token == measured['token_address'], 'receipt token differs from observation')
    owners = sorted({owner for owner, _ in measured['pairs']})
    gate.lens.require(set(amounts) <= set(owners), 'receipt owner has no measured permission evidence')
    results = []
    for owner in owners:
        entries = [row for pair, row in sorted(measured['pairs'].items()) if pair[0] == owner]
        balance = int(entries[0]['balance_raw'])
        receipt = amounts.get(owner, 0)
        gate.lens.require(balance + receipt <= gate.lens.MAX_UINT,
                          'hypothetical balance exceeds uint256')
        after = balance + receipt
        allowance_sum = sum(int(row['allowance_raw']) for row in entries)
        before_cap, after_cap = min(balance, allowance_sum), min(after, allowance_sum)
        pairs = []
        for row in entries:
            allowance = int(row['allowance_raw'])
            before, future = min(balance, allowance), min(after, allowance)
            pairs.append({'spender': row['spender'], 'allowance_raw': str(allowance),
                          'permission_active': allowance > 0,
                          'before_spendable_upper_bound_raw': str(before),
                          'after_spendable_upper_bound_raw': str(future),
                          'incremental_exposure_raw': str(future - before)})
        results.append({
            'owner': owner, 'measured_pair_count': len(entries),
            'active_permission_count': sum(int(row['allowance_raw']) > 0 for row in entries),
            'active_on_empty_balance': balance == 0 and allowance_sum > 0,
            'balance_raw': str(balance), 'receipt_explicitly_supplied': owner in amounts,
            'hypothetical_receipt_raw': str(receipt), 'hypothetical_balance_raw': str(after),
            'before_combined_spendable_upper_bound_raw': str(before_cap),
            'after_combined_spendable_upper_bound_raw': str(after_cap),
            'incremental_combined_exposure_raw': str(after_cap - before_cap),
            'receipt_outside_measured_combined_bound_raw': str(receipt - (after_cap - before_cap)),
            'maximum_additional_exposure_before_receipt_raw': str(
                min(gate.lens.MAX_UINT, allowance_sum) - before_cap),
            'pairs': pairs,
        })
    return {
        'schema': 'permission-receipt-exposure-v1',
        'mode': 'historical_capacity_only' if receipts is None else 'hypothetical_receipts',
        'chain_id': measured['chain_id'], 'token': measured['token'],
        'token_address': measured['token_address'], 'decimals': measured['decimals'],
        'block': gate.changes.block_summary(measured),
        'input_sha256': {'observation': digest(observation),
                         'receipts': None if receipts is None else digest(receipts)},
        'measured_pair_count': len(measured['pairs']), 'complete_wallet_audit': False,
        'owners': results,
        'limitations': [
            'Historical trusted RPC evidence only; no current-chain or future-state assertion.',
            'Receipt amounts are explicit hypothetical net balance increases, not transfers or predictions.',
            'Unspecified measured owners receive zero in the scenario; unknown owners are refused.',
            'Allowances are held fixed; owner bounds cap overlapping spender allowances at balance.',
            'Per-spender incremental bounds overlap and must not be added as an owner total.',
            'Amounts outside measured bounds are not certified safe from unknown permissions.',
            'Standard ERC-20 assumptions; no Permit2, signatures, custom authorization or other-token coverage.',
            'No transaction is built, simulated, signed or sent; no wallet, key or environment access.',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observation', help='workspace raw Allowance Lens or Changes inventory JSON')
    parser.add_argument('--receipts', help='workspace explicit hypothetical receipt scenario JSON')
    args = parser.parse_args(argv)
    try:
        result = assess(gate.load(args.observation or DEFAULT),
                        None if args.receipts is None else gate.load(args.receipts))
        result['demonstration'] = args.observation is None
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
