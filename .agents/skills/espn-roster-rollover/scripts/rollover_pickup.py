"""Run one explicitly authorized next-day pickup at roster rollover; preview is GET-only."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / '.agents/skills/espn-add-drop/scripts')]
from add_drop import ESPN, DEFAULT_ENV, Refused, require, preflight, execute, verify, roster_summary, write_json
from line_up.line_up_editer import plan_explicit_moves, verify_explicit_moves


def validate_config(cfg):
    require(cfg.get('authorized') is True, 'Exact pickup must be authorized')
    for key in ('season', 'league', 'team', 'addId', 'dropId', 'protectedPeriod', 'targetPeriod'):
        require(isinstance(cfg.get(key), int) and cfg[key] > 0, 'Missing positive identity/period')
    require(cfg['addId'] != cfg['dropId'], 'Add and drop must differ')
    require(cfg['targetPeriod'] == cfg['protectedPeriod'] + 1, 'Only next-day rollover supported')
    start, end = map(datetime.fromisoformat, (cfg['start'], cfg['end']))
    require(start.tzinfo is not None and end.tzinfo is not None and start < end, 'Use an explicit timed window')
    require((end - start).total_seconds() <= 3600, 'Rollover window must not exceed one hour')
    return start, end


def minimal_activation(api, cfg):
    period, team, add = cfg['targetPeriod'], cfg['team'], cfg['addId']
    entries = api.roster(period, team)
    by_id = {e['playerId']: e for e in entries}
    require(add in by_id, 'Acquired player missing from target roster')
    slot = by_id[add]['lineupSlotId']
    if slot < 12:
        return plan_explicit_moves(api, team, period, {add: slot})
    league = api.get('?view=mSettings&view=mTeam')
    counts = {int(k): v for k, v in league['settings']['rosterSettings']['lineupSlotCounts'].items() if int(k) < 12 and v > 0}
    pro = api.season_view('proTeamSchedules')
    playing = {t['id'] for t in pro['settings']['proTeams']
               if any(not g.get('canceled') and not g.get('postponed')
                      for g in t.get('proGamesByScoringPeriod', {}).get(str(period), []))}
    raw = by_id[add]['playerPoolEntry']['player']
    require(raw['proTeamId'] in playing, 'Pickup has no game on intended date')
    eligible = [s for s in counts if s in raw['eligibleSlots']]
    for target in eligible:
        occupants = [e for e in entries if e['lineupSlotId'] == target]
        if len(occupants) < counts[target]:
            return plan_explicit_moves(api, team, period, {add: target})
    for target in eligible:
        for e in entries:
            p = e['playerPoolEntry']['player']
            if e['lineupSlotId'] == target and (p['proTeamId'] not in playing or
                    p.get('injuryStatus') in ('OUT', 'INJURY_RESERVE', 'SUSPENSION')):
                return plan_explicit_moves(api, team, period, {add: target, e['playerId']: 12})
    raise Refused('No empty or idle eligible active slot; lineup needs review')


def reconcile_activation(api, cfg, directory):
    journal = directory / 'lineup'
    if journal.exists():
        require((journal / 'plan.json').exists(), 'Incomplete lineup journal; review required')
        plan = json.loads((journal / 'plan.json').read_text())
        sub = journal / 'submission.json'
        result = verify_explicit_moves(api, plan, json.loads(sub.read_text()) if sub.exists() else {})
        write_json(journal / 'verification.json', result)
        return result
    plan = minimal_activation(api, cfg)
    if not plan['payload']['items']:
        return {'state': 'already_set', 'period': cfg['targetPeriod']}
    journal.mkdir(exist_ok=False)
    write_json(journal / 'plan.json', plan)
    write_json(journal / 'attempt.json', {'state': 'one_attempt'})
    submission = api.post(plan['payload'])
    write_json(journal / 'submission.json', submission)
    result = verify_explicit_moves(api, plan, submission)
    write_json(journal / 'result.json', result)
    return result


def finish(api, cfg, directory, result):
    protected = json.loads((directory / 'protected-roster.json').read_text())
    after = roster_summary(api.roster(cfg['protectedPeriod'], cfg['team']))
    same = {p['id']: p['slot'] for p in protected} == {p['id']: p['slot'] for p in after}
    if not same:
        return {'state': 'protected_roster_changed_needs_review', 'terminal': True, 'acquisition': result['state']}
    lineup = reconcile_activation(api, cfg, directory)
    league = api.get('?view=mSettings&view=mTeam')
    team = next(t for t in league['teams'] if t['id'] == cfg['team'])
    return {'state': 'verified_completed' if lineup['state'] in ('verified_completed', 'already_set') else 'lineup_unverified',
            'terminal': True, 'acquisition': result['state'], 'lineup': lineup,
            'protectedRosterPreserved': True,
            'acquisitionCounters': team.get('transactionCounter', {}).get('matchupAcquisitionTotals', {})}


def tick(api, cfg, directory, now, preview=False):
    start, end = validate_config(cfg)
    status_path, journal = directory / 'status.json', directory / 'transaction'
    if status_path.exists() and not preview:
        old = json.loads(status_path.read_text())
        if old.get('terminal'):
            return old
    if not preview and now < start:
        return {'state': 'waiting_for_window', 'terminal': False}
    if not preview and now >= end:
        return {'state': 'expired_needs_review' if journal.exists() else 'expired_no_attempt', 'terminal': True}
    if journal.exists() and not preview:
        require((journal / 'plan.json').exists(), 'Incomplete transaction journal; review required')
        plan = json.loads((journal / 'plan.json').read_text())
        sub = journal / 'submission.json'
        result = verify(api, plan, json.loads(sub.read_text()) if sub.exists() else {})
        write_json(journal / 'verification.json', result)
        if result['state'] == 'verified_completed':
            return finish(api, cfg, directory, result)
        return {'state': result['state'], 'terminal': result['state'] == 'rejected_unchanged', 'postAlreadyAttempted': True}
    league = api.get('?view=mSettings&view=mTeam')
    require(league['id'] == cfg['league'] and league['seasonId'] == cfg['season'], 'League identity mismatch')
    effective = league['status']['transactionScoringPeriod']
    detail = {'currentPeriod': league['scoringPeriodId'], 'effectivePeriod': effective,
              'targetPeriod': cfg['targetPeriod']}
    if effective < cfg['targetPeriod']:
        return {'state': 'waiting_for_roster_rollover', 'terminal': False, **detail}
    if effective != cfg['targetPeriod'] or league['scoringPeriodId'] != cfg['protectedPeriod']:
        return {'state': 'unexpected_period_stop', 'terminal': True, **detail}
    pool = api.players(effective, [cfg['addId'], cfg['dropId']])
    add = pool[cfg['addId']]
    if add['onTeamId'] != 0 or add['status'] != 'FREEAGENT':
        return {'state': 'target_unavailable', 'terminal': True, **detail}
    if add['player'].get('injuryStatus') in ('OUT', 'INJURY_RESERVE', 'SUSPENSION'):
        return {'state': 'target_ruled_out_needs_review', 'terminal': True, **detail}
    plan = preflight(api, cfg['team'], cfg['addId'], cfg['dropId'], rollover_target_period=cfg['targetPeriod'])
    if preview:
        return {'state': 'preview_ready', 'plan': plan, 'terminal': False}
    # Reread just before submission to avoid applying the pair to the protected day.
    fresh = api.get('?view=mSettings&view=mTeam')
    require(fresh['scoringPeriodId'] == cfg['protectedPeriod'] and
            fresh['status']['transactionScoringPeriod'] == cfg['targetPeriod'], 'Period changed before submission')
    require(datetime.now(timezone.utc) < end, 'Window expired before submission')
    write_json(directory / 'protected-roster.json', roster_summary(api.roster(cfg['protectedPeriod'], cfg['team'])))
    result = execute(api, plan, journal)
    if result['state'] == 'verified_completed':
        return finish(api, cfg, directory, result)
    return {'state': result['state'], 'terminal': result['state'] == 'rejected_unchanged',
            'postAlreadyAttempted': True, 'submission': result.get('submission')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    validate_config(cfg)
    directory = args.config.resolve().parent
    with (directory / 'job.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        now = datetime.now(timezone.utc)
        try:
            result = tick(ESPN(cfg['season'], cfg['league'], cfg.get('envFile', DEFAULT_ENV)), cfg, directory, now, args.preview)
        except Refused as exc:
            result = {'state': 'preflight_stopped', 'terminal': True, 'reason': str(exc)}
        except (OSError, ValueError, KeyError, StopIteration):
            result = {'state': 'read_or_verification_failed', 'terminal': False,
                      'postAlreadyAttempted': (directory / 'transaction').exists()}
        result['checkedAt'] = now.isoformat()
        if not args.preview:
            tmp = directory / 'status.tmp'
            write_json(tmp, result)
            tmp.replace(directory / 'status.json')
            with (directory / 'checks.jsonl').open('a') as log:
                log.write(json.dumps(result) + '\n')
        print(json.dumps(result))


if __name__ == '__main__':
    main()
