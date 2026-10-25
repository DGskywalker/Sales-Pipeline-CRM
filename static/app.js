'use strict';
/* Sales Pipeline CRM — dependency-free single-page dashboard. */

const STAGES = ['Lead', 'Contacted', 'Qualified', 'Proposal', 'Won', 'Lost'];
const OPEN = STAGES.slice(0, 4);
const ACT_ICON = { call: '☎', email: '✉', meeting: '◎', note: '✎', stage_change: '➜' };
const VIEWS = {
  dashboard: ['Dashboard', 'Pipeline health, forecast and team performance'],
  pipeline: ['Pipeline', 'Drag deals between stages to update them'],
  contacts: ['Contacts', 'Leads and customers'],
  activity: ['Activity', 'Every call, email, meeting and stage move'],
};

/* ---------- helpers ---------- */
function h(tag, props, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') e.className = v;
    else if (k === 'style') e.style.cssText = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (k in e && k !== 'list') e[k] = v;
    else e.setAttribute(k, v === true ? '' : v);
  }
  for (const kid of kids.flat(Infinity)) if (kid != null && kid !== false) e.append(kid instanceof Node ? kid : String(kid));
  return e;
}
function s(tag, attrs, ...kids) {
  const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs || {})) e.setAttribute(k, v);
  for (const kid of kids.flat(Infinity)) if (kid != null) e.append(kid instanceof Node ? kid : document.createTextNode(kid));
  return e;
}
const $ = sel => document.querySelector(sel);
const money = (n, compact) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: compact ? 1 : 0, notation: compact ? 'compact' : 'standard' }).format(n || 0);
const pct = v => v == null ? '—' : Math.round(v * 100) + '%';
const stageColor = st => `var(--s-${st.toLowerCase()})`;
const date = d => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
function ago(d) {
  const sec = (Date.now() - new Date(d)) / 1000;
  for (const [n, u] of [[86400 * 30, 'mo'], [86400, 'd'], [3600, 'h'], [60, 'm']]) if (sec >= n) return Math.floor(sec / n) + u + ' ago';
  return 'just now';
}
function avatar(name) {
  let hash = 0;
  for (const ch of name || '?') hash = (hash * 31 + ch.charCodeAt(0)) % 360;
  const initials = (name || '?').split(/\s+/).map(p => p[0]).join('').slice(0, 2).toUpperCase();
  return h('span', { class: 'avatar', style: `background:hsl(${hash} 55% 48%)`, title: name }, initials);
}
function debounce(fn, ms = 250) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
function toast(msg, err) {
  const t = h('div', { class: 'toast' + (err ? ' err' : '') }, msg);
  $('#toasts').append(t);
  setTimeout(() => t.remove(), 3500);
}

async function api(path, opts = {}) {
  const init = { ...opts, headers: { ...(opts.headers || {}) } };
  if (opts.body && typeof opts.body !== 'string') { init.body = JSON.stringify(opts.body); init.headers['Content-Type'] = 'application/json'; }
  const r = await fetch('/api' + path, init);
  if (!r.ok) {
    let msg = r.statusText;
    try { const j = await r.json(); msg = typeof j.detail === 'string' ? j.detail : j.detail.map(d => `${d.loc.at(-1)}: ${d.msg}`).join('; '); } catch (_) { /* keep statusText */ }
    throw new Error(msg);
  }
  if (r.status === 204) return null;
  const data = await r.json();
  if (opts.withTotal) return { data, total: +r.headers.get('X-Total-Count') };
  return data;
}
const safe = fn => async (...a) => { try { return await fn(...a); } catch (e) { toast(e.message, true); } };
function formData(form) {
  const out = {};
  for (const [k, v] of new FormData(form)) out[k] = typeof v === 'string' ? v.trim() : v;
  return out;
}
const nullify = o => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, v === '' ? null : v]));

/* ---------- router ---------- */
let current = 'dashboard';
function route() {
  current = (location.hash.replace('#/', '') || 'dashboard');
  if (!VIEWS[current]) current = 'dashboard';
  document.querySelectorAll('#nav a').forEach(a => a.classList.toggle('active', a.dataset.view === current));
  $('#title').textContent = VIEWS[current][0];
  $('#subtitle').textContent = VIEWS[current][1];
  refresh();
}
function refresh() {
  const view = $('#view');
  if (!view.childElementCount) view.replaceChildren(h('div', { class: 'kpis' }, [1, 2, 3, 4].map(() => h('div', { class: 'skeleton' }))));
  return safe(RENDER[current])(view);
}

/* ---------- dashboard ---------- */
async function renderDashboard(view) {
  const [sum, owners, feed, deals] = await Promise.all([
    api('/reports/summary'), api('/reports/owners'), api('/reports/activity?limit=8'), api('/deals?limit=500'),
  ]);
  const openCount = OPEN.reduce((n, st) => n + sum.deals_by_stage.find(x => x.stage === st).count, 0);
  const avgDeal = deals.length ? deals.reduce((a, d) => a + d.value, 0) / deals.length : 0;
  const kpis = [
    ['Open pipeline', money(sum.open_pipeline_value, true), `${openCount} open deals`],
    ['Weighted forecast', money(sum.weighted_forecast, true), 'probability-adjusted'],
    ['Closed won', money(sum.won_value, true), `${sum.deals_by_stage[4].count} deals`],
    ['Win rate', pct(sum.win_rate), `${sum.deals_by_stage[4].count} won · ${sum.deals_by_stage[5].count} lost`],
    ['Avg deal size', money(avgDeal, true), `${deals.length} deals total`],
    ['Contacts', sum.total_contacts.toLocaleString(), 'in database'],
  ];
  view.replaceChildren(
    h('div', { class: 'kpis' }, kpis.map(([l, v, hint]) => h('div', { class: 'card kpi' },
      h('div', { class: 'label' }, l), h('div', { class: 'value num' }, v), h('div', { class: 'hint' }, hint)))),
    h('div', { class: 'grid-2' },
      h('div', { class: 'card' }, h('h2', {}, 'Pipeline by stage', h('small', {}, 'deal count · total value')), funnel(sum.deals_by_stage)),
      h('div', { class: 'card' }, h('h2', {}, 'New pipeline by month', h('small', {}, 'by deal creation date')), monthlyChart(deals))),
    h('div', { class: 'grid-2' },
      h('div', { class: 'card' }, h('h2', {}, 'Team leaderboard', h('small', {}, 'ranked by won value')), leaderboard(owners)),
      h('div', { class: 'card' }, h('h2', {}, 'Recent activity', h('a', { href: '#/activity', style: 'font-size:12px;font-weight:500' }, 'View all →')), feedList(feed))),
  );
}

function funnel(rows) {
  const max = Math.max(1, ...rows.map(r => r.total_value));
  return h('div', {}, rows.map(r => h('div', { class: 'funnel-row' },
    h('span', {}, h('span', { class: 'dot', style: `background:${stageColor(r.stage)}` }), r.stage),
    h('div', { class: 'funnel-bar' }, h('span', { style: `width:${(r.total_value / max) * 100}%;background:${stageColor(r.stage)}` })),
    h('span', { class: 'num' }, `${r.count} · ${money(r.total_value, true)}`))));
}

function monthlyChart(deals) {
  const months = [];
  const now = new Date();
  for (let i = 5; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    months.push({ key: `${d.getFullYear()}-${d.getMonth()}`, label: d.toLocaleString('en-US', { month: 'short' }), won: 0, open: 0, lost: 0 });
  }
  const byKey = Object.fromEntries(months.map(m => [m.key, m]));
  for (const d of deals) {
    const c = new Date(d.created_at);
    const m = byKey[`${c.getFullYear()}-${c.getMonth()}`];
    if (m) m[d.stage === 'Won' ? 'won' : d.stage === 'Lost' ? 'lost' : 'open'] += d.value;
  }
  const W = 560, H = 220, pad = { l: 46, r: 8, t: 10, b: 24 };
  const max = Math.max(1, ...months.map(m => m.won + m.open + m.lost));
  const nice = Math.pow(10, Math.floor(Math.log10(max)));
  const top = Math.ceil(max / nice) * nice;
  const y = v => pad.t + (H - pad.t - pad.b) * (1 - v / top);
  const bw = (W - pad.l - pad.r) / months.length;
  const series = [['won', 'var(--s-won)'], ['open', 'var(--accent)'], ['lost', 'var(--s-lost)']];
  const grid = [0, .25, .5, .75, 1].map(f => [
    s('line', { x1: pad.l, x2: W - pad.r, y1: y(top * f), y2: y(top * f), stroke: 'var(--bd)' }),
    s('text', { x: pad.l - 6, y: y(top * f) + 4, 'text-anchor': 'end' }, money(top * f, true)),
  ]);
  const bars = months.map((m, i) => {
    let acc = 0;
    const x = pad.l + i * bw + bw * 0.22;
    const rects = series.map(([k, color]) => {
      const r = s('rect', { x, width: bw * 0.56, y: y(acc + m[k]), height: Math.max(0, y(acc) - y(acc + m[k])), fill: color, rx: 3 },
        s('title', {}, `${m.label} · ${k}: ${money(m[k])}`));
      acc += m[k];
      return r;
    });
    return [rects, s('text', { x: x + bw * 0.28, y: H - 6, 'text-anchor': 'middle' }, m.label)];
  });
  return h('div', {},
    s('svg', { viewBox: `0 0 ${W} ${H}`, width: '100%', role: 'img', 'aria-label': 'New pipeline value by month' }, grid, bars),
    h('div', { class: 'legend' }, series.map(([k, c]) => h('span', {}, h('span', { class: 'dot', style: `background:${c}` }), k[0].toUpperCase() + k.slice(1)))));
}

function leaderboard(rows) {
  if (!rows.length) return h('div', { class: 'empty' }, 'No owned deals yet');
  return h('div', { class: 'table-wrap' }, h('table', {},
    h('thead', {}, h('tr', {}, h('th', {}, 'Owner'), h('th', { class: 'num' }, 'Open'), h('th', { class: 'num' }, 'Open value'), h('th', { class: 'num' }, 'Won value'), h('th', { class: 'num' }, 'Win rate'))),
    h('tbody', {}, rows.map(r => h('tr', { onclick: () => { location.hash = '#/pipeline'; pipelineState.owner = r.owner; } },
      h('td', {}, h('span', { class: 'who' }, avatar(r.owner), r.owner)),
      h('td', { class: 'num' }, r.open_deals), h('td', { class: 'num' }, money(r.open_value)),
      h('td', { class: 'num' }, money(r.won_value)), h('td', { class: 'num' }, pct(r.win_rate)))))));
}

function feedList(items) {
  if (!items.length) return h('div', { class: 'empty' }, 'No activity yet');
  return h('ul', { class: 'feed' }, items.map(a => h('li', { onclick: () => openDeal(a.deal_id), style: 'cursor:pointer' },
    h('span', { class: 'fi' }, ACT_ICON[a.type] || '•'),
    h('div', { class: 'what' }, a.type === 'stage_change' ? `Moved ${a.note.replace('->', '→')}` : a.note || a.type,
      h('small', {}, a.company && !a.deal_title.includes(a.company) ? `${a.deal_title} · ${a.company}` : a.deal_title)),
    h('time', { title: new Date(a.created_at).toLocaleString() }, ago(a.created_at)))));
}

/* ---------- pipeline board ---------- */
const pipelineState = { q: '', owner: '' };
async function renderPipeline(view) {
  const params = new URLSearchParams({ limit: 500 });
  if (pipelineState.q) params.set('q', pipelineState.q);
  if (pipelineState.owner) params.set('owner', pipelineState.owner);
  const [deals, owners] = await Promise.all([api('/deals?' + params), api('/reports/owners')]);
  const search = h('input', { type: 'search', placeholder: 'Search deals, contacts, companies…', value: pipelineState.q,
    oninput: debounce(e => { pipelineState.q = e.target.value; refresh(); }) });
  const ownerSel = h('select', { onchange: e => { pipelineState.owner = e.target.value; refresh(); } },
    h('option', { value: '' }, 'All owners'), owners.map(o => h('option', { value: o.owner, selected: o.owner === pipelineState.owner }, o.owner)));
  const open = deals.filter(d => OPEN.includes(d.stage));
  const board = h('div', { class: 'board' }, STAGES.map(st => column(st, deals.filter(d => d.stage === st))));
  view.replaceChildren(
    h('div', { class: 'toolbar' }, search, ownerSel, h('span', { class: 'spacer' }),
      h('span', { class: 'muted' }, `${open.length} open · ${money(open.reduce((a, d) => a + d.value, 0))}`)),
    board);
  if (document.activeElement === document.body && pipelineState.q) { search.focus(); search.setSelectionRange(99, 99); }
}

function column(stage, deals) {
  const body = h('div', { class: 'col-body' }, deals.length ? deals.map(dealCard) : h('div', { class: 'empty' }, 'Drop deals here'));
  const col = h('div', { class: 'col', 'data-stage': stage,
    ondragover: e => { e.preventDefault(); col.classList.add('over'); },
    ondragleave: e => { if (!col.contains(e.relatedTarget)) col.classList.remove('over'); },
    ondrop: safe(async e => {
      e.preventDefault(); col.classList.remove('over');
      const id = +e.dataTransfer.getData('text/plain');
      const from = e.dataTransfer.getData('application/x-stage');
      if (!id || from === stage) return;
      await api(`/deals/${id}`, { method: 'PATCH', body: { stage } });
      toast(`Moved to ${stage}`);
      refresh();
    }) },
    h('div', { class: 'col-head' }, h('span', {}, h('span', { class: 'dot', style: `background:${stageColor(stage)}` }), stage, ' ', h('span', { class: 'muted' }, deals.length)),
      h('span', { class: 'muted num' }, money(deals.reduce((a, d) => a + d.value, 0), true))),
    body);
  return col;
}

function dealCard(d) {
  return h('div', { class: 'deal', draggable: true, style: `--stage:${stageColor(d.stage)}`, onclick: () => openDeal(d.id),
    ondragstart: e => { e.dataTransfer.setData('text/plain', d.id); e.dataTransfer.setData('application/x-stage', d.stage); e.currentTarget.classList.add('dragging'); },
    ondragend: e => e.currentTarget.classList.remove('dragging') },
    h('div', { class: 't' }, d.title),
    h('div', { class: 'c' }, `${d.contact_name}${d.company ? ' · ' + d.company : ''}`),
    h('div', { class: 'm' }, h('span', { class: 'v num' }, money(d.value)),
      h('span', { class: 'who muted' }, ago(d.updated_at), d.owner ? avatar(d.owner) : null)));
}

/* ---------- contacts ---------- */
const contactState = { q: '', page: 0, size: 15 };
async function renderContacts(view) {
  const p = new URLSearchParams({ limit: contactState.size, offset: contactState.page * contactState.size });
  if (contactState.q) p.set('q', contactState.q);
  const { data, total } = await api('/contacts?' + p, { withTotal: true });
  const pages = Math.max(1, Math.ceil(total / contactState.size));
  const search = h('input', { type: 'search', placeholder: 'Search name, email or company…', value: contactState.q,
    oninput: debounce(e => { contactState.q = e.target.value; contactState.page = 0; refresh(); }) });
  const from = total ? contactState.page * contactState.size + 1 : 0;
  view.replaceChildren(
    h('div', { class: 'toolbar' }, search, h('span', { class: 'spacer' }),
      h('button', { type: 'button', onclick: importModal }, '⤒ Import CSV'),
      h('button', { type: 'button', class: 'primary', onclick: () => contactModal() }, '+ Add contact')),
    h('div', { class: 'card', style: 'padding:6px 6px 12px' },
      data.length ? h('div', { class: 'table-wrap' }, h('table', {},
        h('thead', {}, h('tr', {}, ['Name', 'Email', 'Company', 'Phone', 'Source', 'Added'].map(t => h('th', {}, t)))),
        h('tbody', {}, data.map(c => h('tr', { onclick: () => openContact(c.id) },
          h('td', {}, h('span', { class: 'who' }, avatar(c.name), h('b', {}, c.name))),
          h('td', { class: 'muted' }, c.email), h('td', {}, c.company || '—'), h('td', { class: 'muted num' }, c.phone || '—'),
          h('td', {}, c.source ? h('span', { class: 'pill' }, c.source.replace(/_/g, ' ')) : '—'),
          h('td', { class: 'muted' }, date(c.created_at)))))))
        : h('div', { class: 'empty' }, contactState.q ? 'No contacts match your search' : 'No contacts yet — add one or import a CSV'),
      h('div', { class: 'pager', style: 'padding:0 10px' },
        h('span', { class: 'muted' }, `${from}–${from + data.length - (total ? 1 : 0)} of ${total}`),
        h('div', {},
          h('button', { type: 'button', disabled: contactState.page === 0, onclick: () => { contactState.page--; refresh(); } }, '← Prev'),
          h('span', { class: 'muted', style: 'padding:7px 4px' }, `Page ${contactState.page + 1} / ${pages}`),
          h('button', { type: 'button', disabled: contactState.page + 1 >= pages, onclick: () => { contactState.page++; refresh(); } }, 'Next →')))));
  if (contactState.q) { search.focus(); search.setSelectionRange(99, 99); }
}

/* ---------- activity ---------- */
const activityState = { type: '' };
async function renderActivity(view) {
  const feed = await api('/reports/activity?limit=100');
  const types = ['', 'stage_change', 'call', 'email', 'meeting', 'note'];
  const shown = activityState.type ? feed.filter(a => a.type === activityState.type) : feed;
  view.replaceChildren(
    h('div', { class: 'toolbar' }, types.map(t => h('button', { type: 'button', class: activityState.type === t ? 'primary' : '',
      onclick: () => { activityState.type = t; refresh(); } }, t ? `${ACT_ICON[t]} ${t.replace('_', ' ')}` : 'All'))),
    h('div', { class: 'card' }, feedList(shown)));
}

const RENDER = { dashboard: renderDashboard, pipeline: renderPipeline, contacts: renderContacts, activity: renderActivity };

/* ---------- drawer ---------- */
function openDrawer(...content) {
  $('#drawer').replaceChildren(...content);
  $('#drawer').classList.add('open');
  $('#drawer').setAttribute('aria-hidden', 'false');
  $('#overlay').hidden = false;
}
function closeDrawer() {
  $('#drawer').classList.remove('open');
  $('#drawer').setAttribute('aria-hidden', 'true');
  $('#overlay').hidden = true;
}
const drawerHead = (title, sub) => h('div', { class: 'drawer-head' },
  h('div', {}, h('h2', {}, title), h('div', { class: 'muted' }, sub)),
  h('button', { type: 'button', class: 'ghost', onclick: closeDrawer, 'aria-label': 'Close' }, '✕'));

const openDeal = safe(async id => {
  const [d, acts] = await Promise.all([api(`/deals/${id}`), api(`/deals/${id}/activities`)]);
  const save = async body => { await api(`/deals/${id}`, { method: 'PATCH', body }); toast('Deal updated'); refresh(); openDeal(id); };
  const form = h('form', { class: 'form-grid', onsubmit: safe(async e => {
    e.preventDefault();
    const f = formData(e.target);
    await save({ title: f.title, value: +f.value || 0, stage: f.stage, owner: f.owner || null });
  }) },
    h('label', { class: 'full' }, 'Title', h('input', { name: 'title', value: d.title, required: true, maxLength: 160 })),
    h('label', {}, 'Value (USD)', h('input', { name: 'value', type: 'number', min: 0, step: 100, value: d.value })),
    h('label', {}, 'Owner', h('input', { name: 'owner', value: d.owner || '', maxLength: 80 })),
    h('label', { class: 'full' }, 'Stage', h('select', { name: 'stage' }, STAGES.map(st => h('option', { selected: st === d.stage }, st)))),
    h('div', { class: 'row-end full' },
      h('button', { type: 'button', class: 'danger', onclick: safe(async () => {
        if (!confirm(`Delete "${d.title}"? This cannot be undone.`)) return;
        await api(`/deals/${id}`, { method: 'DELETE' }); toast('Deal deleted'); closeDrawer(); refresh();
      }) }, 'Delete'),
      h('button', { type: 'submit', class: 'primary' }, 'Save changes')));
  const idx = STAGES.indexOf(d.stage);
  const stepper = h('div', { class: 'stepper', style: `--stage:${stageColor(d.stage)}` }, STAGES.map((st, i) =>
    h('button', { type: 'button', class: st === d.stage ? 'cur' : (i < idx && d.stage !== 'Lost') ? 'done' : '',
      onclick: safe(() => st !== d.stage && save({ stage: st })) }, st)));
  const logForm = h('form', { class: 'form-grid', onsubmit: safe(async e => {
    e.preventDefault();
    const f = formData(e.target);
    await api(`/deals/${id}/activities`, { method: 'POST', body: f });
    toast('Activity logged'); openDeal(id); if (current !== 'pipeline') refresh();
  }) },
    h('label', {}, 'Type', h('select', { name: 'type' }, ['call', 'email', 'meeting', 'note'].map(t => h('option', { value: t }, `${ACT_ICON[t]} ${t}`)))),
    h('label', { class: 'full' }, 'Note', h('textarea', { name: 'note', rows: 2, maxLength: 2000, placeholder: 'What happened?' })),
    h('div', { class: 'row-end full' }, h('button', { type: 'submit' }, 'Log activity')));
  const timeline = acts.length ? h('ul', { class: 'timeline' }, [...acts].reverse().map(a => h('li', { class: a.type === 'stage_change' ? 'stage' : '' },
    h('b', {}, a.type === 'stage_change' ? 'Stage changed ' : `${ACT_ICON[a.type]} ${a.type[0].toUpperCase() + a.type.slice(1)} `),
    a.type === 'stage_change' ? a.note.replace('->', '→') : a.note,
    h('time', {}, new Date(a.created_at).toLocaleString())))) : h('div', { class: 'empty' }, 'No activity yet');
  openDrawer(
    drawerHead(d.title, h('span', {}, h('a', { href: '#', onclick: e => { e.preventDefault(); openContact(d.contact_id); } }, d.contact_name),
      d.company ? ` · ${d.company}` : '', ` · ${money(d.value)}`)),
    stepper, form,
    h('div', { class: 'section' }, h('h3', {}, 'Log activity'), logForm),
    h('div', { class: 'section' }, h('h3', {}, `Timeline (${acts.length})`), timeline));
});

const openContact = safe(async id => {
  const [c, deals] = await Promise.all([api(`/contacts/${id}`), api(`/contacts/${id}/deals`)]);
  const form = h('form', { class: 'form-grid', onsubmit: safe(async e => {
    e.preventDefault();
    await api(`/contacts/${id}`, { method: 'PATCH', body: nullify(formData(e.target)) });
    toast('Contact updated'); refresh(); openContact(id);
  }) },
    h('label', {}, 'Name', h('input', { name: 'name', value: c.name, required: true, maxLength: 120 })),
    h('label', {}, 'Email', h('input', { value: c.email, disabled: true })),
    h('label', {}, 'Company', h('input', { name: 'company', value: c.company || '', maxLength: 160 })),
    h('label', {}, 'Phone', h('input', { name: 'phone', value: c.phone || '', maxLength: 40 })),
    h('label', { class: 'full' }, 'Source', h('input', { name: 'source', value: c.source || '', maxLength: 60 })),
    h('div', { class: 'row-end full' },
      h('button', { type: 'button', class: 'danger', onclick: safe(async () => {
        if (!confirm(`Delete ${c.name} and their ${deals.length} deal(s)?`)) return;
        await api(`/contacts/${id}`, { method: 'DELETE' }); toast('Contact deleted'); closeDrawer(); refresh();
      }) }, 'Delete'),
      h('button', { type: 'submit', class: 'primary' }, 'Save changes')));
  const total = deals.reduce((a, d) => a + d.value, 0);
  openDrawer(
    drawerHead(h('span', { class: 'who' }, avatar(c.name), c.name), `${c.company || 'No company'} · added ${date(c.created_at)}`),
    form,
    h('div', { class: 'section' },
      h('h3', { style: 'display:flex;justify-content:space-between' }, `Deals (${deals.length} · ${money(total)})`,
        h('button', { type: 'button', onclick: () => dealModal(c.id) }, '+ Deal')),
      deals.length ? h('div', { class: 'col-body' }, deals.map(d => dealCard({ ...d, contact_name: c.name, company: c.company })))
        : h('div', { class: 'empty' }, 'No deals for this contact yet')));
});

/* ---------- modals ---------- */
function modal(title, ...content) {
  const m = $('#modal');
  m.replaceChildren(h('h2', {}, title), ...content);
  m.showModal();
  return m;
}
const cancelBtn = () => h('button', { type: 'button', onclick: () => $('#modal').close() }, 'Cancel');

function contactModal() {
  modal('New contact', h('form', { class: 'form-grid', onsubmit: safe(async e => {
    e.preventDefault();
    const c = await api('/contacts', { method: 'POST', body: nullify(formData(e.target)) });
    $('#modal').close(); toast(`Added ${c.name}`); refresh(); openContact(c.id);
  }) },
    h('label', {}, 'Name *', h('input', { name: 'name', required: true, maxLength: 120, autofocus: true })),
    h('label', {}, 'Email *', h('input', { name: 'email', type: 'email', required: true, maxLength: 255 })),
    h('label', {}, 'Company', h('input', { name: 'company', maxLength: 160 })),
    h('label', {}, 'Phone', h('input', { name: 'phone', maxLength: 40 })),
    h('label', { class: 'full' }, 'Source', h('select', { name: 'source' }, ['', 'website', 'referral', 'linkedin', 'conference', 'cold_outreach', 'webinar']
      .map(v => h('option', { value: v }, v ? v.replace('_', ' ') : '—')))),
    h('div', { class: 'row-end full' }, cancelBtn(), h('button', { type: 'submit', class: 'primary' }, 'Create contact'))));
}

const dealModal = safe(async contactId => {
  const contacts = await api('/contacts?limit=200');
  if (!contacts.length) { toast('Add a contact first', true); return contactModal(); }
  modal('New deal', h('form', { class: 'form-grid', onsubmit: safe(async e => {
    e.preventDefault();
    const f = formData(e.target);
    const d = await api('/deals', { method: 'POST', body: { ...f, contact_id: +f.contact_id, value: +f.value || 0, owner: f.owner || null } });
    $('#modal').close(); toast('Deal created'); refresh(); openDeal(d.id);
  }) },
    h('label', { class: 'full' }, 'Title *', h('input', { name: 'title', required: true, maxLength: 160, autofocus: true, placeholder: 'e.g. Annual subscription' })),
    h('label', { class: 'full' }, 'Contact *', h('select', { name: 'contact_id', required: true },
      [...contacts].sort((a, b) => a.name.localeCompare(b.name)).map(c => h('option', { value: c.id, selected: c.id === contactId }, `${c.name}${c.company ? ' — ' + c.company : ''}`)))),
    h('label', {}, 'Value (USD)', h('input', { name: 'value', type: 'number', min: 0, step: 100, value: 0 })),
    h('label', {}, 'Owner', h('input', { name: 'owner', maxLength: 80 })),
    h('label', { class: 'full' }, 'Stage', h('select', { name: 'stage' }, STAGES.map(st => h('option', {}, st)))),
    h('div', { class: 'row-end full' }, cancelBtn(), h('button', { type: 'submit', class: 'primary' }, 'Create deal'))));
});

function importModal() {
  const result = h('div', { class: 'result' });
  const text = h('textarea', { rows: 6, placeholder: 'name,email,company,phone,source\nJane Doe,jane@example.com,Example Inc,,referral' });
  const readFile = file => file && file.text().then(t => { text.value = t; });
  const drop = h('div', { class: 'drop',
    ondragover: e => { e.preventDefault(); drop.classList.add('over'); },
    ondragleave: () => drop.classList.remove('over'),
    ondrop: e => { e.preventDefault(); drop.classList.remove('over'); readFile(e.dataTransfer.files[0]); } },
    'Drop a .csv file here or ', h('label', { style: 'display:inline;color:var(--accent);cursor:pointer;font-size:inherit' }, 'browse',
      h('input', { type: 'file', accept: '.csv,text/csv', hidden: true, onchange: e => readFile(e.target.files[0]) })));
  modal('Import leads from CSV',
    h('p', { class: 'muted', style: 'margin-top:0' }, 'Required columns: name, email. Optional: company, phone, source. Existing emails are skipped.'),
    drop, h('div', { style: 'margin-top:10px' }, text), result,
    h('div', { class: 'row-end' }, cancelBtn(), h('button', { type: 'button', class: 'primary', onclick: safe(async () => {
      if (!text.value.trim()) return toast('Paste CSV or choose a file', true);
      const r = await api('/contacts/import', { method: 'POST', body: text.value, headers: { 'Content-Type': 'text/csv' } });
      result.replaceChildren(h('b', {}, `${r.created} imported`), ` · ${r.skipped_duplicates} duplicates skipped · ${r.errors.length} errors`,
        r.errors.length ? h('ul', { class: 'muted' }, r.errors.slice(0, 5).map(er => h('li', {}, `Row ${er.row}: ${er.reason}`))) : null);
      toast(`Imported ${r.created} contacts`); refresh();
    }) }, 'Import')));
}

/* ---------- boot ---------- */
$('#overlay').addEventListener('click', closeDrawer);
document.addEventListener('keydown', e => { if (e.key === 'Escape' && $('#drawer').classList.contains('open')) closeDrawer(); });
$('#new-contact').addEventListener('click', contactModal);
$('#new-deal').addEventListener('click', () => dealModal());
$('#theme').addEventListener('click', () => {
  const dark = document.documentElement.dataset.theme
    ? document.documentElement.dataset.theme === 'dark'
    : matchMedia('(prefers-color-scheme: dark)').matches;
  document.documentElement.dataset.theme = dark ? 'light' : 'dark';
  try { localStorage.setItem('crm-theme', document.documentElement.dataset.theme); } catch (_) { /* storage unavailable */ }
});
window.addEventListener('hashchange', () => { $('#view').replaceChildren(); route(); });
route();
