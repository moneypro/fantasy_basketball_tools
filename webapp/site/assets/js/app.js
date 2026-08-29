/**
 * Router and page shell.
 *
 * One fetch of /api/league establishes the context every view needs — league
 * name, season, which week to land on, the team list, and whether the season
 * has finished — then the active view renders itself into #view.
 */

import { api, clearCache } from './api.js';
import { el, mount, errorState, loadingState } from './ui.js';
import { renderLeague, leagueHero } from './views/league.js';
import { renderForecast, forecastHero } from './views/forecast.js';
import { renderScoreboard, scoreboardHero } from './views/scoreboard.js';
import { renderRoster, rosterHero } from './views/roster.js';

const MIN_WEEK = 1;
const MAX_WEEK = 23;
const DEFAULT_TAB = 'forecast';
const TABS = ['league', 'forecast', 'scoreboard', 'roster'];

const dom = {
  view: document.getElementById('view'),
  tabs: document.getElementById('tabs'),
  heroEyebrow: document.getElementById('heroEyebrow'),
  heroTitle: document.getElementById('heroTitle'),
  heroLede: document.getElementById('heroLede'),
  brandName: document.getElementById('brandName'),
  brandSub: document.getElementById('brandSub'),
  footMeta: document.getElementById('footMeta')
};

let league = null;
let leagueError = null;
let renderToken = 0;

/* ---------------------------------------------------------------- routing */

function parseRoute() {
  const raw = (location.hash || '').replace(/^#\/?/, '');
  const [path, query] = raw.split('?');
  const params = new URLSearchParams(query || '');
  const tab = TABS.includes(path) ? path : DEFAULT_TAB;

  const weekRaw = Number(params.get('week'));
  const teamRaw = Number(params.get('team'));

  return {
    tab,
    week: Number.isFinite(weekRaw) && weekRaw >= MIN_WEEK && weekRaw <= MAX_WEEK ? weekRaw : null,
    teamId: Number.isFinite(teamRaw) && teamRaw > 0 ? teamRaw : null
  };
}

function go(patch) {
  const current = parseRoute();
  const next = { ...current, ...patch };
  const params = new URLSearchParams();
  if (next.week != null && (next.tab === 'forecast' || next.tab === 'scoreboard')) {
    params.set('week', String(next.week));
  }
  if (next.teamId != null && next.tab === 'roster') params.set('team', String(next.teamId));
  const qs = params.toString();
  location.hash = `#/${next.tab}${qs ? `?${qs}` : ''}`;
}

/* ------------------------------------------------------------ presentation */

function seasonLabel(season) {
  if (typeof season !== 'number' || !Number.isFinite(season)) return null;
  if (season >= 2000 && season <= 2100) {
    return `${season - 1}–${String(season).slice(2)}`;
  }
  return String(season);
}

function setHero(route) {
  const heroes = {
    league: () => leagueHero(league),
    forecast: () => forecastHero(league, route.week),
    scoreboard: () => scoreboardHero(league, route.week),
    roster: () => rosterHero(league)
  };
  const hero = heroes[route.tab]();

  dom.heroTitle.textContent = hero.title;
  dom.heroLede.textContent = hero.lede;

  mount(dom.heroEyebrow);
  if (league) {
    // The league name already sits in the masthead; the eyebrow carries season state.
    const label = seasonLabel(league.season);
    if (label) dom.heroEyebrow.append(`${label} season`);
    dom.heroEyebrow.append(
      league.seasonComplete
        ? el('span', { class: 'tag tag--final', text: 'Season final' })
        : el('span', { class: 'tag tag--live', text: `Week ${league.currentWeek} in progress` })
    );
  } else if (leagueError) {
    dom.heroEyebrow.append('League unavailable');
  } else {
    dom.heroEyebrow.append('Loading league');
  }

  document.title = `${hero.title} · ${league && league.leagueName ? league.leagueName : 'Fantasy Basketball'}`;
}

function setChrome() {
  if (!league) return;
  const label = seasonLabel(league.season);
  dom.brandName.textContent = league.leagueName || 'Fantasy Basketball';
  // Season state lives in the hero eyebrow; the masthead keeps a stable identity.
  dom.brandSub.textContent = 'Forecast board';

  const parts = [];
  if (Array.isArray(league.teams)) parts.push(`${league.teams.length} teams`);
  if (label) parts.push(`${label} season`);
  if (league.seasonComplete) parts.push('complete');
  else if (league.currentWeek) parts.push(`week ${league.currentWeek}`);
  dom.footMeta.textContent = parts.join(' · ');
}

function setTabs(tab) {
  for (const a of dom.tabs.querySelectorAll('.tab')) {
    if (a.dataset.tab === tab) a.setAttribute('aria-current', 'page');
    else a.removeAttribute('aria-current');
  }
}

/* -------------------------------------------------------------- rendering */

async function render() {
  const token = ++renderToken;
  const route = parseRoute();

  setTabs(route.tab);

  if (!league && !leagueError) {
    // Name the section straight away; with no league yet the hero titles are
    // week-free, so nothing has to be corrected once the data lands.
    setHero({ ...route, week: route.week || 1 });
    mount(dom.view, loadingState('Loading league…'));
    dom.view.setAttribute('aria-busy', 'true');
    try {
      league = await api.league();
    } catch (err) {
      leagueError = err;
    }
    if (token !== renderToken) return;
    setChrome();
  }

  const week = route.week != null
    ? route.week
    : Math.min(MAX_WEEK, Math.max(MIN_WEEK, (league && league.currentWeek) || 1));

  const teamId = route.teamId != null
    ? route.teamId
    : league && Array.isArray(league.teams) && league.teams.length
      ? league.teams[0].teamId
      : null;

  setHero({ ...route, week });

  if (leagueError) {
    dom.view.setAttribute('aria-busy', 'false');
    mount(
      dom.view,
      errorState(leagueError, () => {
        leagueError = null;
        league = null;
        clearCache();
        render();
      })
    );
    return;
  }

  const ctx = {
    league,
    week,
    teamId,
    minWeek: MIN_WEEK,
    maxWeek: MAX_WEEK,
    setWeek: (w) => go({ week: Math.min(MAX_WEEK, Math.max(MIN_WEEK, w)) }),
    setTeam: (id) => go({ teamId: id }),
    reload: () => {
      clearCache();
      render();
    }
  };

  const views = {
    league: renderLeague,
    forecast: renderForecast,
    scoreboard: renderScoreboard,
    roster: renderRoster
  };

  dom.view.setAttribute('aria-busy', 'true');
  try {
    await views[route.tab](dom.view, ctx);
  } catch (err) {
    if (token === renderToken) mount(dom.view, errorState(err, ctx.reload));
  }
  if (token === renderToken) dom.view.setAttribute('aria-busy', 'false');
}

/* ------------------------------------------------------------------- boot */

window.addEventListener('hashchange', () => {
  render();
});

// replaceState instead of assigning location.hash: it does not fire hashchange,
// so boot renders exactly once.
if (!location.hash) {
  history.replaceState(null, '', `#/${DEFAULT_TAB}`);
}

render();
