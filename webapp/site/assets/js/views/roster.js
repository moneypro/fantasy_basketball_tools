import { api } from '../api.js';
import {
  el, mount, block, tableWrap, skeletonTable, errorState, emptyState,
  round1, sortableTh, applySort
} from '../ui.js';
import { rosterScaffold } from '../scaffold.js';

const BENCH_SLOTS = new Set(['BE', 'BENCH', 'IR', 'INJURY_RESERVE']);

const COLUMNS = [
  { key: 'name', label: 'Player', numeric: false },
  { key: 'position', label: 'Pos', numeric: false },
  { key: 'proTeam', label: 'Pro team', numeric: false },
  { key: 'injuryStatus', label: 'Status', numeric: false },
  { key: 'avgPoints', label: 'Avg', numeric: true },
  { key: 'totalPoints', label: 'Total', numeric: true }
];

const ACCESSORS = {
  slot: (p) => (BENCH_SLOTS.has(p.lineupSlot) ? 1 : 0),
  name: (p) => p.name || '',
  position: (p) => p.position || '',
  proTeam: (p) => p.proTeam || '',
  injuryStatus: (p) => p.injuryStatus || '',
  avgPoints: (p) => p.avgPoints,
  totalPoints: (p) => p.totalPoints
};

export function rosterHero(league) {
  return {
    title: 'Rosters',
    lede: league && league.seasonComplete
      ? 'End-of-season rosters: who was on each team, where they slotted, and what they averaged.'
      : 'Who is on each team, where they slot in, and what they average.'
  };
}

function statusCell(status) {
  const s = String(status || 'ACTIVE').toUpperCase();
  if (s === 'ACTIVE' || s === 'NORMAL' || s === '') {
    return el('span', { class: 'dim-2', text: 'Active' });
  }
  if (s === 'OUT') return el('span', { class: 'chip chip--out', text: 'Out' });
  if (s === 'DAY_TO_DAY') return el('span', { class: 'chip chip--dtd', text: 'Day to day' });
  return el('span', { class: 'chip chip--dtd', text: s.replace(/_/g, ' ').toLowerCase() });
}

export async function renderRoster(root, ctx) {
  let sort = { key: 'slot', dir: 'asc' };

  const teams = (ctx.league && Array.isArray(ctx.league.teams) ? ctx.league.teams : []).slice();
  const teamId = ctx.teamId != null ? ctx.teamId : teams.length ? teams[0].teamId : null;

  const picker = el('select', {
    class: 'select',
    id: 'teamSelect',
    'aria-label': 'Team',
    on: { change: (e) => ctx.setTeam(Number(e.target.value)) }
  });
  for (const t of teams) {
    picker.append(el('option', { value: String(t.teamId), selected: t.teamId === teamId, text: t.teamName }));
  }

  const toolbar = el(
    'div',
    { class: 'toolbar' },
    el(
      'div',
      { class: 'field' },
      el('label', { class: 'field__label', for: 'teamSelect', text: 'Team' }),
      picker
    ),
    el('span', { class: 'block__note', id: 'rosterMeta', text: 'Loading roster…' })
  );

  if (teamId == null) {
    mount(root, block('Roster', null, emptyState('No teams', 'The league has no teams, so there are no rosters to show.')));
    return;
  }

  mount(root, toolbar, block('Roster', 'Loading', skeletonTable(13, 6)));

  let data;
  try {
    data = await api.roster(teamId);
  } catch (err) {
    mount(
      root,
      toolbar,
      block('Roster', null, errorState(err, () => ctx.reload())),
      rosterScaffold([], (teams.find((t) => t.teamId === teamId) || {}).teamName)
    );
    toolbar.querySelector('#rosterMeta').textContent = 'Roster unavailable';
    return;
  }

  const players = Array.isArray(data.players) ? data.players : [];
  const teamName = data.teamName || (teams.find((t) => t.teamId === teamId) || {}).teamName || 'Team';

  toolbar.querySelector('#rosterMeta').textContent = players.length
    ? `${players.length} players · starters first`
    : 'Empty roster';

  if (!players.length) {
    mount(
      root,
      toolbar,
      block('Roster', null, emptyState(`${teamName} has no players on file`, 'Once the roster is published it appears here.')),
      rosterScaffold([], teamName)
    );
    return;
  }

  const container = el('div');

  const draw = () => {
    let rows = applySort(players, sort, ACCESSORS);
    if (sort.key === 'slot') {
      // Within starters and bench, order by scoring average.
      rows = rows.sort((a, b) => {
        const g = ACCESSORS.slot(a) - ACCESSORS.slot(b);
        if (g !== 0) return g;
        return (b.avgPoints || 0) - (a.avgPoints || 0);
      });
    }

    const thead = el(
      'thead',
      null,
      el(
        'tr',
        null,
        sortableTh({ key: 'slot', label: 'Slot', numeric: false }, sort, onSort),
        ...COLUMNS.map((c) => {
          const th = sortableTh(c, sort, onSort);
          if (c.key === 'name') th.classList.add('col-team');
          return th;
        })
      )
    );

    const tbody = el(
      'tbody',
      null,
      ...rows.map((p) => {
        const bench = BENCH_SLOTS.has(p.lineupSlot);
        return el(
          'tr',
          null,
          el('td', null, el('span', { class: `slot${bench ? ' slot--bench' : ''}`, text: p.lineupSlot || '—' })),
          el('th', { scope: 'row' }, el('span', { class: bench ? 'dim' : 'teamname', text: p.name || '—' })),
          el('td', { class: 'dim', text: p.position || '—' }),
          el('td', { class: 'dim-2', text: p.proTeam || '—' }),
          el('td', null, statusCell(p.injuryStatus)),
          el('td', { class: 'num num--lead', text: round1(p.avgPoints) }),
          el('td', { class: 'num dim', text: round1(p.totalPoints) })
        );
      })
    );

    mount(container, tableWrap(el('table', { class: 'grid' }, thead, tbody), `${teamName} roster`, true));
  };

  function onSort(key) {
    const desc = key === 'avgPoints' || key === 'totalPoints';
    if (sort.key === key) sort = { key, dir: sort.dir === 'asc' ? 'desc' : 'asc' };
    else sort = { key, dir: desc ? 'desc' : 'asc' };
    draw();
  }

  draw();

  mount(
    root,
    toolbar,
    block(teamName, `${players.length} players`, container),
    rosterScaffold(players, teamName)
  );
}
