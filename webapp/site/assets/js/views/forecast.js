import { api } from '../api.js';
import {
  el, mount, block, tableWrap, skeletonTable, errorState, emptyState,
  round0, signed, sortableTh, applySort, injuryMarks,
  projectionScale, intervalBar, projectionLegend, weekChips, relativeTime
} from '../ui.js';
import { predictionScaffold } from '../scaffold.js';

const COLUMNS = [
  { key: 'teamName', label: 'Team', numeric: false },
  { key: 'games', label: 'G', numeric: true },
  { key: 'mean', label: 'Projected', numeric: true },
  { key: 'meanWithDtd', label: 'With DTD', numeric: true }
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

  if (!league) return { title: 'Forecast', lede: method };

  return {
    title: `Week ${week} forecast`,
    numeral: String(week).padStart(2, '0'),
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

  const chips = weekChips(week, ctx.minWeek, ctx.maxWeek, (w) => ctx.setWeek(w));

  const toolbar = el(
    'div',
    { class: 'toolbar' },
    chips,
    el('span', { class: 'block__note', id: 'forecastMeta', text: 'Loading forecast…' })
  );

  mount(root, toolbar, block(`Week ${week} board`, 'Loading', skeletonTable(12, 6)));

  const current = chips.querySelector('.weekchip[aria-current="true"]');
  if (current) current.scrollIntoView({ block: 'nearest', inline: 'center' });

  let data;
  try {
    data = await api.forecast(week);
  } catch (err) {
    mount(
      root,
      toolbar,
      block(`Week ${week} board`, null, errorState(err, () => ctx.reload())),
      predictionScaffold(week, ctx.maxWeek)
    );
    toolbar.querySelector('#forecastMeta').textContent = 'Forecast unavailable';
    return;
  }

  const teams = Array.isArray(data.teams) ? data.teams : [];

  const generated = relativeTime(data.generatedAt);
  toolbar.querySelector('#forecastMeta').textContent = generated
    ? `Generated ${generated} · sorted by projected points`
    : `${teams.length} teams · sorted by projected points`;

  if (!teams.length) {
    mount(
      root,
      toolbar,
      block(
        `Week ${week} board`,
        null,
        emptyState(
          `No forecast for week ${week}`,
          'Nothing has been generated for this week. Pick another week from the strip above.'
        )
      ),
      predictionScaffold(week, ctx.maxWeek)
    );
    return;
  }

  const scale = projectionScale(teams);

  // Desktop table and mobile list live in separate sub-containers inside the
  // same board block; CSS shows one or the other by viewport width.
  const desktopWrap = el('div', { class: 'fboard-desktop' });
  const mobileWrap = el('div', { class: 'fboard-mobile' });
  const boardBlock = el('div', null, desktopWrap, mobileWrap);
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

  /* ------------------------------------------------------ desktop table */

  const drawDesktop = (rows) => {
    const thead = el(
      'thead',
      null,
      el(
        'tr',
        null,
        el('th', { scope: 'col', class: 'col-rank', text: 'Rk' }),
        ...COLUMNS.map((c, i) => {
          const th = sortableTh(c, sort, onSort);
          if (c.key === 'teamName') th.classList.add('col-team');
          if (i === 2) th.setAttribute('colspan', '2'); // Projected number + range bar
          return th;
        }),
        el('th', { scope: 'col', text: 'Unavailable' })
      )
    );

    const tbody = el(
      'tbody',
      null,
      ...rows.map((t, i) => {
        const gap = typeof t.meanWithDtd === 'number' && typeof t.mean === 'number' ? t.meanWithDtd - t.mean : 0;
        const hasDelta = Math.round(gap) > 0;
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
          el(
            'td',
            { class: 'proj' },
            el('span', { class: 'proj__val', text: round0(t.mean) }),
            el('span', { class: 'proj__sd', text: ` ± ${round0(t.stdDev)}` })
          ),
          el('td', null, intervalBar(t.mean, t.stdDev, scale, i)),
          el(
            'td',
            { class: 'num', style: { whiteSpace: 'nowrap' } },
            el('span', { class: 'dtdval', text: round0(t.meanWithDtd) }),
            hasDelta ? el('span', { class: 'dtddelta', text: `  ${signed(gap)}` }) : null
          ),
          el('td', null, injuryMarks(t.injuries))
        );
      })
    );

    mount(
      desktopWrap,
      tableWrap(el('table', { class: 'grid grid--sticky' }, thead, tbody), `Week ${week} forecast board`),
      projectionLegend()
    );
  };

  /* ------------------------------------------------------- mobile board */

  const drawMobile = (rows) => {
    const list = el(
      'div',
      { class: 'fboard-mobile__list' },
      ...rows.map((t, i) => {
        const gap = typeof t.meanWithDtd === 'number' && typeof t.mean === 'number' ? t.meanWithDtd - t.mean : 0;
        const hasDelta = Math.round(gap) > 0;
        return el(
          'div',
          { class: 'fboard-mobile__row' },
          el('span', { class: 'fboard-mobile__rank', text: String(i + 1) }),
          el(
            'div',
            { class: 'fboard-mobile__mid' },
            el('div', { class: 'fboard-mobile__name', text: t.teamName || '—' }),
            el(
              'div',
              { class: 'fboard-mobile__barrow' },
              el('span', { class: 'fboard-mobile__games', text: `${t.games != null ? t.games : '—'}g` }),
              intervalBar(t.mean, t.stdDev, scale, i, true)
            )
          ),
          el(
            'div',
            { class: 'fboard-mobile__stat' },
            el(
              'div',
              null,
              el('span', { class: 'proj__val', text: round0(t.mean) }),
              el('span', { class: 'proj__sd', text: ` ±${round0(t.stdDev)}` })
            ),
            hasDelta ? el('div', { class: 'fboard-mobile__delta', text: `${signed(gap)} w/ DTD` }) : null
          )
        );
      })
    );

    mount(
      mobileWrap,
      el(
        'div',
        { class: 'fboard-mobile__head' },
        el('span', { text: 'Team' }),
        el('span', { text: 'Projected ▼' })
      ),
      list,
      el('p', {
        class: 'fboard-mobile__note',
        text: 'The day-by-day split is further down the page. Read-only — everyone sees the same board.'
      })
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
    drawDesktop(rows);
    drawMobile(rows);
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
    block(
      `Week ${week} board`,
      'Sorted by projected points — click any heading to re-sort',
      boardBlock
    ),
    block('Remaining days, cumulative', 'Same order as above', daysBlock),
    predictionScaffold(week, ctx.maxWeek)
  );
}
