/**
 * Thin JSON client for the league API.
 *
 * The base URL arrives at runtime from /config.js, which the deploy script
 * rewrites. Everything here fails soft: a missing config, an unreachable host
 * and a 4xx/5xx all surface as one ApiError the views can render.
 */

export class ApiError extends Error {
  constructor(message, status, kind) {
    super(message);
    this.name = 'ApiError';
    this.status = status || 0;
    this.kind = kind || 'http'; // 'config' | 'network' | 'http'
  }
}

/** @returns {string|null} base URL without trailing slash, or null if unconfigured */
export function apiBase() {
  const cfg = typeof window !== 'undefined' ? window.FB_CONFIG : null;
  if (!cfg || typeof cfg.apiBaseUrl !== 'string') return null;
  return cfg.apiBaseUrl.replace(/\/+$/, '');
}

export function isConfigured() {
  return apiBase() !== null;
}

const cache = new Map();

function keyFor(path, params) {
  const qs = new URLSearchParams(
    Object.entries(params || {}).filter(([, v]) => v !== undefined && v !== null && v !== '')
  ).toString();
  return qs ? `${path}?${qs}` : path;
}

/**
 * GET a JSON endpoint. Successful responses are memoised for the page session
 * so switching tabs and stepping back through weeks is instant.
 */
export async function get(path, params, opts) {
  const key = keyFor(path, params);
  if (!opts || !opts.fresh) {
    if (cache.has(key)) return cache.get(key);
  }

  const base = apiBase();
  if (base === null) {
    throw new ApiError(
      'The board has no API endpoint configured, so there is nothing to read yet.',
      0,
      'config'
    );
  }

  let res;
  try {
    res = await fetch(base + key, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      credentials: 'omit'
    });
  } catch (err) {
    throw new ApiError('Cannot reach the league service. Check your connection and try again.', 0, 'network');
  }

  let body = null;
  try {
    body = await res.json();
  } catch (err) {
    body = null;
  }

  if (!res.ok) {
    const msg = body && typeof body.error === 'string' ? body.error : `The service answered ${res.status}.`;
    throw new ApiError(msg, res.status, 'http');
  }

  if (body === null || typeof body !== 'object') {
    throw new ApiError('The service returned something that is not league data.', res.status, 'http');
  }

  cache.set(key, body);
  return body;
}

export function clearCache() {
  cache.clear();
}

export const api = {
  league: () => get('/api/league'),
  forecast: (week) => get('/api/forecast', { week }),
  scoreboard: (week) => get('/api/scoreboard', { week }),
  roster: (teamId) => get('/api/roster', { teamId })
};
