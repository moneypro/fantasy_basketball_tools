/**
 * Small DOM helpers plus the shared pieces every view uses:
 * loading skeletons, error and empty states, chips, sortable headers,
 * and the interval bar that makes the ± visible.
 */

/** Hyperscript-ish element builder. Text always goes through textContent. */
export function el(tag, attrs, ...children) {
  const node = document.createElement(tag);
  const a = attrs || {};

  for (const [k, v] of Object.entries(a)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = String(v);
    else if (k === 'style' && typeof v === 'object') Object.assign(node.style, v);
    else if (k === 'dataset') Object.assign(node.dataset, v);
    else if (k === 'on') for (const [ev, fn] of Object.entries(v)) node.addEventListener(ev, fn);
    else if (v === true) node.setAttribute(k, '');
    else node.setAttribute(k, String(v));
  }

  for (const child of children.flat(4)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
  return node;
}

export function mount(node, ...children) {
  clear(node);
  for (const child of children.flat(4)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

/* --------------------------------------------------------------- numbers */

const isNum = (v) => typeof v === 'number' && Number.isFinite(v);

export function round0(v) {
  return isNum(v) ? String(Math.round(v)) : '—';
}

export function round1(v) {
  return isNum(v) ? v.toFixed(1) : '—';
}

export function signed(v) {
  if (!isNum(v)) return '—';
  const r = Math.round(v);
  return (r > 0 ? '+' : '') + r;
}

export function pct3(w, l) {
  const g = (w || 0) + (l || 0);
  if (!g) return '.000';
  return (w / g).toFixed(3).replace(/^0/, '');
}

export function relativeTime(iso) {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  const mins = Math.round((Date.now() - t) / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs} hr ago`;
  const days = Math.round(hrs / 24);
  return days === 1 ? 'yesterday' : `${days} days ago`;
}

/* ---------------------------------------------------------------- blocks */

export function block(title, note, ...children) {
  return el(
    'section',
    { class: 'block' },
    el(
      'div',
      { class: 'block__head' },
      el('h2', { class: 'block__title', text: title }),
      note ? el('p', { class: 'block__note', text: note }) : null
    ),
    ...children
  );
}

/**
 * Scrollable shell for a table. It is focusable so the columns that overflow
 * can be reached from the keyboard, which means it needs a name.
 */
export function tableWrap(table, label, compact) {
  return el(
    'div',
    {
      class: `tablewrap${compact ? ' tablewrap--compact' : ''}`,
      tabindex: '0',
      role: 'group',
      'aria-label': `${label}, scrollable`
    },
    table
  );
}

/* ---------------------------------------------------------------- states */

export function skeletonTable(rows = 8, cols = 5) {
  // Slight per-row variation so the placeholder reads like rows of text
  // rather than a repeating graphic.
  const firstCol = [22, 17, 25, 19, 23, 16, 21, 26, 18, 24, 20, 15, 22];
  return el(
    'div',
    { class: 'tablewrap', 'aria-hidden': 'true' },
    ...Array.from({ length: rows }, (_, r) =>
      el(
        'div',
        { class: 'skelrow' },
        ...Array.from({ length: cols }, (_, c) =>
          el('div', {
            class: 'skel',
            style: c === 0
              ? { flex: `0 0 ${firstCol[r % firstCol.length]}%` }
              : { flex: `1 1 ${60 + ((r * 7 + c * 13) % 34)}%` }
          })
        )
      )
    )
  );
}

export function skeletonCards(n = 6) {
  return el(
    'div',
    { class: 'cards', 'aria-hidden': 'true' },
    ...Array.from({ length: n }, () =>
      el(
        'div',
        { class: 'card' },
        el('div', { class: 'skel', style: { width: '38%', marginBottom: '1rem' } }),
        el('div', { class: 'skel', style: { width: '80%', height: '20px', marginBottom: '0.7rem' } }),
        el('div', { class: 'skel', style: { width: '70%', height: '20px' } })
      )
    )
  );
}

export function loadingState(label) {
  return el(
    'div',
    { 'aria-label': label || 'Loading' },
    el('p', { class: 'block__note', style: { marginBottom: '0.6rem' }, text: label || 'Loading…' }),
    skeletonTable()
  );
}

export function errorState(err, onRetry) {
  const kind = err && err.kind;
  const eyebrow = kind === 'config' ? 'Not configured' : kind === 'network' ? 'Offline' : `Error ${err && err.status ? err.status : ''}`.trim();

  const body = el('p', { class: 'state__body', text: (err && err.message) || 'Something went wrong.' });

  if (kind === 'config') {
    body.append(
      ' Deploy writes ',
      el('code', { text: 'config.js' }),
      ' with the API address; until then this page has nothing to read.'
    );
  }

  return el(
    'div',
    { class: 'state', role: 'alert' },
    el('p', { class: 'state__eyebrow', text: eyebrow }),
    el('h3', { class: 'state__title', text: kind === 'config' ? 'No API address' : 'Could not load this view' }),
    body,
    onRetry
      ? el(
          'div',
          { class: 'state__actions' },
          el('button', { class: 'btn', type: 'button', text: 'Try again', on: { click: onRetry } })
        )
      : null
  );
}

export function emptyState(title, body) {
  return el(
    'div',
    { class: 'state' },
    el('p', { class: 'state__eyebrow state__eyebrow--calm', text: 'Nothing here' }),
    el('h3', { class: 'state__title', text: title }),
    el('p', { class: 'state__body', text: body })
  );
}

/* ----------------------------------------------------------------- chips */

export function injuryChips(injuries) {
  const out = (injuries && Array.isArray(injuries.out) ? injuries.out : []).filter(Boolean);
  const dtd = (injuries && Array.isArray(injuries.dayToDay) ? injuries.dayToDay : []).filter(Boolean);

  if (!out.length && !dtd.length) {
    return el('span', { class: 'chip chip--none', text: 'Full strength' });
  }

  return el(
    'div',
    { class: 'chips' },
    ...out.map((n) => el('span', { class: 'chip chip--out', title: `Out: ${n}`, text: n })),
    ...dtd.map((n) => el('span', { class: 'chip chip--dtd', title: `Day to day: ${n}`, text: n }))
  );
}

/* ------------------------------------------------- the interval (signature) */

/**
 * Build a shared linear scale across every team's projection so the bars in
 * different rows are directly comparable.
 */
export function projectionScale(teams) {
  let lo = Infinity;
  let hi = -Infinity;

  for (const t of teams) {
    const candidates = [];
    if (isNum(t.mean)) candidates.push(t.mean - (isNum(t.stdDev) ? t.stdDev : 0), t.mean + (isNum(t.stdDev) ? t.stdDev : 0));
    if (isNum(t.meanWithDtd)) candidates.push(t.meanWithDtd);
    for (const c of candidates) {
      if (c < lo) lo = c;
      if (c > hi) hi = c;
    }
  }

  if (!Number.isFinite(lo) || !Number.isFinite(hi) || hi === lo) {
    return () => 50;
  }

  const pad = (hi - lo) * 0.07;
  lo -= pad;
  hi += pad;

  return (v) => {
    if (!isNum(v)) return null;
    const p = ((v - lo) / (hi - lo)) * 100;
    return Math.min(100, Math.max(0, p));
  };
}

const legendItem = (swatch, label) =>
  el(
    'span',
    { class: 'legend__item' },
    el('span', { class: `legend__swatch legend__swatch--${swatch}`, 'aria-hidden': 'true' }),
    label
  );

export function projectionLegend() {
  return el(
    'div',
    { class: 'legend' },
    legendItem('band', '±1 standard deviation'),
    legendItem('tick', 'mean'),
    el('span', { class: 'legend__sep', 'aria-hidden': 'true', text: '│' }),
    el('span', { class: 'legend__item' }, el('span', { class: 'legend__mark legend__mark--out', text: 'Name' }), ' out'),
    el('span', { class: 'legend__item' }, el('span', { class: 'legend__mark legend__mark--dtd', text: 'Name' }), ' day to day')
  );
}

/* --------------------------------------------------- forecast board bits */

/**
 * Just the ±1σ band + mean tick, with no value text — the forecast board
 * puts the number in its own column and the bar in the next one.
 */
export function intervalBar(mean, sd, scale, index, thin) {
  const label = `Projected ${round0(mean)} points, standard deviation ${round0(isNum(sd) ? sd : 0)}`;
  const bar = el('div', {
    class: `ivl${thin ? ' ivl--thin' : ''}`,
    role: 'img',
    'aria-label': label,
    style: { '--i': String(index || 0) }
  });

  const l = scale(mean - (isNum(sd) ? sd : 0));
  const r = scale(mean + (isNum(sd) ? sd : 0));
  if (l !== null && r !== null) {
    bar.append(el('span', { class: 'ivl__band', style: { left: `${l}%`, width: `${Math.max(r - l, 1.2)}%` } }));
  }

  const m = scale(mean);
  if (m !== null) bar.append(el('span', { class: 'ivl__tick', style: { left: `${m}%` } }));

  return bar;
}

/**
 * Injury marks rendered as underlined names — solid orange for out, dotted
 * for day-to-day — instead of pill chips, so a row with several injuries
 * still reads as prose rather than a wall of badges.
 */
export function injuryMarks(injuries) {
  const out = (injuries && Array.isArray(injuries.out) ? injuries.out : []).filter(Boolean);
  const dtd = (injuries && Array.isArray(injuries.dayToDay) ? injuries.dayToDay : []).filter(Boolean);

  if (!out.length && !dtd.length) {
    return el('span', { class: 'imark imark--full', text: '—' });
  }

  return el(
    'div',
    { class: 'imarks' },
    ...out.map((n) => el('span', { class: 'imark imark--out', title: `Out: ${n}`, text: n })),
    ...dtd.map((n) => el('span', { class: 'imark imark--dtd', title: `Day to day: ${n}`, text: n }))
  );
}

/* --------------------------------------------------------- sortable head */

/**
 * @param {object} spec {key, label, numeric}
 * @param {object} sort {key, dir}
 * @param {(key:string)=>void} onSort
 */
export function sortableTh(spec, sort, onSort) {
  const active = sort.key === spec.key;
  const th = el('th', {
    scope: 'col',
    class: spec.numeric ? 'th-num' : '',
    ...(active ? { 'aria-sort': sort.dir === 'asc' ? 'ascending' : 'descending' } : {})
  });

  th.append(
    el(
      'button',
      {
        class: 'sortbtn',
        type: 'button',
        title: `Sort by ${spec.label}`,
        on: { click: () => onSort(spec.key) }
      },
      el('span', { text: spec.label }),
      el('span', { class: 'sortbtn__arrow', 'aria-hidden': 'true', text: active && sort.dir === 'asc' ? '▲' : '▼' })
    )
  );
  return th;
}

export function applySort(rows, sort, accessors) {
  const get = accessors[sort.key];
  if (!get) return rows.slice();
  const dir = sort.dir === 'asc' ? 1 : -1;
  return rows.slice().sort((a, b) => {
    const av = get(a);
    const bv = get(b);
    if (typeof av === 'string' || typeof bv === 'string') {
      return String(av).localeCompare(String(bv)) * dir;
    }
    const an = isNum(av) ? av : -Infinity;
    const bn = isNum(bv) ? bv : -Infinity;
    return (an - bn) * dir;
  });
}

/* ---------------------------------------------------------- week control */

export function weekStepper(week, minWeek, maxWeek, onChange) {
  const select = el('select', {
    class: 'select',
    id: 'weekSelect',
    'aria-label': 'Week',
    on: { change: (e) => onChange(Number(e.target.value)) }
  });

  for (let w = minWeek; w <= maxWeek; w++) {
    select.append(el('option', { value: String(w), selected: w === week, text: `Week ${w}` }));
  }

  return el(
    'div',
    { class: 'field' },
    el('label', { class: 'field__label', for: 'weekSelect', text: 'Week' }),
    el(
      'div',
      { class: 'stepper' },
      el('button', {
        class: 'stepper__btn',
        type: 'button',
        'aria-label': 'Previous week',
        text: '‹',
        disabled: week <= minWeek,
        on: { click: () => onChange(week - 1) }
      }),
      select,
      el('button', {
        class: 'stepper__btn',
        type: 'button',
        'aria-label': 'Next week',
        text: '›',
        disabled: week >= maxWeek,
        on: { click: () => onChange(week + 1) }
      })
    )
  );
}

/**
 * Ledger-style week strip: a hairline with a dial dot, and every week as a
 * clickable chip, the current one filled solid. Used by the forecast board
 * in place of the plain select-and-arrows stepper.
 */
export function weekChips(week, minWeek, maxWeek, onChange) {
  const chips = el('div', { class: 'weekchips', role: 'group', 'aria-label': 'Week' });
  for (let w = minWeek; w <= maxWeek; w++) {
    const current = w === week;
    chips.append(
      el('button', {
        class: 'weekchip',
        type: 'button',
        'aria-current': current ? 'true' : null,
        text: String(w).padStart(2, '0'),
        on: { click: () => onChange(w) }
      })
    );
  }

  return el(
    'div',
    { class: 'weekbar' },
    el('div', { class: 'weekdial' }, el('span', { class: 'weekdial__dot', 'aria-hidden': 'true' })),
    chips
  );
}
