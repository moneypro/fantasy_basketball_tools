/*
 * Placeholder runtime config.
 *
 * The deploy script overwrites this file in the build directory with the real
 * HTTP API base URL, e.g.
 *   window.FB_CONFIG = { apiBaseUrl: "https://xxxx.execute-api.us-west-2.amazonaws.com" };
 *
 * An empty string means "same origin", so the site also works when it is served
 * from a host that proxies /api/* itself (and degrades to a clear error state
 * when nothing answers).
 */
window.FB_CONFIG = { apiBaseUrl: "" };
