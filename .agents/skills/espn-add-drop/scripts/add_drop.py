#!/usr/bin/env python3
"""One paired ESPN basketball add/drop. Default: read-only preview."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

DEFAULT_ENV = '/home/hong/fantasy_basketball_tools/.env'


class Refused(Exception):
    pass


def require(condition, message):
    if not condition:
        raise Refused(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def credentials(path):
    values = {}
    for line in Path(path).read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip().strip('\"\'')
    values.update(os.environ)
    require(all(values.get(k) for k in ('ESPN_S2', 'SWID')), 'Missing ESPN credentials')
    return values


def normalize_owner(value):
    return str(value).strip().strip('{}').lower()


def transaction_summary(row):
    keys = ('id', 'type', 'status', 'isPending', 'scoringPeriodId', 'teamId', 'items')
    return {k: row[k] for k in keys if k in row}


def matching(rows, team, add, drop):
    return [transaction_summary(t) for t in rows
            if t.get('teamId') == team and t.get('type') == 'FREEAGENT'
            and {(i.get('type'), i.get('playerId')) for i in t.get('items', [])}
            == {('ADD', add), ('DROP', drop)}]


def roster_summary(entries):
    return [{'id': e['playerId'], 'slot': e['lineupSlotId'],
             'name': e['playerPoolEntry']['player']['fullName']} for e in entries]


class ESPN:
    def __init__(self, season, league, env_file):
        cfg = credentials(env_file)
        self.owner = normalize_owner(cfg['SWID'])
        self.season, self.league = season, league
        self.base = (f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/'
                     f'seasons/{season}/segments/0/leagues/{league}')
        self.headers = {'Cookie': f"espn_s2={cfg['ESPN_S2']}; SWID={cfg['SWID']}",
                        'Accept': 'application/json', 'Content-Type': 'application/json',
                        'Origin': 'https://fantasy.espn.com', 'Referer': 'https://fantasy.espn.com/'}
        self.secrets = (cfg['ESPN_S2'], cfg['SWID'], cfg['SWID'].strip('{}'))

    def redact(self, value):
        text = str(value)
        for secret in self.secrets:
            if secret:
                text = text.replace(secret, '[redacted]')
        return text

    def get(self, query, extra=None):
        req = urllib.request.Request(self.base + query, headers={**self.headers, **(extra or {})})
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                return json.load(response)
        except (OSError, ValueError) as exc:
            raise Refused(f'ESPN read failed: {type(exc).__name__}; no cached data substituted') from None

    def players(self, period, ids):
        filt = {'players': {'filterIds': {'value': ids}}}
        data = self.get(f'?view=kona_player_info&scoringPeriodId={period}',
                        {'x-fantasy-filter': json.dumps(filt)})
        return {e['id']: e for e in data['players']}

    def roster(self, period, team):
        data = self.get(f'?view=mRoster&scoringPeriodId={period}')
        return next(t for t in data['teams'] if t['id'] == team)['roster']['entries']

    def transactions(self):
        return self.get('?view=mTransactions2').get('transactions', [])

    def season_view(self, view):
        url = self.base.split('/segments/')[0] + '?view=' + view
        try:
            with urllib.request.urlopen(url, timeout=25) as response:
                return json.load(response)
        except (OSError, ValueError):
            raise Refused('Season metadata read failed') from None

    def post(self, payload):
        req = urllib.request.Request(self.base.replace('lm-api-reads.', 'lm-api-writes.') + '/transactions/',
                                     data=json.dumps(payload).encode(), headers=self.headers, method='POST')
        result = {}
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                result['httpStatus'], raw = response.status, response.read().decode()
        except urllib.error.HTTPError as exc:
            result['httpStatus'], raw = exc.code, exc.read().decode()
        except OSError as exc:
            return {'transportError': type(exc).__name__}
        try:
            body = json.loads(raw)
        except ValueError:
            return {**result, 'nonJsonResponse': True}
        if isinstance(body, dict):
            result['response'] = transaction_summary(body)
            for key in ('messages', 'errors', 'message'):
                if key in body:
                    result[key] = self.redact(json.dumps(body[key]))[:2000]
            result['errorTypes'] = [d.get('type') for d in body.get('details', []) if isinstance(d, dict)]
        else:
            result['unexpectedResponseType'] = type(body).__name__
        return result


def preflight(api, team_id, add_id, drop_id, *, rollover_target_period=None):
    require(add_id != drop_id, 'Add and drop must be different players')
    league = api.get('?view=mSettings&view=mTeam')
    require(league['id'] == api.league and league['seasonId'] == api.season, 'League/season mismatch')
    require(league['status'].get('isActive') and not league['status'].get('isExpired'), 'League inactive')
    team = next((t for t in league['teams'] if t['id'] == team_id), None)
    require(team is not None, 'Team not found')
    owners = [team.get('primaryOwner'), *team.get('owners', [])]
    require(api.owner in {normalize_owner(o) for o in owners if o}, 'Session is not an owner of this team')
    require(not team.get('isTransactionLocked'), 'Team transactions locked')
    current = league['scoringPeriodId']
    effective = league['status'].get('transactionScoringPeriod', current)
    budget_matchup = league['status']['currentMatchupPeriod']
    if rollover_target_period is not None:
        require(effective == rollover_target_period and current == effective - 1,
                'Expected next-day roster rollover has not occurred')
        # Rollover jobs may inspect the target matchup's allowance. This is not
        # proof ESPN charges that allowance: one atomic request lets ESPN decide.
        calendar = api.season_view('chui_default')
        segment = next(s for s in calendar['segments'] if s['id'] == league.get('segmentId', 0))
        schedule = league['settings']['scheduleSettings']
        periods = next(t['periods'] for t in segment['periodTypes'] if t['id'] == schedule['periodTypeId'])
        period_ids = {p['id'] for p in periods if p['scoringPeriodStart'] <= effective <= p['scoringPeriodEnd']}
        matchups = [int(mid) for mid, ids in schedule['matchupPeriods'].items() if period_ids.intersection(ids)]
        require(len(matchups) == 1, 'Cannot resolve target matchup budget')
        budget_matchup = matchups[0]
    pool = api.players(effective, [add_id, drop_id])
    require(add_id in pool and drop_id in pool, 'Player ID missing from live pool')
    add, drop = pool[add_id], pool[drop_id]
    require(add['onTeamId'] == 0 and add['status'] == 'FREEAGENT',
            'Add player is not a free agent; no waiver claim or substitution will be made')
    require(drop['onTeamId'] == team_id and drop['status'] == 'ONTEAM', 'Drop player is not on this team')
    require(drop['player'].get('droppable') is True, 'Drop player is undroppable or status unknown')
    for entry in (add, drop):
        require(entry.get('rosterLocked') is False and entry.get('tradeLocked') is False,
                'Effective-period roster/trade lock is set or unknown')
    settings = league['settings']
    limit = settings['acquisitionSettings'].get('matchupAcquisitionLimit', -1)
    used = team.get('transactionCounter', {}).get('matchupAcquisitionTotals', {}).get(
        str(budget_matchup), 0)
    require(limit is not None and (limit < 0 or used < limit), 'Matchup acquisition limit reached or unknown')
    season_limit = settings['acquisitionSettings'].get('acquisitionLimit', -1)
    require(season_limit is not None and (season_limit < 0 or
            team.get('transactionCounter', {}).get('acquisitions', 0) < season_limit), 'Season acquisition limit reached')
    roster = roster_summary(api.roster(effective, team_id))
    require(drop_id in {p['id'] for p in roster} and add_id not in {p['id'] for p in roster},
            'Ownership and effective roster disagree')
    slot_counts = settings['rosterSettings']['lineupSlotCounts']
    require(slot_counts.get('12', 0) > 0 and 12 in add['player'].get('eligibleSlots', []), 'No eligible bench slot')
    drop_slot = next(p['slot'] for p in roster if p['id'] == drop_id)
    require(drop_slot not in (13, 14), 'Dropping from IR needs a separate active-roster capacity review')
    bench_after = sum(p['slot'] == 12 for p in roster) + (drop_slot != 12)
    require(settings['rosterSettings'].get('isBenchUnlimited') or bench_after <= slot_counts['12'],
            'Bench capacity requires a separate lineup change')
    payload = {'isLeagueManager': False, 'teamId': team_id, 'type': 'FREEAGENT',
               'scoringPeriodId': current, 'executionType': 'EXECUTE', 'items': [
                   {'playerId': add_id, 'type': 'ADD', 'fromTeamId': 0, 'toTeamId': team_id,
                    'fromLineupSlotId': -1, 'toLineupSlotId': 12},
                   {'playerId': drop_id, 'type': 'DROP', 'fromTeamId': team_id, 'toTeamId': 0,
                    'fromLineupSlotId': drop_slot, 'toLineupSlotId': -1}]}
    txs = matching(api.transactions(), team_id, add_id, drop_id)
    require(not any(t.get('isPending') or t.get('status') == 'PENDING' for t in txs),
            'Matching pending transaction exists; reconcile it first')
    return {'season': api.season, 'league': api.league, 'team': team_id, 'teamName': team.get('name'),
            'add': {'id': add_id, 'name': add['player']['fullName']},
            'drop': {'id': drop_id, 'name': drop['player']['fullName']},
            'currentPeriod': current, 'effectivePeriod': effective, 'beforeRoster': roster,
            'budgetMatchupChecked': budget_matchup,
            'budgetNote': 'ESPN determines actual charge; future-matchup acceptance not guaranteed'
                if rollover_target_period is not None else 'Current matchup allowance checked',
            'priorTransactionIds': [t['id'] for t in txs], 'payload': payload, 'checkedAt': now()}


def verify(api, plan, submission):
    team, add, drop = plan['team'], plan['add']['id'], plan['drop']['id']
    period = plan['effectivePeriod']
    pool = api.players(period, [add, drop])
    roster = roster_summary(api.roster(period, team))
    txs = matching(api.transactions(), team, add, drop)
    response_id = submission.get('response', {}).get('id')
    txs = [t for t in txs if t.get('id') == response_id or t.get('id') not in plan['priorTransactionIds']]
    ids = {p['id'] for p in roster}
    expected = ({p['id'] for p in plan['beforeRoster']} - {drop}) | {add}
    owned = pool[add]['onTeamId'] == team and pool[add]['status'] == 'ONTEAM' and pool[drop]['onTeamId'] == 0
    executed = any(t.get('status') == 'EXECUTED' and t.get('isPending') is False for t in txs)
    if owned and ids == expected and executed:
        state = 'verified_completed'
    elif any(t.get('isPending') or t.get('status') == 'PENDING' for t in txs):
        state = 'pending'
    else:
        state = 'unverified'
        # A definite client-error rejection plus unchanged state can be corrected manually.
        unchanged = (pool[add]['onTeamId'] == 0 and pool[add]['status'] == 'FREEAGENT'
                     and pool[drop]['onTeamId'] == team and pool[drop]['status'] == 'ONTEAM'
                     and ids == {p['id'] for p in plan['beforeRoster']})
        if submission.get('httpStatus') in (400, 401, 403, 409, 422) and unchanged and not txs:
            state = 'rejected_unchanged'
    return {'state': state, 'ownership': [{'id': pid, 'owner': pool[pid]['onTeamId'],
            'status': pool[pid]['status']} for pid in (add, drop)], 'effectivePeriod': period,
            'lineup': roster, 'matchingTransactions': txs, 'checkedAt': now()}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def execute(api, plan, journal):
    journal.mkdir(parents=True, exist_ok=False)  # refuses repeat even after a crash
    write_json(journal / 'plan.json', plan)
    write_json(journal / 'attempt.json', {'startedAt': now()})
    submission = api.post(plan['payload'])  # exactly one POST; never retried
    write_json(journal / 'submission.json', submission)
    try:
        result = verify(api, plan, submission)
    except (Refused, KeyError, StopIteration, OSError):
        result = {'state': 'unverified', 'readbackError': 'Readback failed; use --verify', 'checkedAt': now()}
    result['submission'] = submission
    write_json(journal / 'result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--season', type=int)
    parser.add_argument('--league', type=int, default=30695)
    parser.add_argument('--team', type=int, default=2)
    parser.add_argument('--add-id', type=int)
    parser.add_argument('--drop-id', type=int)
    parser.add_argument('--env-file', default=DEFAULT_ENV)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--journal', type=Path)
    parser.add_argument('--verify', type=Path, help='Read-only reconciliation of an existing journal')
    args = parser.parse_args()
    try:
        if args.verify:
            require(not args.execute, '--verify cannot execute')
            plan = json.loads((args.verify / 'plan.json').read_text())
            api = ESPN(plan['season'], plan['league'], args.env_file)
            path = args.verify / 'submission.json'
            submission = json.loads(path.read_text()) if path.exists() else {}
            result = verify(api, plan, submission)
            write_json(args.verify / 'verification.json', result)
        else:
            require(all((args.season, args.add_id, args.drop_id)), '--season, --add-id and --drop-id are required')
            require(not args.execute or args.journal is not None, '--execute requires a unique --journal directory')
            api = ESPN(args.season, args.league, args.env_file)
            plan = preflight(api, args.team, args.add_id, args.drop_id)
            result = execute(api, plan, args.journal) if args.execute else {'state': 'preview_only', 'plan': plan}
        print(json.dumps(result, indent=2))
        return 0 if result['state'] in ('preview_only', 'verified_completed') else 2
    except (Refused, OSError, ValueError, KeyError, StopIteration) as exc:
        # Do not emit arbitrary exception strings that could include HTTP headers/member data.
        message = str(exc) if isinstance(exc, Refused) else type(exc).__name__
        print(json.dumps({'state': 'stopped', 'reason': message}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
