"""Auditable player tables; live remainder is a clock-based heuristic, not ESPN odds."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pickup_report import box_points, PACIFIC


def remaining_fraction(status):
    if status.get('type', {}).get('state') == 'post':
        return 0.0
    period = status.get('period')
    if not isinstance(period, int) or period < 1 or period > 4:
        return None  # Overtime needs a separate model, not a zero projection.
    try:
        clock = status.get('clock')
        if clock is None:
            parts = status['displayClock'].split(':')
            clock = sum(float(v) * 60 ** i for i, v in enumerate(reversed(parts)))
        if not 0 <= float(clock) <= 720:
            return None
        return ((4 - period) * 720 + float(clock)) / 2880
    except (KeyError, TypeError, ValueError):
        return None


def surname(name):
    words = name.split()
    suffix = words.pop() if words[-1] in ('Jr.', 'Jr', 'Sr.', 'II', 'III', 'IV') else ''
    last = words.pop()
    while words and words[-1].lower() in ('da', 'de', 'del', 'van', 'von'):
        last = words.pop() + ' ' + last
    return last + (' ' + suffix if suffix else '')


def fetch_boxes(c, board, roster_ids, nonce):
    def fetch(event):
        data = c.get('box_' + event['id'],
                     'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event='
                     + event['id'] + '&_=' + nonce, optional=True)
        if data is None:
            return event['id'], {'status': event['status'], 'players': {}}
        status = data.get('header', {}).get('competitions', [{}])[0].get('status', event['status'])
        players = {}
        for team in data.get('boxscore', {}).get('players', []):
            for group in team.get('statistics', []):
                for athlete in group.get('athletes', []):
                    pid = str(athlete['athlete']['id'])
                    if pid in roster_ids:
                        players[pid] = {'stats': dict(zip(group['labels'], athlete.get('stats', []))),
                                        'didNotPlay': athlete.get('didNotPlay', False)}
        return event['id'], {'status': status, 'players': players}
    with ThreadPoolExecutor(max_workers=4) as pool:
        return dict(pool.map(fetch, board.get('events', [])))


def build_tables(packet, schedule, boxes, weights, no_return=None):
    """Use saved starters today; future optimized selections are labeled hypothetical."""
    no_return = no_return or {}
    result = {'teams': {}, 'comparisons': {}, 'method':
              'Expected = baseline FP/game for unstarted games; baseline × regulation time remaining / 48 minutes for live games. Normal rotations assumed. No automatic matchup, foul, blowout, or minutes-limit adjustment.'}
    for tid, team in packet['teams'].items():
        rows = []
        names = Counter(surname(p['name']) for p in team['roster'])
        for day in team['models']['seasonBaseline']['includingDTD']['days']:
            period = day['period']
            today = period == packet['currentScoringPeriod']
            selected = {p['id'] for p in day['players']}
            for p in team['roster']:
                game = schedule.get(period, {}).get(p['nbaTeamId'])
                if not game or p['slot'] in (13, 14):
                    continue
                # Current bench points never count. Future assignments may be optimized.
                if (today and p['slot'] >= 12) or (not today and p['id'] not in selected):
                    continue
                state = game['state'] if today else 'pre'
                box = boxes.get(game['eventId'], {}) if today else {}
                status = box.get('status', {})
                state = status.get('type', {}).get('state', state)
                line = box.get('players', {}).get(str(p['id']))
                out = p['injury'] in ('OUT', 'INJURY_RESERVE', 'SUSPENSION')
                stopped = today and str(p['id']) in no_return
                current = None if state == 'pre' else (
                    box_points(line['stats'], weights) if line and not line['didNotPlay']
                    else 0.0 if out or (line and line['didNotPlay']) else None)
                fraction = 0.0 if out or stopped or state == 'post' else (
                    1.0 if state == 'pre' else remaining_fraction(status))
                expected = {method: (0.0 if fraction == 0 else
                            p[method] * fraction if p[method] is not None and fraction is not None else None)
                            for method in ('seasonBaseline', 'recentBlend')}
                label = surname(p['name'])
                if names[label] > 1:
                    label = p['name'][0] + '. ' + label
                rows.append({'name': p['name'], 'lastName': label, 'playerId': p['id'],
                             'date': ', '.join(day['date']), 'today': today, 'state': state,
                             'current': current, 'expected': expected, 'fractionRemaining': fraction,
                             'baseline': p['seasonBaseline'], 'baselineSource': p['baselineSource'],
                             'status': 'Out for game' if stopped else 'Out' if out else
                             status.get('type', {}).get('shortDetail', 'Not started'),
                             'evidence': no_return.get(str(p['id'])),
                             'hypothetical': not today})
        current_rows = [r for r in rows if r['today'] and r['state'] != 'pre']
        current_sum = sum(r['current'] for r in current_rows) if all(r['current'] is not None for r in current_rows) else None
        models = {}
        for method in ('seasonBaseline', 'recentBlend'):
            missing = any(d['missingBaselines'] for d in team['models'][method]['includingDTD']['days'])
            remaining = sum(r['expected'][method] for r in rows) if not missing and all(r['expected'][method] is not None for r in rows) else None
            models[method] = {'remaining': remaining,
                              'final': team['liveScore'] + remaining if remaining is not None else None}
        result['teams'][tid] = {'rows': rows, 'currentSubtotal': current_sum, 'models': models}
    for method in ('seasonBaseline', 'recentBlend'):
        yours = result['teams'][str(packet['teamId'])]['models'][method]['final']
        theirs = result['teams'][str(packet['opponentId'])]['models'][method]['final']
        result['comparisons'][method] = yours - theirs if yours is not None and theirs is not None else None
    return result


def render_markdown(packet):
    tables = packet['playerTables']
    yours, theirs = str(packet['teamId']), str(packet['opponentId'])
    fmt = lambda value: 'Unknown' if value is None else f'{value:.1f}'
    stamp = datetime.fromisoformat(packet['fetchedAt']).astimezone(PACIFIC).strftime('%Y-%m-%d %H:%M:%S %Z')
    lines = [f"Fetched {stamp}. Matchup ends {', '.join(packet['endDates'])}.", '',
             f"Current score: {packet['teams'][yours]['name']} {fmt(packet['teams'][yours]['liveScore'])} – "
             f"{fmt(packet['teams'][theirs]['liveScore'])} {packet['teams'][theirs]['name']}.", '',
             'Expected = points still to come. Current = points earned in the listed game.', '']
    for tid in (yours, theirs):
        team, tab = packet['teams'][tid], tables['teams'][tid]
        lines += [f"**{team['name']}**", '', '| Last Name | Expected | Current |', '|---|---:|---:|']
        for r in tab['rows']:
            label = r['lastName'] + (f" ({r['date']}; hypothetical)" if not r['today'] else '')
            actual = 'Not started' if r['state'] == 'pre' and r['status'] != 'Out' else fmt(r['current']) + ' — ' + r['status']
            if r['status'] == 'Out' and r['state'] == 'pre':
                actual = 'Not started — Out'
            lines.append(f"| {label} | {fmt(r['expected']['seasonBaseline'])} | {actual} |")
        lines += [f"| **Total** | **{fmt(tab['models']['seasonBaseline']['remaining'])}** | **{fmt(tab['currentSubtotal'])}** |", '']
    lines += ['**Projected finish**', '']
    for tid in (yours, theirs):
        model = tables['teams'][tid]['models']['seasonBaseline']
        lines.append(f"- {packet['teams'][tid]['name']}: {fmt(packet['teams'][tid]['liveScore'])} + {fmt(model['remaining'])} = **{fmt(model['final'])}**")
    for method, label in [('seasonBaseline', 'Projected margin'), ('recentBlend', 'Recent-blend margin')]:
        value = tables['comparisons'][method]
        lines.append(f"- {label} (you − opponent): **{value:+.1f}**" if value is not None else f'- {label}: **Partial; missing estimates**')
    notes = set()
    for tab in tables['teams'].values():
        for row in tab['rows']:
            if row['baselineSource'] != 'season projection':
                notes.add(f"{row['name']}: {row['baselineSource']}.")
            if row['evidence']:
                notes.add(f"{row['name']}: {row['evidence']['reason']} ([source]({row['evidence']['source']})).")
    lines += ['', *sorted(notes)]
    lines += ['', tables['method'], 'Current points are already in the weekly score; they are not added twice. Totals use unrounded values.',
              'Today uses saved active players. Future selections assume optimized legal lineups. Confirm in-game injuries; the feed may lag.']
    return '\n'.join(lines) + '\n'
