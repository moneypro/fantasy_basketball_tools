import { api } from '../api.js';
import {
  el, mount, block, skeletonCards, errorState, emptyState,
  round0, round1, signed, weekStepper
} from '../ui.js';

export function scoreboardHero(league, week) {
  if (!league) {
    return { title: 'Scoreboard', lede: 'Matchup scores next to the projection each team carried into the week.' };
  }
  return {
    title: `Week ${week} scoreboard`,
    lede: league.seasonComplete
      ? 'Final results for the week, next to the projection each team carried into it.'
      : 'Live totals for the week, next to what the model projects each team finishes on.'
  };
}

function side(team, opponent, isFinal) {
  const score = typeof team.score === 'number' ? team.score : null;
  const other = typeof opponent.score === 'number' ? opponent.score : null;
  const winner = score !== null && other !== null && score > other;
  const loser = score !== null && other !== null && score < other;

  return el(
    'div',
    { class: `side${winner ? ' side--winner' : ''}${loser ? ' side--loser' : ''}` },
    el('span', { class: 'side__name', text: team.teamName || '—' }),
    el('span', { class: 'side__score', text: score === null ? '—' : round1(score) }),
    el(
      'span',
      { class: 'side__proj' },
      isFinal ? 'projected ' : 'projected finish ',
      el('b', { text: round0(team.projected) }),
      typeof team.projected === 'number' && score !== null
        ? `  ·  ${signed(score - team.projected)} vs projection`
        : ''
    )
  );
}

function matchupCard(m, isFinal, index) {
  const home = m.home || {};
  const away = m.away || {};
  const hs = typeof home.score === 'number' ? home.score : null;
  const as = typeof away.score === 'number' ? away.score : null;
  const margin = hs !== null && as !== null ? Math.abs(hs - as) : null;

  const leader = hs === null || as === null ? null : hs > as ? home.teamName : as > hs ? away.teamName : null;

  const projMargin =
    typeof home.projected === 'number' && typeof away.projected === 'number'
      ? home.projected - away.projected
      : null;

  return el(
    'article',
    { class: 'card' },
    el(
      'div',
      { class: 'card__head' },
      el('span', { text: `Matchup ${index + 1}` }),
      el('span', { class: `tag ${isFinal ? 'tag--final' : 'tag--live'}`, text: isFinal ? 'Final' : 'In progress' })
    ),
    side(home, away, isFinal),
    side(away, home, isFinal),
    el(
      'div',
      { class: 'card__foot' },
      el(
        'span',
        null,
        margin === null
          ? 'No score yet'
          : leader
            ? [isFinal ? 'Won by ' : 'Leading by ', el('span', { class: 'delta', text: round1(margin) })]
            : 'Level'
      ),
      el(
        'span',
        null,
        projMargin === null
          ? ''
          : `model had ${projMargin >= 0 ? home.teamName : away.teamName} ${signed(Math.abs(projMargin))}`
      )
    )
  );
}

export async function renderScoreboard(root, ctx) {
  const week = ctx.week;
  const isFinal = !!(ctx.league && ctx.league.seasonComplete);

  const toolbar = el(
    'div',
    { class: 'toolbar' },
    weekStepper(week, ctx.minWeek, ctx.maxWeek, (w) => ctx.setWeek(w)),
    el('span', { class: 'block__note', id: 'sbMeta', text: 'Loading matchups…' })
  );

  mount(root, toolbar, block(`Week ${week} matchups`, 'Loading', skeletonCards(6)));

  let data;
  try {
    data = await api.scoreboard(week);
  } catch (err) {
    mount(root, toolbar, block(`Week ${week} matchups`, null, errorState(err, () => ctx.reload())));
    toolbar.querySelector('#sbMeta').textContent = 'Scoreboard unavailable';
    return;
  }

  const matchups = Array.isArray(data.matchups) ? data.matchups : [];
  toolbar.querySelector('#sbMeta').textContent = matchups.length
    ? `${matchups.length} matchups · scores against projection`
    : 'No matchups';

  if (!matchups.length) {
    mount(
      root,
      toolbar,
      block(
        `Week ${week} matchups`,
        null,
        emptyState(`No matchups for week ${week}`, 'This week has no schedule on file. Try another week.')
      )
    );
    return;
  }

  mount(
    root,
    toolbar,
    block(
      `Week ${week} matchups`,
      isFinal ? 'Season complete — final scores' : 'Scores update through the week',
      el('div', { class: 'cards' }, ...matchups.map((m, i) => matchupCard(m, isFinal, i)))
    )
  );
}
