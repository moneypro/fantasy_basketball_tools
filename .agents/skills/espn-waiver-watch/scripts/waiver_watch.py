"""Bounded free-agent watch; never submits waiver claims or retries acquisitions."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / '.agents/skills/espn-add-drop/scripts'),
                str(ROOT / '.agents/skills/espn-roster-rollover/scripts')]
from add_drop import ESPN, DEFAULT_ENV, Refused, require, preflight, execute, verify, roster_summary, write_json
from rollover_pickup import finish


def validate_config(cfg):
    require(cfg.get('authorized') is True, 'Exact pair and window must be authorized')
    for k in ('season', 'league', 'team', 'addId', 'dropId', 'protectedPeriod', 'targetPeriod'):
        require(type(cfg.get(k)) is int and cfg[k] > 0, 'Missing positive identity or period')
    require(cfg['addId'] != cfg['dropId'], 'Add and drop must differ')
    require(cfg['targetPeriod'] == cfg['protectedPeriod'] + 1, 'Protect the preceding day')
    start, end = [datetime.fromisoformat(cfg[k]) for k in ('start', 'end')]
    require(start.tzinfo is not None and end.tzinfo is not None, 'Timezone required')
    require(0 < (end - start).total_seconds() <= 7200, 'Window must be at most two hours')
    if 'teammateDecision' in cfg:
        rule = cfg['teammateDecision']
        require(cfg.get('priorityClaim') and all(type(rule.get(k)) is int and rule[k] > 0 for k in
                ('teammateId', 'teamId', 'eventId', 'alternateId')), 'Missing conditional fallback identity')
        require(len({cfg['addId'], cfg['dropId'], cfg['priorityClaim']['addId'], rule['alternateId'], rule['teammateId']}) == 5,
                'Overlapping conditional targets')
        resume, decide, stop = (datetime.fromisoformat(rule[k]) for k in ('resume', 'decide', 'stop'))
        require(end < resume <= decide < stop and (stop - resume).total_seconds() <= 7200
                and (stop - start).total_seconds() <= 86400, 'Invalid pre-lock follow-up window')
        if rule.get('observeFrom'):
            observe = datetime.fromisoformat(rule['observeFrom'])
            require(observe <= start and (stop - observe).total_seconds() <= 48*3600,
                    'Invalid continuous teammate watch')
    return start, end


def teammate_report(rule):
    with urlopen(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={rule['eventId']}", timeout=8) as response:
        game = json.load(response)
    require(str(game['header']['id']) == str(rule['eventId']), 'Wrong game in injury check')
    teams = [t for t in game.get('injuries', []) if int(t['team']['id']) == rule['teamId']]
    if len(teams) != 1 or not isinstance(teams[0].get('injuries'), list):
        return {'status': 'Unavailable'}
    rows = [i for i in teams[0]['injuries'] if int(i['athlete']['id']) == rule['teammateId']]
    return rows[0] if len(rows) == 1 else ({} if not rows else {'status': 'Unavailable'})


def choose_fallback(api, cfg, effective, now, directory=None, preview=False):
    rule = cfg['teammateDecision']
    player = api.players(effective, [rule['teammateId']])[rule['teammateId']]['player']
    require(player['proTeamId'] == rule['teamId'] and player['fullName'] == rule['teammateName'], 'Wrong teammate')
    injury = player.get('injuryStatus')
    report = teammate_report(rule)
    status = report.get('status')
    # ESPN can carry the previous game's designation into the new game's preview.
    stamp = report.get('date')
    fresh = stamp and datetime.fromisoformat(stamp.replace('Z', '+00:00')) >= datetime.fromisoformat(rule['freshAfter'])
    path = directory / 'teammate-clearance.json' if directory and rule.get('observeFrom') else None
    saved = json.loads(path.read_text()) if path and path.exists() else None
    if saved:
        require((saved['eventId'], saved['teammateId']) == (rule['eventId'], rule['teammateId']),
                'Teammate clearance belongs to a different game')
    # Only a corroborated, newer OUT report can supersede a recorded clearance.
    if injury == 'OUT' and status == 'Out' and fresh and (not saved or
            datetime.fromisoformat(stamp.replace('Z', '+00:00')) > datetime.fromisoformat(saved['checkedAt'])):
        if saved and not preview:
            path.replace(path.with_name('superseded-teammate-clearance.json'))
        return cfg['addId'], 'teammate_out'
    if saved:
        return rule['alternateId'], 'teammate_previously_cleared'
    if (fresh and status in ('Available', 'Active') and injury != 'OUT') or (injury == 'ACTIVE' and not report):
        if path and not preview:
            tmp = path.with_suffix('.tmp')
            write_json(tmp, {'eventId': rule['eventId'], 'teammateId': rule['teammateId'],
                             'checkedAt': now.isoformat(), 'gameStatus': status or 'off injury list',
                             'fantasyStatus': injury})
            tmp.replace(path)
        return rule['alternateId'], 'teammate_active'
    if now >= datetime.fromisoformat(rule['decide']):
        return rule['alternateId'], 'no_confirmed_absence_at_deadline'
    return None, 'waiting_for_teammate_status'


def tick(api, cfg, directory, now, preview=False):
    start, end = validate_config(cfg)
    status, journal = directory / 'status.json', directory / 'transaction'
    if status.exists() and not preview:
        old = json.loads(status.read_text())
        if old.get('terminal'):
            return old
    rule = cfg.get('teammateDecision')
    continuous = rule and rule.get('observeFrom')

    def observe_wait(state):
        value = {'state': state, 'terminal': False}
        if continuous and now >= datetime.fromisoformat(continuous):
            _, value['teammateDecision'] = choose_fallback(api, cfg, cfg['targetPeriod'], now, directory, preview)
        return value

    if not preview and now < start:
        return observe_wait('waiting_for_window')
    if rule and now >= end:
        if not continuous and now < datetime.fromisoformat(rule['resume']):
            return {'state': 'waiting_for_prelock_window', 'terminal': False}
        end = datetime.fromisoformat(rule['stop'])
    if now >= end:
        return {'state': 'expired_needs_review' if journal.exists() else 'expired_no_attempt', 'terminal': True}
    if journal.exists():
        if preview:
            return {'state': 'existing_attempt_needs_verification', 'terminal': False}
        require((journal / 'plan.json').exists(), 'Incomplete journal; manual review required')
        plan = json.loads((journal / 'plan.json').read_text())
        if rule:
            require(plan['add']['id'] in (cfg['addId'], rule['alternateId']) and plan['drop']['id'] == cfg['dropId'],
                    'Unknown saved conditional transaction')
            cfg = {**cfg, 'addId': plan['add']['id']}
        sub = journal / 'submission.json'
        result = verify(api, plan, json.loads(sub.read_text()) if sub.exists() else {})
        write_json(journal / 'verification.json', result)
        if result['state'] == 'verified_completed':
            return finish(api, cfg, directory, result)
        return {'state': result['state'], 'terminal': result['state'] == 'rejected_unchanged',
                'postAlreadyAttempted': True}
    league = api.get('?view=mSettings&view=mTeam')
    require(league['id'] == cfg['league'] and league['seasonId'] == cfg['season'], 'Identity mismatch')
    effective = league['status']['transactionScoringPeriod']
    if cfg.get('priorityClaim'):
        priority = cfg['priorityClaim']
        claim_id = priority.get('transactionId')
        if not claim_id:
            return observe_wait('waiting_for_priority_claim_evidence')
        rows = api.transactions()
        # ESPN's PROCESS row links to the original pending waiver by relatedTransactionId.
        linked = [t for t in rows if t.get('relatedTransactionId') == claim_id
                  and t.get('executionType') == 'PROCESS' and t.get('isPending') is False]
        if len(linked) > 1:
            return {'state': 'ambiguous_priority_claim_result', 'terminal': False}
        claim = linked[0] if linked else next((t for t in rows if t.get('id') == claim_id), None)
        if claim is None:
            return observe_wait('waiting_for_priority_claim_evidence')
        require(claim.get('teamId') == cfg['team'] and claim.get('type') == 'WAIVER'
                and {(i.get('type'), i.get('playerId')) for i in claim.get('items', [])}
                == {('ADD', priority['addId']), ('DROP', cfg['dropId'])}, 'Priority claim identity mismatch')
        if claim.get('isPending') or claim.get('status') == 'PENDING':
            return observe_wait('waiting_for_priority_claim')
        if claim.get('status') == 'EXECUTED' and claim.get('isPending') is False:
            pool = api.players(effective, [priority['addId'], cfg['dropId']])
            if pool[priority['addId']]['onTeamId'] != cfg['team'] or pool[cfg['dropId']]['onTeamId'] == cfg['team']:
                return {'state': 'waiting_for_priority_ownership', 'terminal': False}
            if preview:
                return {'state': 'priority_claim_awarded', 'terminal': False}
            primary_cfg = {**cfg, 'addId': priority['addId'], 'targetPeriod': priority['activationPeriod']}
            result = finish(api, primary_cfg, Path(priority['directory']), {'state': 'verified_completed'})
            return {**result, 'selectedPickup': priority['addId'], 'priorityClaimId': priority['transactionId']}
        if claim.get('isPending') is not False or claim.get('status') not in ('FAILED', 'REJECTED', 'CANCELED', 'FAILED_INVALIDPLAYERSOURCE'):
            return {'state': 'waiting_for_priority_claim_resolution', 'terminal': False}
        if priority.get('requireOtherWinner') or claim.get('status') == 'FAILED_INVALIDPLAYERSOURCE':
            if claim.get('status') == 'CANCELED':
                return {'state': 'primary_canceled_no_fallback', 'terminal': True}
            owner = api.players(effective, [priority['addId']])[priority['addId']]['onTeamId']
            if owner in (0, cfg['team']) or not any(
                t.get('teamId') == owner and t.get('type') == 'WAIVER' and t.get('status') == 'EXECUTED'
                and t.get('isPending') is False and t.get('scoringPeriodId') == cfg['targetPeriod']
                and any(i.get('type') == 'ADD' and i.get('playerId') == priority['addId'] for i in t.get('items', []))
                for t in rows):
                return {'state': 'waiting_for_competing_award', 'terminal': False}
    decision = {}
    original = cfg
    if rule:
        chosen, reason = choose_fallback(api, cfg, effective, now, directory, preview)
        if chosen is None:
            return {'state': reason, 'terminal': False}
        decision = {'selectedPickup': chosen, 'reason': reason}
        cfg = {**cfg, 'addId': chosen}
    pool = api.players(effective, [cfg['addId'], cfg['dropId']])
    add, drop = pool[cfg['addId']], pool[cfg['dropId']]
    detail = {'addStatus': add['status'], 'addOwner': add['onTeamId'],
              'effectivePeriod': effective, 'waiverProcessDate': add.get('waiverProcessDate'), **decision}
    if add['onTeamId'] != 0:
        return {'state': 'target_already_owned', 'terminal': True, **detail}
    if drop['onTeamId'] != cfg['team'] or drop['status'] != 'ONTEAM':
        return {'state': 'drop_no_longer_rostered', 'terminal': True, **detail}
    if effective > cfg['targetPeriod']:
        return {'state': 'unexpected_period_stop', 'terminal': True, **detail}
    if add['status'] == 'WAIVERS':
        return {'state': 'waiting_for_free_agent', 'terminal': False, **detail}
    if add['status'] != 'FREEAGENT':
        return {'state': 'unexpected_availability_stop', 'terminal': True, **detail}
    if effective < cfg['targetPeriod']:
        return {'state': 'waiting_for_target_period', 'terminal': False, **detail}
    require(league['scoringPeriodId'] in (cfg['protectedPeriod'], cfg['targetPeriod']), 'Unexpected current period')
    if add['player'].get('injuryStatus') in ('OUT', 'INJURY_RESERVE', 'SUSPENSION'):
        return {'state': 'target_ruled_out_needs_review', 'terminal': True, **detail}
    if preview:
        return {'state': 'preview_free_agent', 'terminal': False, **detail}
    plan = preflight(api, cfg['team'], cfg['addId'], cfg['dropId'])
    require(plan['effectivePeriod'] == cfg['targetPeriod'], 'Period changed during preflight')
    write_json(directory / 'protected-roster.json', roster_summary(api.roster(cfg['protectedPeriod'], cfg['team'])))
    if continuous:
        chosen, reason = choose_fallback(api, original, effective, datetime.now(timezone.utc), directory)
        if chosen != cfg['addId']:
            return {'state': 'teammate_status_changed_before_pickup', 'terminal': False, 'reason': reason}
    require(datetime.now(timezone.utc) < end, 'Window expired before submission')
    result = execute(api, plan, journal)
    if result['state'] == 'verified_completed':
        return {**finish(api, cfg, directory, result), **decision}
    return {'state': result['state'], 'terminal': result['state'] == 'rejected_unchanged',
            'postAlreadyAttempted': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    start, end = validate_config(cfg)
    directory = args.config.resolve().parent
    with (directory / 'job.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        now = datetime.now(timezone.utc)
        try:
            result = tick(ESPN(cfg['season'], cfg['league'], cfg.get('envFile', DEFAULT_ENV)),
                          cfg, directory, now, args.preview)
        except Refused as exc:
            retry = str(exc).startswith('ESPN read failed:')
            result = {'state': 'read_failed_retry' if retry else 'preflight_stopped',
                      'terminal': not retry, 'reason': str(exc)}
        except (OSError, ValueError, KeyError, StopIteration):
            stop = datetime.fromisoformat(cfg['teammateDecision']['stop']) if cfg.get('teammateDecision') else end
            result = {'state': 'read_or_verification_failed', 'terminal': now >= stop,
                      'postAlreadyAttempted': (directory / 'transaction').exists()}
        result['checkedAt'] = now.isoformat()
        if not args.preview:
            temp = directory / 'status.tmp'
            write_json(temp, result)
            temp.replace(directory / 'status.json')
            with (directory / 'checks.jsonl').open('a') as log:
                log.write(json.dumps(result) + '\n')
        print(json.dumps(result))


if __name__ == '__main__':
    main()
