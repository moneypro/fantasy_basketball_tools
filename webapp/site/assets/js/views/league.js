import { api } from '../api.js';
import {
  el, mount, block, tableWrap, skeletonTable, errorState, emptyState,
  round1, signed, pct3, sortableTh, applySort
} from '../ui.js';

const COLUMNS = [
  { key: 'standing', label: '#', numeric: true },
  { key: 'teamName', label: 'Team', numeric: false },
  { key: 'wins', label: 'W', numeric: true },
  { key: 'losses', label: 'L', numeric: true },
  { key: 'pct', label: 'Pct', numeric: true },
  { key: 'pointsFor', label: 'Points for', numeric: true },
  { key: 'pointsAgainst', label: 'Points against', numeric: true },
  { key: 'diff', label: 'Diff', numeric: true }
];

const ACCESSORS = {
  standing: (t) => t.standing,
  teamName: (t) => t.teamName || '',
  wins: (t) => t.wins,
  losses: (t) => t.losses,
  pct: (t) => ((t.wins || 0) + (t.losses || 0) ? (t.wins || 0) / ((t.wins || 0) + (t.losses || 0)) : 0),
  pointsFor: (t) => t.pointsFor,
  pointsAgainst: (t) => t.pointsAgainst,
  diff: (t) => (t.pointsFor || 0) - (t.pointsAgainst || 0)
};

export function leagueHero(league) {
  return {
    title: 'Standings',
    lede: league && league.seasonComplete
      ? 'Final table for the season. Records, points scored and points conceded across every matchup week.'
      : 'Records, points scored and points conceded across the season.'
  };
}

export async function renderLeague(root, ctx) {
  let sort = { key: 'standing', dir: 'asc' };

  mount(root, block('Standings', 'Loading', skeletonTable(12, 6)));

  let data;
  try {
    data = await api.league();
  } catch (err) {
    mount(root, block('Standings', null, errorState(err, () => ctx.reload())));
    return;
  }

  const teams = Array.isArray(data.teams) ? data.teams : [];
  if (!teams.length) {
    mount(root, block('Standings', null, emptyState('No teams yet', 'The league has no teams to show. Once the season is set up the table fills in here.')));
    return;
  }

  const container = el('div');

  const draw = () => {
    const rows = applySort(teams, sort, ACCESSORS);

    const thead = el('thead', null, el('tr', null, ...COLUMNS.map((c) => sortableTh(c, sort, onSort))));

    const tbody = el(
      'tbody',
      null,
      ...rows.map((t) => {
        const diff = (t.pointsFor || 0) - (t.pointsAgainst || 0);
        return el(
          'tr',
          null,
          el('td', { class: 'col-rank', text: t.standing != null ? String(t.standing) : '—' }),
          el(
            'th',
            { scope: 'row', class: 'col-team' },
            el('span', { class: 'teamname', text: t.teamName || '—' }),
            t.abbrev ? el('span', { class: 'teamabbr', text: t.abbrev }) : null
          ),
          el('td', { class: 'num num--lead', text: t.wins != null ? String(t.wins) : '—' }),
          el('td', { class: 'num dim', text: t.losses != null ? String(t.losses) : '—' }),
          el('td', { class: 'num dim', text: pct3(t.wins, t.losses) }),
          el('td', { class: 'num num--lead', text: round1(t.pointsFor) }),
          el('td', { class: 'num dim', text: round1(t.pointsAgainst) }),
          el('td', {
            class: 'num',
            style: { color: diff >= 0 ? 'var(--leather)' : 'var(--muted)' },
            text: signed(diff)
          })
        );
      })
    );

    const table = el('table', { class: 'grid grid--sticky' }, thead, tbody);
    mount(container, tableWrap(table, 'League standings', true));
  };

  function onSort(key) {
    const numericDefaultDesc = key !== 'standing' && key !== 'teamName' && key !== 'losses' && key !== 'pointsAgainst';
    if (sort.key === key) sort = { key, dir: sort.dir === 'asc' ? 'desc' : 'asc' };
    else sort = { key, dir: numericDefaultDesc ? 'desc' : 'asc' };
    draw();
  }

  draw();

  mount(
    root,
    block(
      'Standings',
      `${teams.length} teams · sort by any column`,
      container
    )
  );
}
