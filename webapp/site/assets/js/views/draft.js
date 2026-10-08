import { api } from '../api.js';
import { el, mount, block, tableWrap, loadingState, emptyState, round1, signed, sortableTh, applySort } from '../ui.js';

const label = (year) => `${year - 1}–${String(year).slice(-2)}`;

export function draftHero(season) {
  return {
    title: 'Draft Recap',
    lede: `${season ? label(season) + ' · ' : ''}Who won the draft? Original picks, full-season points, steals and busts across the league’s history.`
  };
}

function playersTable(players, title, showTeam = false) {
  const headers = ['Player', ...(showTeam ? ['Team'] : []), 'Round', 'Pick', 'Points', 'Scoring rank', 'Value'];
  return tableWrap(el('table', { class: 'grid draft-players' },
    el('thead', null, el('tr', null, ...headers.map((h) => el('th', { scope: 'col', text: h })))),
    el('tbody', null, ...players.map((p) => el('tr', null,
      el('th', { scope: 'row', text: p.name }),
      ...(showTeam ? [el('td', { text: p.teamName })] : []),
      el('td', { class: 'num', text: p.round }),
      el('td', { class: 'num', text: p.pick }),
      el('td', { class: 'num num--lead', text: round1(p.points) }),
      el('td', { class: 'num', text: p.scoringRank ?? '—' }),
      el('td', { class: 'num', text: signed(p.value) })
    )))
  ), title, true);
}

export async function renderDraft(root, ctx) {
  mount(root, loadingState('Loading draft archive…'));
  const archive = await api.draftSeasons();
  const years = archive.seasons || [];
  if (!years.length) {
    mount(root, emptyState('No draft history', 'No seasons are available yet.'));
    return;
  }
  const season = ctx.season ?? archive.latestSeason;
  const select = el('select', { id: 'draftSeason', class: 'select', on: { change: (e) => ctx.setSeason(Number(e.target.value)) } },
    ...years.map((s) => el('option', { value: s.season, selected: s.season === season, text: label(s.season) })));
  const toolbar = el('div', { class: 'toolbar' },
    el('div', { class: 'field' }, el('label', { class: 'field__label', for: 'draftSeason', text: 'Season' }), select),
    el('p', { class: 'block__note', text: `${years.length} seasons · first season ${label(archive.firstSeason)}` }));
  if (!years.some((s) => s.season === season)) {
    select.selectedIndex = -1;
    mount(root, toolbar, emptyState('Season unavailable', 'Choose a season from the archive.'));
    return;
  }
  mount(root, toolbar, loadingState('Loading season results…'));
  const data = await api.draft(season);
  if (!data.draftAvailable) {
    mount(root, toolbar, emptyState('No draft records', 'ESPN has this season on record but does not provide its draft picks.'));
    return;
  }
  const pointsLabel = data.benchmarkScoring ? 'Re-scored points' : 'Fantasy points';
  const methodology = el('div', { class: 'draft-method' },
    el('p', { text: `Each original draft pick earns their full NBA season total, including games after a trade or drop and games on the fantasy bench. ${data.seasonComplete ? 'Final season totals.' : 'Season-to-date totals; results may change.'} Teams are ranked within this season.` }),
    el('p', { text: data.benchmarkScoring
      ? `This was a category-scoring season. These are retrospective points calculated from historical stats using the ${label(data.benchmarkSeason)} league scoring rules, not original category results.`
      : 'Points use this season’s league scoring rules. Totals across different seasons may use different rules and season lengths.' }),
    el('p', { text: 'Value = overall draft pick − scoring rank among drafted players. Positive values identify steals; negative values identify busts. Bust awards and each team’s lowest scorers consider rounds 1–10 only. Equal totals share a rank.' }),
    el('p', { class: 'dim', text: `Snapshot updated ${new Date(data.generatedAt).toLocaleDateString()}.` }),
    data.missingPlayers ? el('p', { role: 'status', text: `${data.missingPlayers} player totals are unavailable. Incomplete team totals are shown as — and rank-based awards are withheld. Player ranks and values cover only players with available totals.` }) : null);
  const leaderboard = el('div');
  let sort = { key: 'rank', dir: 'asc' };
  const columns = [
    { key: 'rank', label: '#', numeric: true },
    { key: 'teamName', label: 'Team', numeric: false },
    { key: 'count', label: 'Picks', numeric: true },
    { key: 'totalPoints', label: pointsLabel, numeric: true }
  ];
  function draw() {
    const rows = applySort(data.teams, sort, { rank: (t) => t.rank ?? 999, teamName: (t) => t.teamName, count: (t) => t.picks.length, totalPoints: (t) => t.totalPoints });
    mount(leaderboard, tableWrap(el('table', { class: 'grid' },
      el('thead', null, el('tr', null, ...columns.map((c) => sortableTh(c, sort, (key) => {
        sort = { key, dir: sort.key === key ? (sort.dir === 'asc' ? 'desc' : 'asc') : key === 'totalPoints' ? 'desc' : 'asc' };
        draw();
      })))),
      el('tbody', null, ...rows.map((t) => el('tr', null,
        el('td', { class: 'col-rank', text: t.rank ?? '—' }),
        el('th', { scope: 'row', class: 'col-team' }, el('a', { href: `#draft-team-${t.teamId}`, text: t.teamName, on: { click: (e) => {
          e.preventDefault();
          const detail = root.querySelector(`[data-draft-team="${t.teamId}"]`);
          detail.open = true;
          detail.scrollIntoView({ behavior: 'smooth', block: 'start' });
          detail.querySelector('summary').focus();
        } } })),
        el('td', { class: 'num', text: t.picks.length }),
        el('td', { class: 'num num--lead', text: round1(t.totalPoints) })
      )))
    ), 'Draft rankings', true));
  }
  draw();
  const winners = data.teams.filter((t) => t.rank === 1);
  const winner = el('div', { class: 'draft-winner' },
    el('p', { class: 'field__label', text: data.missingPlayers ? 'Highest complete draft total · incomplete coverage' : data.benchmarkScoring ? 'Best draft · retrospective comparison' : 'Draft winner' }),
    el('h2', { text: winners.map((t) => t.teamName).join(' / ') || 'Incomplete data' }),
    el('p', { text: winners.length ? `${round1(winners[0].totalPoints)} ${pointsLabel.toLowerCase()} from original draft picks` : 'No complete team totals available.' }));
  mount(root, toolbar, el('p', { class: 'draft-season-name', text: `${data.leagueName} · ${label(season)} · snapshot ${new Date(data.generatedAt).toLocaleDateString()}` }),
    data.benchmarkScoring ? el('p', { class: 'draft-notice', text: `Category-scoring season: this comparison re-scores historical stats with ${label(data.benchmarkSeason)} fantasy-point rules.` }) : null,
    data.missingPlayers ? el('p', { class: 'draft-notice', text: `${data.missingPlayers} player total unavailable. Incomplete teams are unranked; steals and busts are withheld.` }) : null,
    winner,
    block('Draft rankings', 'Sort by any column', leaderboard),
    el('div', { class: 'draft-awards' },
      block('Biggest steals', 'Largest positive value', data.steals.length ? playersTable(data.steals, 'Biggest steals', true) : emptyState('No steals to show', 'No positive values or complete scoring coverage.')),
      block('Biggest busts', 'Rounds 1–10 · largest negative value', data.busts.length ? playersTable(data.busts, 'Biggest busts', true) : emptyState('No busts to show', 'No negative values or complete scoring coverage.'))),
    block('Each team’s draft', 'Open a team to inspect every pick',
      ...data.teams.map((t) => el('details', { class: 'draft-team', dataset: { draftTeam: t.teamId } },
        el('summary', { text: `${t.rank ?? '—'}. ${t.teamName} · ${round1(t.totalPoints)} points` }),
        el('div', { class: 'draft-team__body' },
          block('Top 5 scorers', null, playersTable(t.topScorers, 'Top scorers')),
          block('Lowest 3 scorers', 'Rounds 1–10', playersTable(t.worstScorers, 'Lowest scorers')),
          block('Every draft pick', `${t.picks.length} players`, playersTable(t.picks, 'Every draft pick')))))),
    block('How this is calculated', null, methodology));
}
