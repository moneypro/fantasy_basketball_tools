/**
 * Interface previews for features that are NOT enabled.
 *
 * Both panels are rendered inside a `<fieldset disabled>` so every control is
 * inert at the platform level — nothing here is wired to a handler and the API
 * has no write endpoints at all. They exist so the shape of the eventual
 * feature is visible on a board that is, for now, read-only.
 */

import { el } from './ui.js';

const SLOTS = ['PG', 'SG', 'SF', 'PF', 'C', 'G', 'F', 'UTIL', 'BE', 'IR'];
const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

function previewBadge() {
  return el('span', { class: 'tag tag--preview', text: 'Preview — not enabled yet' });
}

function slotSelect(current, playerName) {
  const select = el('select', {
    class: 'select',
    disabled: true,
    'aria-label': `Lineup slot for ${playerName}`
  });
  const options = SLOTS.includes(current) ? SLOTS : [current, ...SLOTS];
  for (const slot of options) {
    select.append(el('option', { value: slot, selected: slot === current, text: slot }));
  }
  return select;
}

/**
 * "Update Your Roster" — lineup editor preview. Rows mirror the real roster
 * so the preview is about the team you are actually looking at.
 */
export function rosterScaffold(players, teamName) {
  const rows = (players || []).slice(0, 12);

  const table = el(
    'table',
    { class: 'grid' },
    el(
      'thead',
      null,
      el(
        'tr',
        null,
        el('th', { scope: 'col', text: 'Slot' }),
        el('th', { scope: 'col', text: 'Player' }),
        el('th', { scope: 'col', text: 'Pro team' }),
        el('th', { scope: 'col', class: 'th-num', text: 'Avg' })
      )
    ),
    el(
      'tbody',
      null,
      ...rows.map((p) =>
        el(
          'tr',
          null,
          el('td', null, slotSelect(p.lineupSlot || 'BE', p.name || 'player')),
          el('td', { class: 'teamname', text: p.name || '—' }),
          el('td', { class: 'dim', text: p.proTeam || '—' }),
          el('td', {
            class: 'num dim',
            text: typeof p.avgPoints === 'number' ? p.avgPoints.toFixed(1) : '—'
          })
        )
      )
    )
  );

  return el(
    'fieldset',
    { class: 'scaffold', disabled: true, 'aria-disabled': 'true' },
    el('legend', null, el('span', { text: 'Update your roster' }), previewBadge()),
    el('p', {
      class: 'scaffold__note',
      text:
        `Lineup editing is switched off. This board is a read-only view of the league — ` +
        `these controls show what setting a lineup for ${teamName || 'a team'} will look like once it is turned on.`
    }),
    el(
      'div',
      { class: 'scaffold__body' },
      rows.length ? el('div', { class: 'tablewrap' }, table) : el('p', { class: 'dim', text: 'No players to show.' }),
      el(
        'div',
        { class: 'scaffold__actions' },
        el('button', { class: 'btn btn--primary', type: 'button', disabled: true, text: 'Save lineup' }),
        el('button', { class: 'btn', type: 'button', disabled: true, text: 'Reset' }),
        el('span', { class: 'scaffold__hint', text: 'Saving is disabled — no changes leave this page.' })
      )
    )
  );
}

/**
 * "Run Prediction" — custom forecast request preview. The fields mirror the
 * arguments the weekly model already takes: week, starting day, daily lineup
 * size, and which injury statuses count.
 */
export function predictionScaffold(week, maxWeek) {
  const weekSelect = el('select', { class: 'select', id: 'sc-week', disabled: true });
  for (let w = 1; w <= (maxWeek || 23); w++) {
    weekSelect.append(el('option', { value: String(w), selected: w === week, text: `Week ${w}` }));
  }

  const daySelect = el('select', { class: 'select', id: 'sc-day', disabled: true });
  for (const d of DAYS) daySelect.append(el('option', { value: d, text: d }));

  const check = (id, label, checked) =>
    el(
      'label',
      { class: 'check', for: id },
      el('input', { type: 'checkbox', id, disabled: true, checked: !!checked }),
      el('span', { text: label })
    );

  return el(
    'fieldset',
    { class: 'scaffold', disabled: true, 'aria-disabled': 'true' },
    el('legend', null, el('span', { text: 'Run prediction' }), previewBadge()),
    el('p', {
      class: 'scaffold__note',
      text:
        'Custom prediction runs are switched off. Forecasts on this board are generated on a schedule; ' +
        'these fields show the settings a run will accept once it is turned on.'
    }),
    el(
      'div',
      { class: 'scaffold__body' },
      el(
        'div',
        { class: 'scaffold__grid' },
        el('div', { class: 'formrow' }, el('label', { for: 'sc-week', text: 'Week' }), weekSelect),
        el('div', { class: 'formrow' }, el('label', { for: 'sc-day', text: 'Start from' }), daySelect),
        el(
          'div',
          { class: 'formrow' },
          el('label', { for: 'sc-size', text: 'Daily lineup size' }),
          el('input', { class: 'input', id: 'sc-size', type: 'number', value: '9', min: '1', max: '13', disabled: true })
        ),
        el(
          'div',
          { class: 'formrow' },
          el('span', { class: 'formrow__label', id: 'sc-status-label', text: 'Count players who are' }),
          el(
            'div',
            { class: 'checks', role: 'group', 'aria-labelledby': 'sc-status-label' },
            check('sc-active', 'Active', true),
            check('sc-dtd', 'Day to day', false),
            check('sc-out', 'Out', false)
          )
        )
      ),
      el(
        'div',
        { class: 'scaffold__actions' },
        el('button', { class: 'btn btn--primary', type: 'button', disabled: true, text: 'Run prediction' }),
        el('span', { class: 'scaffold__hint', text: 'Running is disabled — this form sends nothing.' })
      )
    )
  );
}
