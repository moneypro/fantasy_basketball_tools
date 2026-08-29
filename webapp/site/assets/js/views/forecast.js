import { api } from '../api.js';
import {
  el, mount, block, tableWrap, skeletonTable, errorState, emptyState,
  round0, signed, sortableTh, applySort, injuryChips,
  projectionScale, projectionCell, projectionLegend, weekStepper, relativeTime
} from '../ui.js';
import { predictionScaffold } from '../scaffold.js';

const COLUMNS = [
  { key: 'teamName', label: 'Team', numeric: false },
  { key: 'games', label: '# of games', numeric: true },
  { key: 'mean', label: 'Projected', numeric: false },
  { key: 'meanWithDtd', label: 'With day-to-day', numeric: true }
];

const ACCESSORS = {
  teamName: (t) => t.teamName || '',
  games: (t) => t.games,
  mean: (t) => t.mean,
  meanWithDtd: (t) => t.meanWithDtd
};

export function forecastHero(league, week) {
  const method =
    'Each day the model takes the nine highest-scoring available players on a roster and adds up their means and variances, ' +
    'then carries that total through to Sunday.';

  // With no league loaded, say nothing about whether the season is running.
  if (!league) return { title: 'Forecast', lede: method };

  return {
    title: `Week ${week} forecast`,
    lede:
      `${method} ` +
      (league.seasonComplete
        ? 'The season is over, so these are the projections as they stood going into the week.'
        : 'Numbers refresh as injuries and schedules change.')
  };
}

export async function renderForecast(root, ctx) {
  let sort = { key: 'mean', dir: 'desc' };
  const week = ctx.week;

  const toolbar = el(
    'div',
    { class: 'toolbar' },
    weekStepper(week, ctx.minWeek, ctx.maxWeek, (w) => ctx.setWeek(w)),
    el('span', { class: 'block__note', id: 'forecastMeta', text: 'Loading forecast…' })
  );

  mount(root, toolbar, block(`Week ${week} projection`, 'Loading', skeletonTable(12, 5)));

  let data;
  try {
    data = await api.forecast(week);
  } catch (err) {
    mount(
      root,
      toolbar,
      block(`Week ${week} projection`, null, errorState(err, () => ctx.reload())),
      predictionScaffold(week, ctx.maxWeek)
    );
    toolbar.querySelector('#forecastMeta').textContent = 'Forecast unavailable';
    return;
  }

  const teams = Array.isArray(data.teams) ? data.teams : [];

  const generated = relativeTime(data.generatedAt);
  toolbar.querySelector('#forecastMeta').textContent = generated
    ? `Generated ${generated}`
    : `${teams.length} teams`;

  if (!teams.length) {
    mount(
      root,
      toolbar,
      block(
        `Week ${week} projection`,
        null,
        emptyState(
          `No forecast for week ${week}`,
          'Nothing has been generated for this week. Pick another week from the selector above.'
        )
      ),
      predictionScaffold(week, ctx.maxWeek)
    );
    return;
  }

  const scale = projectionScale(teams);

  const projBlock = el('div');
  const daysBlock = el('div');

  /* ---------------------------------------------------- day column model */

  let dayNames = [];
  for (const t of teams) {
    const days = Array.isArray(t.remainingDays) ? t.remainingDays : [];
    if (days.length > dayNames.length) dayNames = days.map((d) => d.day);
  }

  const dayLookup = new Map();
  for (const t of teams) {
    const map = new Map();
    for (const d of Array.isArray(t.remainingDays) ? t.remainingDays : []) map.set(d.day, d);
    dayLookup.set(t.teamId, map);
  }

  /* ------------------------------------------------------------- drawing */

  const drawProjection = (rows) => {
    const thead = el(
      'thead',
      null,
      el(
        'tr',
        null,
        el('th', { scope: 'col', class: 'col-rank', text: '#' }),
        ...COLUMNS.map((c) => {
          const th = sortableTh(c, sort, onSort);
          if (c.key === 'teamName') th.classList.add('col-team');
          return th;
        }),
        el('th', { scope: 'col', text: 'Injuries' })
      )
    );

    const tbody = el(
      'tbody',
      null,
      ...rows.map((t, i) => {
        const gap = typeof t.meanWithDtd === 'number' && typeof t.mean === 'number' ? t.meanWithDtd - t.mean : 0;
        return el(
          'tr',
          null,
          el('td', { class: 'col-rank', text: String(i + 1) }),
          el(
            'th',
            { scope: 'row', class: 'col-team' },
            el('span', { class: 'teamname', text: t.teamName || '—' })
          ),
          el('td', { class: 'num dim', text: t.games != null ? String(t.games) : '—' }),
          el('td', null, projectionCell(t, scale, i)),
          el(
            'td',
            { class: 'num' },
            el('span', { text: round0(t.meanWithDtd) }),
            el('span', { class: 'dim', text: ` ± ${round0(t.stdDevWithDtd)}` }),
            Math.round(gap) > 0
              ? el('span', { style: { color: 'var(--flag)' }, text: `  ${signed(gap)}` })
              : null
          ),
          el('td', null, injuryChips(t.injuries))
        );
      })
    );

    mount(
      projBlock,
      tableWrap(el('table', { class: 'grid grid--sticky' }, thead, tbody), `Week ${week} projection`),
      projectionLegend()
    );
  };

  const drawDays = (rows) => {
    if (!dayNames.length) {
      mount(daysBlock, emptyState('No day-by-day breakdown', 'This forecast did not include a remaining-days split.'));
      return;
    }

    const thead = el(
      'thead',
      null,
      el(
        'tr',
        null,
        el('th', { scope: 'col', class: 'col-rank', text: '#' }),
        el('th', { scope: 'col', class: 'col-team', text: 'Team' }),
        ...dayNames.map((d) => el('th', { scope: 'col', class: 'th-num', text: d }))
      )
    );

    const tbody = el(
      'tbody',
      null,
      ...rows.map((t, i) => {
        const map = dayLookup.get(t.teamId) || new Map();
        return el(
          'tr',
          null,
          el('td', { class: 'col-rank', text: String(i + 1) }),
          el(
            'th',
            { scope: 'row', class: 'col-team' },
            el('span', { class: 'teamname', text: t.teamName || '—' })
          ),
          ...dayNames.map((name) => {
            const d = map.get(name);
            if (!d) return el('td', { class: 'num dim-2', text: '—' });
            return el(
              'td',
              { class: 'num' },
              el('span', { text: round0(d.mean) }),
              el('span', { class: 'dim-2', text: ` ± ${round0(d.stdDev)}` })
            );
          })
        );
      })
    );

    const table = el(
      'table',
      { class: 'grid grid--sticky' },
      el('caption', { text: 'Each column is the projected total from that day through the end of the week.' }),
      thead,
      tbody
    );

    mount(daysBlock, tableWrap(table, `Week ${week} remaining days`));
  };

  const drawAll = () => {
    const rows = applySort(teams, sort, ACCESSORS);
    drawProjection(rows);
    drawDays(rows);
  };

  function onSort(key) {
    if (sort.key === key) sort = { key, dir: sort.dir === 'asc' ? 'desc' : 'asc' };
    else sort = { key, dir: key === 'teamName' ? 'asc' : 'desc' };
    drawAll();
  }

  drawAll();

  mount(
    root,
    toolbar,
    block(`Week ${week} projection`, 'Sorted by projected points — click any heading to re-sort', projBlock),
    block('Remaining days, cumulative', 'Same order as above', daysBlock),
    predictionScaffold(week, ctx.maxWeek)
  );
}
