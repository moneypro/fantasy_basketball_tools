import { api } from '../api.js';
import { el, mount, block, tableWrap, loadingState, emptyState, round1, signed, sortableTh, applySort } from '../ui.js';

const label = (year) => `${year - 1}–${String(year).slice(-2)}`;

export function draftHero(season) {
  return {
    title: 'Draft Recap',
    lede: `${season ? label(season) + ' · ' : ''}Compare original draft picks, projected rankings for the new season, and results across the league’s history.`
  };
}

function playersTable(players, title, showTeam = false, projected = false) {
  const headers = ['Player', ...(showTeam ? ['Team'] : []), 'Round', 'Pick', projected ? 'Projected points' : 'Points', projected ? 'Projected rank' : 'Scoring rank', 'Value'];
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
    ...years.map((s) => el('option', { value: s.season, selected: s.season === season, text: `${label(s.season)}${s.pointsBasis === 'projected' ? ' · projected' : ''}` })));
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
  const projected = data.pointsBasis === 'projected';
  const missingPicks = data.teams.flatMap((t) => t.picks.filter((p) => p.points === null));
  const knownCount = data.teams.reduce((n, t) => n + t.picks.length, 0) - data.missingPlayers;
  const rankedCount = data.teams.filter((t) => t.rank !== null).length;
  const coverageNote = projected && data.missingPlayers
    ? `Missing ESPN projections: ${missingPicks.map((p) => `${p.name} (${p.teamName.trim()})`).join(', ')}. Team ranks compare only the ${rankedCount} fully projected teams; incomplete teams remain unranked. Player ranks, values, steals and reaches are provisional comparisons among the ${knownCount} players with projections.`
    : `${data.missingPlayers} player totals are unavailable. Incomplete team totals are shown as — and rank-based awards are withheld. Player ranks and values cover only players with available totals.`;
  const pointsLabel = projected ? 'Projected points' : data.benchmarkScoring ? 'Re-scored points' : 'Fantasy points';
  const rankingsTitle = projected ? 'Projected draft rankings' : 'Draft rankings';
  const stealsTitle = projected ? 'Projected steals' : 'Biggest steals';
  const bustsTitle = projected ? 'Projected reaches' : 'Biggest busts';
  const methodology = el('div', { class: 'draft-method' },
    el('p', { text: projected
      ? 'Teams are ranked by the sum of ESPN’s full-season projected fantasy points for every original draft pick, including bench picks. Projected totals use ESPN’s expected games played. These are draft-roster comparisons, not forecasts of fantasy standings or weekly lineup scores.'
      : `Each original draft pick earns their full NBA season total, including games after a trade or drop and games on the fantasy bench. ${data.seasonComplete ? 'Final season totals.' : 'Season-to-date totals; results may change.'} Teams are ranked within this season.` }),
    el('p', { text: data.benchmarkScoring
      ? `This was a category-scoring season. These are retrospective points calculated from historical stats using the ${label(data.benchmarkSeason)} league scoring rules, not original category results.`
      : 'Points use this season’s league scoring rules. Totals across different seasons may use different rules and season lengths.' }),
    el('p', { text: projected
      ? 'Value = overall draft pick − projected points rank among drafted players. Positive values identify projected steals; negative values identify projected reaches. Reaches and each team’s lowest projected scorers consider rounds 1–10 only. Equal totals share a rank. Actual results, preseason stats, ADP, and research ratings do not affect these rankings.'
      : 'Value = overall draft pick − scoring rank among drafted players. Positive values identify steals; negative values identify busts. Bust awards and each team’s lowest scorers consider rounds 1–10 only. Equal totals share a rank.' }),
    el('p', { class: 'dim', text: `${projected ? 'ESPN projection snapshot' : 'Snapshot'} updated ${new Date(data.generatedAt).toLocaleString()}.${projected ? ' Projections can change; this report stays fixed until refreshed.' : ''}` }),
    data.missingPlayers ? el('p', { role: 'status', text: coverageNote }) : null);
  const leaderboard = el('div');
  let sort = { key: 'rank', dir: 'asc' };
  const columns = [
    { key: 'rank', label: '#', numeric: true },
    { key: 'teamName', label: 'Team', numeric: false },
    { key: 'count', label: projected ? 'Projected picks' : 'Picks', numeric: true },
    { key: 'totalPoints', label: pointsLabel, numeric: true }
  ];
  function draw() {
    const rows = applySort(data.teams, sort, { rank: (t) => t.rank ?? 999, teamName: (t) => t.teamName, count: (t) => t.picks.length - (projected ? t.missingPlayers : 0), totalPoints: (t) => t.totalPoints });
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
        el('td', { class: 'num', text: projected ? `${t.picks.length - t.missingPlayers}/${t.picks.length}` : t.picks.length }),
        el('td', { class: 'num num--lead', text: round1(t.totalPoints) })
      )))
    ), rankingsTitle, true));
  }
  draw();
  const winners = data.teams.filter((t) => t.rank === 1);
  const winner = el('div', { class: 'draft-winner' },
    el('p', { class: 'field__label', text: data.missingPlayers ? (projected ? 'Projected leader · complete teams only' : 'Highest complete draft total · incomplete coverage') : projected ? 'Projected draft leader' : data.benchmarkScoring ? 'Best draft · retrospective comparison' : 'Draft winner' }),
    el('h2', { text: winners.map((t) => t.teamName).join(' / ') || 'Incomplete data' }),
    el('p', { text: winners.length ? `${round1(winners[0].totalPoints)} ${pointsLabel.toLowerCase()} from original draft picks` : 'No complete team totals available.' }));
  mount(root, toolbar, el('p', { class: 'draft-season-name', text: `${data.leagueName} · ${label(season)} · snapshot ${new Date(data.generatedAt).toLocaleDateString()}` }),
    projected ? el('p', { class: 'draft-notice', text: 'Draft complete · rankings use only ESPN’s projected full-season fantasy points under this season’s league scoring rules.' }) : null,
    data.benchmarkScoring ? el('p', { class: 'draft-notice', text: `Category-scoring season: this comparison re-scores historical stats with ${label(data.benchmarkSeason)} fantasy-point rules.` }) : null,
    data.missingPlayers ? el('p', { class: 'draft-notice', text: coverageNote }) : null,
    winner,
    block(rankingsTitle, 'Sort by any column', leaderboard),
    el('div', { class: 'draft-awards' },
      block(stealsTitle, projected && data.missingPlayers ? `Provisional · ${knownCount} projected players` : 'Largest positive value', data.steals.length ? playersTable(data.steals, stealsTitle, true, projected) : emptyState('No steals to show', 'No positive values or complete scoring coverage.')),
      block(bustsTitle, `Rounds 1–10 · ${projected && data.missingPlayers ? 'provisional' : 'largest negative value'}`, data.busts.length ? playersTable(data.busts, bustsTitle, true, projected) : emptyState(projected ? 'No reaches to show' : 'No busts to show', 'No negative values or complete scoring coverage.'))),
    block('Each team’s draft', 'Open a team to inspect every pick',
      ...data.teams.map((t) => el('details', { class: 'draft-team', dataset: { draftTeam: t.teamId } },
        el('summary', { text: `${t.rank ?? '—'}. ${t.teamName} · ${round1(t.totalPoints)} ${projected ? 'projected points' : 'points'}` }),
        el('div', { class: 'draft-team__body' },
          projected && t.missingPlayers ? el('p', { class: 'draft-notice', text: `${round1(t.picks.reduce((sum, p) => sum + (p.points ?? 0), 0))} projected points from ${t.picks.length - t.missingPlayers}/${t.picks.length} picks. Missing: ${t.picks.filter((p) => p.points === null).map((p) => p.name).join(', ')}. Full total and team rank are unavailable.` }) : null,
          block(projected ? 'Top 5 projected scorers' : 'Top 5 scorers', null, playersTable(t.topScorers, 'Top scorers', false, projected)),
          block(projected ? 'Lowest 3 projected scorers' : 'Lowest 3 scorers', 'Rounds 1–10', playersTable(t.worstScorers, 'Lowest scorers', false, projected)),
          block('Every draft pick', `${t.picks.length} players`, playersTable(t.picks, 'Every draft pick', false, projected)))))),
    block('How this is calculated', null, methodology));
}
