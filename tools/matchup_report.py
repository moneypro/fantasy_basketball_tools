"""GET-only matchup outlook with live season boundaries and legal lineup capacity."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
from matchup_tables import fetch_boxes, build_tables, render_markdown
from pickup_report import Collector, config, normalize, best_lineup, average, PACIFIC, SLOTS


def matchup_bounds(league, season_data):
    settings = league['settings']['scheduleSettings']
    segment = next(s for s in season_data['segments'] if s['id'] == league.get('segmentId', 0))
    periods = next(t['periods'] for t in segment['periodTypes'] if t['id'] == settings['periodTypeId'])
    selected = settings['matchupPeriods'][str(league['status']['currentMatchupPeriod'])]
    rows = [p for p in periods if p['id'] in selected]
    if not rows:
        raise RuntimeError('No verified matchup boundaries')
    return min(p['scoringPeriodStart'] for p in rows), max(p['scoringPeriodEnd'] for p in rows)


def player_baselines(raw, season, weights):
    """Keep the legacy recent-split blend as a labeled comparison, using the live year."""
    projected = average(raw, season, True, weights)
    current = average(raw, season, False, weights)
    previous = average(raw, season - 1, False, weights)
    splits = []
    for split in (3, 2, 1):
        row = next((s for s in raw.get('stats', []) if s.get('id') == f'0{split}{season}'), None)
        if row and row.get('stats', {}).get('42'):
            splits.append(sum(row['stats'].get(str(k), 0) * v for k, v in weights.items()) / row['stats']['42'])
    if projected is not None:
        splits.append(projected)
    fallback = current if current is not None else previous
    return {'seasonBaseline': projected if projected is not None else fallback,
            'recentBlend': statistics.mean(splits) if splits else fallback,
            'baselineSource': 'season projection' if projected is not None else
                'current-season actual fallback' if current is not None else
                'previous-season actual fallback' if previous is not None else 'unavailable',
            'blendSplitCount': len(splits)}


def daily_projection(roster, slots, games, method, include_dtd, current=False):
    """Started games never enter remaining projections; locked active slots stay occupied."""
    available_slots = list(slots)
    candidates, live, missing = [], [], []
    for player in roster:
        game = games.get(player['nbaTeamId'])
        if not game:
            continue
        if current and game['state'] != 'pre':
            if player['slot'] in available_slots:
                available_slots.remove(player['slot'])
                if game['state'] == 'in':
                    live.append(player['name'])
            continue
        if player['slot'] in (13, 14) or player['injury'] in ('OUT', 'INJURY_RESERVE', 'SUSPENSION'):
            continue
        if not include_dtd and player['injury'] != 'ACTIVE':
            continue
        if player[method] is None:
            missing.append(player['name'])
            continue
        candidates.append({**player, 'projected': player[method]})
    points, selection = best_lineup(candidates, available_slots)
    by_id = {p['id']: p for p in roster}
    return {'unstartedPoints': round(points, 2), 'usableStarts': len(selection),
            'inProgressActivePlayers': live, 'missingBaselines': missing,
            'players': [{'id': pid, 'name': by_id[pid]['name'], 'slot': SLOTS.get(slot, str(slot)),
                         'savedSlot': SLOTS.get(by_id[pid]['slot'], str(by_id[pid]['slot'])),
                         'points': round(by_id[pid][method], 2), 'injury': by_id[pid]['injury'],
                         'baselineSource': by_id[pid]['baselineSource']} for pid, slot in selection]}


def collect(args):
    root = Path(__file__).resolve().parents[1]
    cfg = config(Path(args.env_file or root / '.env'))
    league_id = args.league or int(cfg['LEAGUE_ID'])
    today = datetime.now(PACIFIC).date()
    year = args.season or today.year + (today.month >= 7)
    output = Path(args.output) if args.output else root / 'output' / f'matchup_{today}_{datetime.now(PACIFIC):%H%M%S}'
    c = Collector(output)
    nonce = str(int(datetime.now(timezone.utc).timestamp() * 1000))
    headers = {'Cache-Control': 'no-cache', 'Cookie': f"espn_s2={cfg['ESPN_S2']}; SWID={cfg['SWID']}"}
    season_url = f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{year}'
    base = f'{season_url}/segments/0/leagues/{league_id}'
    league = c.get('league', base + '?view=mSettings&view=mTeam&view=mRoster&view=mMatchupScore&_=' + nonce, headers)
    if league['seasonId'] != year or league['id'] != league_id:
        raise RuntimeError('League or season mismatch')
    if league['settings']['scoringSettings']['scoringType'] != 'H2H_POINTS':
        raise RuntimeError('Matchup forecast supports H2H points only')
    season = c.get('season_calendar', season_url + '?view=chui_default')
    start, end = matchup_bounds(league, season)
    current = league['scoringPeriodId']
    if not start <= current <= end:
        raise RuntimeError('Current period is outside verified matchup boundaries')
    match = next(m for m in league['schedule'] if m['matchupPeriodId'] == league['status']['currentMatchupPeriod']
                 and any(m.get(side, {}).get('teamId') == args.team for side in ('home', 'away')))
    if not all(match.get(side, {}).get('teamId') for side in ('home', 'away')):
        raise RuntimeError('No two-team matchup (possibly a bye)')
    team_ids = [match[side]['teamId'] for side in ('home', 'away')]
    pro = c.get('pro_schedule', season_url + '?view=proTeamSchedules')
    nba = {t['id']: t for t in pro['settings']['proTeams']}
    board = c.get('today_scoreboard', 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=' + today.strftime('%Y%m%d') + '&_=' + nonce)
    states = {str(e['id']): e['status']['type']['state'] for e in board.get('events', [])}
    schedule, dates = {}, {}
    for tid, team in nba.items():
        for period, gs in team.get('proGamesByScoringPeriod', {}).items():
            period = int(period)
            for g in gs:
                if g.get('canceled') or g.get('postponed'):
                    continue
                day = datetime.fromtimestamp(g['date'] / 1000, PACIFIC).date().isoformat()
                dates.setdefault(period, set()).add(day)
                event_id = str(g.get('id'))
                state = states.get(event_id, 'pre')
                # Never count an already-started game when the scoreboard record is missing.
                if period == current and event_id not in states and g['date'] / 1000 <= datetime.now(timezone.utc).timestamp():
                    state = 'in'
                schedule.setdefault(period, {})[tid] = {'state': state, 'eventId': event_id}
    if dates.get(current) != {str(today)}:
        raise RuntimeError('Live scoring period does not match the current Pacific date')
    weights = {x['statId']: x['points'] for x in league['settings']['scoringSettings']['scoringItems']}
    slots = [int(k) for k, n in league['settings']['rosterSettings']['lineupSlotCounts'].items() if int(k) < 12 for _ in range(n)]
    warnings = ['Projections assume optimized legal starters, not saved future lineups.',
                'Season baselines do not adjust for opponent defense or changing minutes; review injury/role news.',
                'The legacy-style recent blend averages overlapping 30/15/7-day splits and season projection. Early-season splits can duplicate the same tiny sample.',
                'Differences between models are not confidence intervals; no calibrated win probability is provided.',
                'OUT players are excluded for the remaining horizon; review likely returns before using a multi-day outlook.',
                'In-progress game remainder is not modeled; final totals stay unavailable while either team has active live games or missing baselines.']
    teams = {}
    for side in ('home', 'away'):
        tid = match[side]['teamId']
        team = next(t for t in league['teams'] if t['id'] == tid)
        entries = team['roster']['entries']
        slotmap = {e['playerId']: e['lineupSlotId'] for e in entries}
        roster = []
        for entry in entries:
            raw = entry['playerPoolEntry']['player']
            p = normalize(entry['playerPoolEntry'], year, weights, nba, slotmap)
            p.update(player_baselines(raw, year, weights))
            roster.append(p)
        settled = match[side]['totalPoints']
        live_score = match[side].get('totalPointsLive')
        if live_score is None:
            live_score = settled
        models = {}
        for method in ('seasonBaseline', 'recentBlend'):
            models[method] = {}
            for include in (True, False):
                days = [{'period': p, 'date': sorted(dates.get(p, [])),
                         **daily_projection(roster, slots, schedule.get(p, {}), method, include, p == current)}
                        for p in range(current, end + 1)]
                total = round(sum(d['unstartedPoints'] for d in days), 2)
                complete = not any(d['inProgressActivePlayers'] or d['missingBaselines'] for d in days)
                models[method]['includingDTD' if include else 'activeOnly'] = {
                    'remainingUnstartedPoints': total, 'finalProjectedTotal': round(live_score + total, 2) if complete else None,
                    'days': days}
        teams[str(tid)] = {'name': team.get('name', str(tid)), 'settledScore': settled, 'liveScore': live_score,
                           'roster': roster, 'models': models, 'waiverPriority': team.get('waiverRank'),
                           'acquisitionsUsed': team.get('transactionCounter', {}).get('matchupAcquisitionTotals', {}).get(str(league['status']['currentMatchupPeriod']), 0)}
    other = next(t for t in team_ids if t != args.team)
    comparisons = []
    for method in ('seasonBaseline', 'recentBlend'):
        for yours in ('includingDTD', 'activeOnly'):
            for theirs in ('includingDTD', 'activeOnly'):
                a = teams[str(args.team)]['models'][method][yours]['finalProjectedTotal']
                b = teams[str(other)]['models'][method][theirs]['finalProjectedTotal']
                comparisons.append({'model': method, 'yourHealthScenario': yours, 'opponentHealthScenario': theirs,
                                    'projectedMargin': round(a - b, 2) if a is not None and b is not None else None})
    packet = {'fetchedAt': datetime.now(timezone.utc).isoformat(), 'date': str(today), 'season': year,
              'leagueId': league_id, 'teamId': args.team, 'opponentId': other,
              'matchupPeriod': league['status']['currentMatchupPeriod'], 'currentScoringPeriod': current,
              'transactionScoringPeriod': league['status'].get('transactionScoringPeriod'),
              'startPeriod': start, 'endPeriod': end, 'startDates': sorted(dates.get(start, [])),
              'endDates': sorted(dates.get(end, [])), 'teams': teams, 'comparisons': comparisons,
              'acquisitionLimit': league['settings']['acquisitionSettings'].get('matchupAcquisitionLimit'),
              'warnings': warnings, 'sources': c.sources, 'actionState': 'read_only'}
    no_return = {}
    if getattr(args, 'no_return_file', None):
        override = json.loads(Path(args.no_return_file).read_text())
        if override.get('date') != str(today):
            raise ValueError('No-return evidence must match today')
        no_return = override['players']
        if not all(isinstance(v, dict) and v.get('source') and v.get('reason') for v in no_return.values()):
            raise ValueError('No-return evidence needs source and reason')
    boxes = fetch_boxes(c, board, {str(p['id']) for t in teams.values() for p in t['roster']}, nonce)
    packet['playerTables'] = build_tables(packet, schedule, boxes, weights, no_return)
    packet['tableFetchedAt'] = datetime.now(timezone.utc).isoformat()
    packet['reportMarkdown'] = render_markdown(packet)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'matchup.md').write_text(packet['reportMarkdown'])
    (output / 'live_boxscores.json').write_text(json.dumps(boxes, indent=2) + '\n')
    (output / 'matchup.json').write_text(json.dumps(packet, indent=2) + '\n')
    return packet


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--season', type=int)
    parser.add_argument('--league', type=int)
    parser.add_argument('--team', type=int, default=2)
    parser.add_argument('--env-file')
    parser.add_argument('--output')
    parser.add_argument('--no-return-file', help='Dated JSON injury evidence: date and players keyed by ESPN ID, each with source and reason')
    parser.add_argument('--format', choices=('markdown', 'json'), default='markdown')
    args = parser.parse_args()
    try:
        packet = collect(args)
        print(packet['reportMarkdown'] if args.format == 'markdown' else json.dumps(packet, indent=2))
    except (RuntimeError, KeyError, ValueError, OSError, StopIteration) as exc:
        raise SystemExit('Matchup collection failed: ' + type(exc).__name__) from None
