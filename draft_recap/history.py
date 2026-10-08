"""Build public draft recaps from ESPN records; never export member information."""
from collections import defaultdict


def season_recap(year, league, players, benchmark_items):
    scoring = league['settings']['scoringSettings']
    benchmark = scoring['scoringType'] not in ('H2H_POINTS', 'TOTAL_POINTS')
    weights = benchmark_items if benchmark else scoring['scoringItems']
    player_map = {p['id']: p.get('player', p) for p in players}
    teams = {t['id']: t.get('name') or ' '.join(filter(None, [t.get('location'), t.get('nickname')])) or f"Team {t['id']}" for t in league['teams']}
    picks = []
    for pick in league.get('draftDetail', {}).get('picks', []):
        player = player_map.get(pick['playerId'], {})
        total = next((s for s in player.get('stats', [])
                      if s.get('seasonId') == year and s.get('statSourceId') == 0
                      and s.get('statSplitTypeId') == 0), None)
        points = None
        if total is not None:
            if not benchmark and total.get('appliedTotal') is not None:
                points = float(total['appliedTotal'])
            elif total.get('stats') is not None:
                points = sum(float(total['stats'].get(str(w['statId']), 0)) * float(w['points']) for w in weights)
        picks.append({
            'playerId': pick['playerId'], 'name': player.get('fullName') or f"Player {pick['playerId']}",
            'teamId': pick['teamId'], 'teamName': teams.get(pick['teamId'], f"Team {pick['teamId']}"),
            'round': pick['roundId'], 'pick': pick['overallPickNumber'],
            'points': round(points, 2) if points is not None else None,
            'scoringRank': None, 'value': None,
        })
    # Competition ranks: equal totals get the same rank. Missing data is not zero.
    known = sorted((p for p in picks if p['points'] is not None), key=lambda p: (-p['points'], p['pick']))
    rank = 0
    previous = None
    for i, p in enumerate(known, 1):
        if p['points'] != previous:
            rank = i
        p['scoringRank'] = rank
        p['value'] = p['pick'] - rank
        previous = p['points']
    grouped = defaultdict(list)
    for p in picks:
        grouped[p['teamId']].append(p)
    summaries = []
    for team_id, drafted in grouped.items():
        scored = [p for p in drafted if p['points'] is not None]
        complete = len(scored) == len(drafted)
        summaries.append({
            'teamId': team_id, 'teamName': teams.get(team_id, f'Team {team_id}'),
            'totalPoints': round(sum(p['points'] for p in scored), 2) if complete else None,
            'missingPlayers': len(drafted) - len(scored), 'picks': sorted(drafted, key=lambda p: p['pick']),
            'topScorers': sorted(scored, key=lambda p: (-p['points'], p['pick']))[:5],
            'worstScorers': sorted((p for p in scored if p['round'] <= 10), key=lambda p: (p['points'], p['pick']))[:3],
        })
    summaries.sort(key=lambda t: (t['totalPoints'] is None, -(t['totalPoints'] or 0), t['teamId']))
    previous = None
    rank = 0
    for i, team in enumerate(summaries, 1):
        if team['totalPoints'] is None:
            team['rank'] = None
        else:
            if team['totalPoints'] != previous:
                rank = i
            team['rank'] = rank
            previous = team['totalPoints']
    status = league.get('status', {})
    missing = len(picks) - len(known)
    # Incomplete coverage makes rank-based labels unreliable, so omit awards.
    steals = sorted((p for p in known if p['value'] > 0), key=lambda p: (-p['value'], p['pick']))[:5] if not missing else []
    busts = sorted((p for p in known if p['value'] < 0 and p['round'] <= 10), key=lambda p: (p['value'], p['pick']))[:5] if not missing else []
    return {
        'season': year, 'leagueName': league['settings'].get('name', ''),
        'seasonComplete': status.get('latestScoringPeriod', 0) > status.get('finalScoringPeriod', 0),
        'scoringType': scoring['scoringType'], 'benchmarkScoring': benchmark,
        'draftAvailable': bool(picks), 'missingPlayers': missing,
        'teams': summaries, 'steals': steals, 'busts': busts,
    }
