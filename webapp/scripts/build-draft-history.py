#!/usr/bin/env python3
"""Refresh sanitized draft snapshots using env credentials or AWS Secrets Manager.

Run from the repo root: python3 webapp/scripts/build-draft-history.py
Only public player/team analysis is written. ESPN cookies stay in memory.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from draft_recap.history import season_recap


def fetch(creds, year, views, filters=None):
    base = 'https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/'
    league_id = int(creds['LEAGUE_ID'])
    path = f'seasons/{year}/segments/0/leagues/{league_id}' if year >= 2018 else f'leagueHistory/{league_id}'
    params = [('view', v) for v in views]
    if year < 2018:
        params.append(('seasonId', year))
    headers = {'Cookie': f"espn_s2={creds['ESPN_S2']}; SWID={creds['SWID']}"}
    if filters:
        headers['x-fantasy-filter'] = json.dumps(filters)
    req = urllib.request.Request(base + path + '?' + urllib.parse.urlencode(params), headers=headers)
    with urllib.request.urlopen(req, timeout=45) as response:
        data = json.load(response)
    return data[0] if isinstance(data, list) else data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--season', type=int, default=2026, help='Latest ESPN season (ending year)')
    args = parser.parse_args()
    creds = {k: os.environ.get(k) for k in ('ESPN_S2', 'SWID', 'LEAGUE_ID')}
    if not all(creds.values()):
        creds = json.loads(subprocess.check_output([
            'aws', 'secretsmanager', 'get-secret-value', '--secret-id',
            os.environ.get('ESPN_SECRET_NAME', 'fantasy-basketball/espn'),
            '--region', os.environ.get('AWS_REGION', 'us-west-2'),
            '--query', 'SecretString', '--output', 'text',
        ]))
    current = fetch(creds, args.season, ['mSettings', 'mTeam', 'mDraftDetail'])
    years = sorted(set(current['status'].get('previousSeasons', []) + [args.season]), reverse=True)
    benchmark = current['settings']['scoringSettings']['scoringItems']
    if current['settings']['scoringSettings']['scoringType'] != 'H2H_POINTS':
        raise RuntimeError('Latest season must have points scoring for the historical benchmark')
    output = ROOT / 'webapp/site/data/draft'
    output.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).isoformat()
    recaps = []
    for year in years:
        league = current if year == args.season else fetch(creds, year, ['mSettings', 'mTeam', 'mDraftDetail'])
        ids = sorted({p['playerId'] for p in league.get('draftDetail', {}).get('picks', [])})
        players = []
        # Batching avoids oversized filter headers in leagues with large drafts.
        for start in range(0, len(ids), 80):
            filters = {'players': {'filterIds': {'value': ids[start:start + 80]},
                       'filterStatsForTopScoringPeriodIds': {'value': league['status']['finalScoringPeriod'],
                                                           'additionalValue': [f'00{year}', f'10{year}']}}}
            players.extend(fetch(creds, year, ['kona_playercard'], filters).get('players', []))
        recap = season_recap(year, league, players, benchmark)
        recap.update(generatedAt=generated, benchmarkSeason=args.season)
        recaps.append(recap)
        print(f"{year}: {len(ids)} picks, {recap['missingPlayers']} missing player totals", flush=True)
    # Fetch every season successfully before replacing any published snapshots.
    for recap in recaps:
        (output / f"{recap['season']}.json").write_text(json.dumps(recap, ensure_ascii=False, separators=(',', ':')) + '\n')
    manifest = {'generatedAt': generated, 'firstSeason': min(years), 'latestSeason': max(years),
                'seasons': [{k: r[k] for k in ('season', 'seasonComplete', 'draftAvailable', 'missingPlayers', 'benchmarkScoring')} for r in recaps]}
    (output / 'index.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
