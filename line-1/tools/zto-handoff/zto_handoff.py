#!/usr/bin/env python3
"""Make one explicit, non-sending ZTO/IMD bound handoff after review."""
import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'zto-review'))
import zto_review as review

HERE = Path(__file__).resolve().parent
SCHEMA = 'zto-bound-handoff-v1'
HANDOFF_KEYS = {
    'schema', 'status', 'chain_id', 'pool_id', 'block', 'source_digests',
    'input_token', 'output_token', 'requested_input_raw', 'requested_input',
    'minimum_output_raw', 'minimum_output', 'slippage_bps',
    'review_reference_block', 'review_age_blocks', 'settlement', 'transaction',
    'limitations', 'mode', 'handoff_sha256',
}


def handoff(observation, report, policy, amount, mode='library'):
    """Re-review evidence and select precisely one complete candidate amount.

    This deliberately contains no recipient, router, calldata, gas, signature,
    or transaction fields.  It is a finite planning handoff, not an order.
    """
    result = review.review(observation, report, policy)
    review.sizes.path.z.require(result['status'] == 'accepted',
                                'review did not accept a usable bound')
    review.sizes.path.z.require(isinstance(amount, str) and len(amount) <= 100,
                                'amount must be a short decimal string')
    state, _, _ = review.sizes.path.decode(observation)
    input_token = policy['input_token']
    output_token = 'IMD' if input_token == 'ZTO' else 'ZTO'
    input_decimals = state['decimals'][1 if input_token == 'ZTO' else 0]
    output_decimals = state['decimals'][0 if input_token == 'ZTO' else 1]
    raw = str(review.sizes.path.z.parse_amount(amount, input_decimals))
    matches = [row for row in result['usable_bounds']
               if row['requested_input_raw'] == raw]
    review.sizes.path.z.require(len(matches) == 1,
                                'amount is not exactly one reviewed usable bound')
    chosen = matches[0]
    output = {
        'schema': SCHEMA,
        'status': 'ready_for_human_review',
        'chain_id': result['chain_id'],
        'pool_id': result['pool_id'],
        'block': result['block'],
        'source_digests': {
            'snapshot_sha256': result['snapshot_sha256'],
            'policy_sha256': result['policy_sha256'],
            'report_sha256': result['report_sha256'],
        },
        'input_token': input_token,
        'output_token': output_token,
        'requested_input_raw': chosen['requested_input_raw'],
        'requested_input': review.sizes.path.z.units(
            int(chosen['requested_input_raw']), input_decimals),
        'minimum_output_raw': chosen['minimum_output_raw'],
        'minimum_output': review.sizes.path.z.units(
            int(chosen['minimum_output_raw']), output_decimals),
        'slippage_bps': policy['slippage_bps'],
        'review_reference_block': result['reference_block'],
        'review_age_blocks': result['age_blocks'],
        'settlement': 'unspecified',
        'transaction': None,
        'limitations': [
            'No recipient, router, calldata, gas setting, signature, or transaction is prepared.',
            'The minimum is a reviewed planning bound, not an enforced or guaranteed receipt.',
            'Historical evidence is not a current quote, execution simulation, or settlement proof.',
        ],
        'mode': mode,
    }
    output['handoff_sha256'] = review.digest(output)
    return output


def verify_handoff(value):
    """Validate a self-contained handoff without treating it as settlement data.

    This catches changed fields after a handoff has crossed a file, chat, or
    worker boundary. It validates structural and arithmetic consistency only;
    the original snapshot, report, and policy establish its provenance.
    """
    require = review.sizes.path.z.require
    require(type(value) is dict and set(value) == HANDOFF_KEYS,
            'handoff must contain exactly the documented fields')
    require(value['schema'] == SCHEMA, 'wrong handoff schema')
    require(value['status'] == 'ready_for_human_review', 'handoff is not ready for review')
    require(value['chain_id'] == 1 and value['pool_id'] == review.sizes.path.z.POOL,
            'handoff is not for the assigned Ethereum ZTO/IMD pool')
    require(value['input_token'] in ('ZTO', 'IMD') and
            value['output_token'] in ('ZTO', 'IMD') and
            value['input_token'] != value['output_token'], 'invalid token direction')
    require(value['mode'] in ('historical_demo', 'caller_policy', 'library'), 'invalid mode')
    require(value['settlement'] == 'unspecified' and value['transaction'] is None,
            'handoff must not contain settlement or transaction data')
    require(type(value['block']) is dict and set(value['block']) == {'number', 'hash', 'timestamp'} and
            all(isinstance(value['block'][key], str) and re.fullmatch(r'0x[0-9a-f]+', value['block'][key])
                for key in value['block']), 'invalid pinned block')
    require(type(value['source_digests']) is dict and
            set(value['source_digests']) == {'snapshot_sha256', 'policy_sha256', 'report_sha256'} and
            all(isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest)
                for digest in value['source_digests'].values()), 'invalid source digests')
    require(type(value['slippage_bps']) is int and 0 <= value['slippage_bps'] < 10000 and
            all(type(value[key]) is int and value[key] >= 0
                for key in ('review_reference_block', 'review_age_blocks')), 'invalid review settings')
    require(type(value['limitations']) is list and len(value['limitations']) >= 1 and
            all(isinstance(item, str) and item for item in value['limitations']), 'invalid limitations')
    decimals = 18  # Both assigned ERC-20s are 18-decimal in the pinned pool evidence.
    requested = review.sizes.path.z.parse_amount(value['requested_input'], decimals)
    minimum = review.sizes.path.z.parse_amount(value['minimum_output'], decimals)
    require(value['requested_input_raw'] == str(requested) and requested > 0,
            'requested input display disagrees with raw units')
    require(value['minimum_output_raw'] == str(minimum) and minimum > 0,
            'minimum output display disagrees with raw units')
    require(isinstance(value['handoff_sha256'], str) and re.fullmatch(r'[0-9a-f]{64}', value['handoff_sha256']),
            'invalid handoff digest')
    unsigned = {key: item for key, item in value.items() if key != 'handoff_sha256'}
    require(value['handoff_sha256'] == review.digest(unsigned), 'handoff digest mismatch')
    return {'schema': 'zto-bound-handoff-verification-v1', 'status': 'accepted',
            'handoff_sha256': value['handoff_sha256'], 'pool_id': value['pool_id'],
            'input_token': value['input_token'], 'output_token': value['output_token'],
            'limitations': ['This checks the handoff file only; it does not independently re-review its evidence or prepare settlement.']}


def verify_evidence(value, observation, report, policy):
    """Rebuild a handoff from supplied evidence and require byte-for-byte meaning.

    Unlike :func:`verify_handoff`, this is useful when the receiver has the
    three source documents as well as the transferred handoff.  It reruns the
    review and derives the only acceptable handoff for the claimed amount.
    The comparison is type-sensitive and includes every limitation, so a file
    that merely has a valid self-digest cannot be substituted for these inputs.
    """
    require = review.sizes.path.z.require
    verify_handoff(value)
    result = review.review(observation, report, policy)
    require(result['status'] == 'accepted', 'evidence review did not accept a usable bound')
    expected_digests = {
        'snapshot_sha256': result['snapshot_sha256'],
        'policy_sha256': result['policy_sha256'],
        'report_sha256': result['report_sha256'],
    }
    require(value['source_digests'] == expected_digests,
            'handoff source digests do not match supplied evidence')
    expected = handoff(observation, report, policy, value['requested_input'], value['mode'])
    require(value == expected, 'handoff does not exactly match supplied reviewed evidence')
    return {'schema': 'zto-bound-handoff-evidence-verification-v1',
            'status': 'accepted', 'handoff_sha256': value['handoff_sha256'],
            'pool_id': value['pool_id'], 'input_token': value['input_token'],
            'output_token': value['output_token'], 'limitations': [
                'This rechecks supplied historical files; it is not a live quote, execution simulation, or settlement approval.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--demo', action='store_true',
                      help='offline handoff from bundled historical real-pool evidence')
    mode.add_argument('--policy', help='review policy JSON inside this workspace')
    mode.add_argument('--verify', help='verify a workspace handoff JSON without making a new handoff')
    parser.add_argument('--verify-evidence', metavar='HANDOFF',
                        help='re-review workspace evidence and compare it to a workspace handoff')
    parser.add_argument('--snapshot', help='ZTO Path snapshot JSON inside this workspace')
    parser.add_argument('--report', help='ZTO Sizes report JSON inside this workspace')
    parser.add_argument('--amount',
                        help='one exact decimal candidate amount from the reviewed policy')
    parser.add_argument('--save',
                        help='write a newly made handoff JSON inside this workspace')
    args = parser.parse_args(argv)
    try:
        if args.verify and args.verify_evidence:
            raise ValueError('--verify and --verify-evidence are alternatives')
        if args.verify or args.verify_evidence:
            if args.save:
                raise ValueError('--save is available only when making a handoff')
            if args.amount:
                raise ValueError('--verify cannot be combined with handoff inputs')
            handoff_file = args.verify or args.verify_evidence
            value = review.read_json(handoff_file)
            if args.verify:
                if args.snapshot or args.report or args.policy:
                    raise ValueError('--verify cannot be combined with evidence inputs')
                result = verify_handoff(value)
            else:
                if args.demo:
                    if args.snapshot or args.report or args.policy:
                        raise ValueError('--demo cannot be combined with custom evidence')
                    policy_file = review.HERE / 'demo-policy.json'
                    snapshot_file, report_file = review.DEFAULT_SNAPSHOT, review.DEFAULT_REPORT
                else:
                    if not args.policy or not args.snapshot or not args.report:
                        raise ValueError('--verify-evidence requires --demo or --policy, --snapshot, and --report')
                    policy_file, snapshot_file, report_file = args.policy, args.snapshot, args.report
                result = verify_evidence(value, review.read_json(snapshot_file),
                                         review.read_json(report_file), review.read_json(policy_file))
        elif args.demo:
            if not args.amount:
                raise ValueError('--amount is required when making a handoff')
            if args.snapshot or args.report:
                raise ValueError('--demo cannot be combined with custom files')
            policy_file = review.HERE / 'demo-policy.json'
            snapshot_file, report_file = review.DEFAULT_SNAPSHOT, review.DEFAULT_REPORT
            selected_mode = 'historical_demo'
        elif args.policy:
            if not args.amount:
                raise ValueError('--amount is required when making a handoff')
            if not args.snapshot or not args.report:
                raise ValueError('--policy requires --snapshot and --report')
            policy_file, snapshot_file, report_file = args.policy, args.snapshot, args.report
            selected_mode = 'caller_policy'
        else:
            raise ValueError('choose --demo, --policy, --verify, or --verify-evidence')
        if not args.verify and not args.verify_evidence:
            result = handoff(review.read_json(snapshot_file), review.read_json(report_file),
                             review.read_json(policy_file), args.amount, selected_mode)
            if args.save:
                # The inherited writer enforces the workspace boundary and a
                # 100 KB size limit.  This makes a reviewable artifact, never
                # a transaction or a request to an external service.
                review.sizes.path.save_json(args.save, result)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (ValueError, KeyError, TypeError, AttributeError, OSError, OverflowError,
            RecursionError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
