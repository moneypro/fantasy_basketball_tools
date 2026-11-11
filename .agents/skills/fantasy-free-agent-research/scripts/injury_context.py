#!/usr/bin/env python3
"""Read-only league-wide ESPN injury inventory and normalized player pool."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.pickup_report import Collector, config, normalize, utc_now


def collect(args):
    cfg = config(ROOT / '.env')
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    c = Collector(output.parent)
    headers = {'Cookie': f"espn_s2={cfg['ESPN_S2']}; SWID={cfg['SWID']}"}
    base = f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{args.season}/segments/0/leagues/{args.league}'
    league = c.get('league_settings', base + '?view=mSettings', headers)
    if league.get('seasonId') != args.season or league.get('id') != args.league:
        raise RuntimeError('League/season mismatch')
    period = league['scoringPeriodId']
    weights = {s['statId']: s['points'] for s in league['settings']['scoringSettings']['scoringItems']}
    pro = c.get('nba_teams', f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{args.season}?view=proTeamSchedules')
    teams = {t['id']: t for t in pro['settings']['proTeams'] if t['id'] != 0}
    players, seen = [], set()
    for offset in range(0, 10000, 500):
        filt = {'players': {'limit': 500, 'offset': offset,
                'sortDraftRanks': {'sortPriority': 1, 'sortAsc': True, 'value': 'STANDARD'},
                'filterStatsForTopScoringPeriodIds': {'value': 1,
                    'additionalValue': [f'00{args.season - 1}', f'10{args.season}', f'00{args.season}']}}}
        chunk = c.get(f'players_{offset}', base + f'?view=kona_player_info&scoringPeriodId={period}',
                      {**headers, 'x-fantasy-filter': json.dumps(filt)})['players']
        fresh = [p for p in chunk if p['id'] not in seen]
        if chunk and not fresh:
            raise RuntimeError('Player pagination did not advance')
        players.extend(normalize(p, args.season, weights, teams, {}) for p in fresh)
        seen.update(p['id'] for p in fresh)
        if len(chunk) < 500:
            break
    else:
        raise RuntimeError('Player pool exceeded pagination limit')
    flagged = {'OUT', 'DAY_TO_DAY', 'INJURY_RESERVE', 'SUSPENSION'}
    groups = []
    for tid, t in sorted(teams.items(), key=lambda item: item[1].get('abbrev', '')):
        injured = [{k: p[k] for k in ('id', 'name', 'injury', 'ownerTeamId', 'availability', 'eligibleSlots')}
                   for p in players if p['nbaTeamId'] == tid and p['injury'] in flagged]
        groups.append({'nbaTeamId': tid, 'team': t.get('abbrev'), 'injuryFlags': injured})
    packet = {'fetchedAt': utc_now(), 'season': args.season, 'leagueId': args.league,
              'scoringPeriodId': period,
              'transactionScoringPeriod': league['status'].get('transactionScoringPeriod', period),
              'teams': groups, 'players': players, 'sources': c.sources,
              'limitations': ['Flags describe ESPN status at retrieval, not confirmed availability for future games.',
                              'Current NBA membership, starter roles and beneficiaries require dated news/box-score verification.',
                              'Legacy entries may retain stale team IDs/flags. No automatic minutes adjustment.',
                              'No offensive rating, defensive rating or pace endpoint is integrated.']}
    output.write_text(json.dumps(packet, indent=2))
    print(json.dumps({'state': 'read_only_completed', 'output': str(output),
                      'teams': len(groups), 'players': len(players),
                      'injuryFlagCount': sum(len(g['injuryFlags']) for g in groups)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--season', type=int, required=True, help='ESPN season ending year')
    parser.add_argument('--league', type=int, default=30695)
    parser.add_argument('--output', required=True, help='Normalized JSON output path')
    args = parser.parse_args()
    try:
        collect(args)
    except (KeyError, RuntimeError, OSError, ValueError) as exc:
        # Never emit request headers, environment values or raw responses.
        print(json.dumps({'state': 'failed', 'errorType': type(exc).__name__}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
