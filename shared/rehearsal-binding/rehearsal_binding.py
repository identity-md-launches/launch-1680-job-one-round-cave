#!/usr/bin/env python3
"""Bind a proposed Ethereum call to an exact historical rehearsal. Offline only."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'binding_rehearse_core', HERE / 'call-rehearsal' / 'rehearse.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

SCHEMA = 'rehearsal-binding-v1'
LIMIT = 95_000
PLAN_KEYS = {'schema', 'chain_id', 'call', 'block', 'expected_return'}
OBS_KEYS = {'schema', 'source', 'chain_id', 'call', 'block', 'returns',
            'code_present', 'outcome'}
BLOCK_KEYS = {'number', 'hash', 'timestamp'}
LIMITS = (
    'Bound means only that this explicit call and expected bytes match saved provider '
    'evidence at the exact reviewed historical block. It is not approval to transact. '
    'The sender may be a contract: this does not prove that anyone can originate the call. '
    'No nonce, gas, fees, access list, wallet wrapping, signatures, state effects, ABI '
    'meaning, balances, current state or future success are checked. Even a returned '
    'ABI false may be bound if those exact bytes were expected. Digests identify input '
    'content; they do not authenticate a provider or the chain. Nothing is sent.'
)


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        core.require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('non-finite JSON number: ' + value)


def parse_json(raw):
    core.require(len(raw) <= LIMIT, 'input exceeds 95 KB')
    return json.loads(raw, object_pairs_hook=no_duplicates, parse_constant=reject_constant)


def read_json(path):
    with core.workspace_path(path).open('rb') as handle:
        return parse_json(handle.read(LIMIT + 1))


def exact_block(value):
    core.require(isinstance(value, dict) and set(value) == BLOCK_KEYS,
                 'block must contain exactly number, hash and timestamp')
    return core.header(value)


def plan(value):
    core.require(isinstance(value, dict) and set(value) == PLAN_KEYS,
                 'plan must have exactly the documented fields')
    core.require(value['schema'] == SCHEMA, 'unsupported plan schema')
    core.require(type(value['chain_id']) is int and value['chain_id'] == 1,
                 'plan requires Ethereum mainnet chain_id 1')
    core.require(isinstance(value['call'], dict) and
                 set(value['call']) == {'from', 'to', 'data', 'value'},
                 'plan requires explicit from, to, data and value only')
    return {'schema': SCHEMA, 'chain_id': 1,
            'call': core.transaction(value['call']), 'block': exact_block(value['block']),
            'expected_return': core.data(value['expected_return'])}


def observation(value):
    core.require(isinstance(value, dict) and
                 set(value) in (OBS_KEYS, OBS_KEYS | {'transport'}),
                 'observation must have exactly the call-rehearsal-v1 fields')
    core.require(len(json.dumps(value, allow_nan=False).encode()) <= LIMIT,
                 'observation exceeds 95 KB')
    exact_block(value['block'])
    outcome = value['outcome']
    if isinstance(outcome, dict) and 'error' in outcome:
        error = core.RPCError(outcome['error']).error
        core.require(set(error) <= {'code', 'message', 'data'}, 'unknown RPC error fields')
    return core.report(value)


def digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False).encode('ascii')
    return hashlib.sha256(encoded).hexdigest()


def bind(evidence, proposed):
    """Require exact context and successful raw return; do not release a transaction."""
    wanted = plan(proposed)
    checked = observation(evidence)
    actual_block = exact_block(evidence['block'])
    differences = []
    for section, actual in (('call', checked['call']), ('block', actual_block)):
        for field, expected in wanted[section].items():
            if field in actual and actual[field] != expected:
                differences.append({'field': section + '.' + field,
                                    'expected': expected, 'observed': actual[field]})
    report = {'schema': SCHEMA, 'verdict': 'inconclusive', 'reason': '',
              'plan': wanted, 'source': evidence['source'],
              'observed_call': checked['call'], 'observed_block': actual_block,
              'result': checked['result'], 'differences': differences,
              'plan_sha256': digest(wanted), 'evidence_sha256': digest(evidence),
              'limits': LIMITS}
    if 'transport' in checked:
        report['transport'] = checked['transport']
        report['limits'] += (' Contributor relay source is attribution only; '
                             'upstream identity and independence are unverified.')

    def finish(verdict, reason):
        report.update(verdict=verdict, reason=reason)
        return report

    if differences:
        return finish('mismatch', 'proposed call or reviewed block differs from the rehearsal')
    if 'from' not in checked['call']:
        return finish('inconclusive', 'rehearsal omitted the sender; cannot bind an explicit caller')
    result = checked['result']
    if result['status'] == 'reverted':
        return finish('mismatch', 'provider reported a revert; expected a return')
    if result['status'] not in ('returned', 'returned_true', 'returned_false'):
        return finish('inconclusive', 'RPC failure or malformed selected return interpretation')
    if result['raw'] != wanted['expected_return']:
        differences.append({'field': 'expected_return', 'expected': wanted['expected_return'],
                            'observed': result['raw']})
        return finish('mismatch', 'returned bytes differ from the reviewed expectation')
    return finish('bound', 'explicit call, exact block and expected return bytes all match')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('demo', help='bind a real historical ZTO balance query offline')
    check = commands.add_parser('check', help='check saved evidence against a reviewed call plan')
    check.add_argument('evidence')
    check.add_argument('plan')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            evidence = read_json(HERE / 'zto-observation.json')
            proposed = read_json(HERE / 'zto-plan.json')
        else:
            proposed = read_json(args.plan)
            plan(proposed)
            evidence = read_json(args.evidence)
        result = bind(evidence, proposed)
        print(json.dumps(result, indent=2, allow_nan=False))
        return {'bound': 0, 'mismatch': 1, 'inconclusive': 2}[result['verdict']]
    except (ValueError, KeyError, TypeError, OSError, RecursionError) as exc:
        print(json.dumps({'schema': SCHEMA, 'verdict': 'inconclusive', 'error': str(exc)}),
              file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
