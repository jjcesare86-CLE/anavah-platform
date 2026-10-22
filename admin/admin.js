/* Anavah Admin — vanilla JS SPA. All dynamic text is set via textContent (no innerHTML with data). */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var TZ = 'America/New_York', ME = null, TOKEN = null;
  try { TOKEN = sessionStorage.getItem('anv_tok'); } catch (e) {}

  // ---------- helpers ----------
  function h(tag, attrs) {
    var el = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v == null || v === false) return;
      if (k === 'class') el.className = v;
      else if (k.slice(0, 2) === 'on') el.addEventListener(k.slice(2), v);
      else if (k === 'value') el.value = v;
      else if (k === 'checked' || k === 'disabled' || k === 'selected' || k === 'hidden') el[k] = !!v;
      else el.setAttribute(k, v === true ? '' : v);
    });
    for (var i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }
  function add(el, c) {
    if (c == null || c === false) return;
    if (Array.isArray(c)) return c.forEach(function (x) { add(el, x); });
    el.appendChild(typeof c === 'object' ? c : document.createTextNode(String(c)));
  }
  function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }
  function toast(msg, bad) { var t = $('toast'); t.textContent = msg; t.className = 'on' + (bad ? ' bad' : ''); clearTimeout(toast.t); toast.t = setTimeout(function () { t.className = ''; }, 3200); }
  function api(path, opts) {
    opts = opts || {};
    var o = { method: opts.method || 'GET', headers: { Authorization: 'Bearer ' + TOKEN } };
    if (opts.body !== undefined) { o.body = JSON.stringify(opts.body); o.headers['Content-Type'] = 'application/json'; }
    return fetch('/api/admin' + path, o).then(function (r) {
      if (r.status === 401 && path !== '/login') { logout(); throw new Error('Session expired'); }
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : 'Request failed');
        return d;
      });
    });
  }
  function fail(e) { toast(e.message || 'Something went wrong', true); }
  function fmtDT(iso) { return new Date(iso).toLocaleString('en-US', { timeZone: TZ, weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }); }
  function fmtT(iso) { return new Date(iso).toLocaleTimeString('en-US', { timeZone: TZ, hour: 'numeric', minute: '2-digit' }); }
  function localParts(iso) {
    var p = {}; new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
      .formatToParts(new Date(iso)).forEach(function (x) { p[x.type] = x.value; });
    return { date: p.year + '-' + p.month + '-' + p.day, min: (+p.hour) * 60 + (+p.minute) };
  }
  function todayStr() { return new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(new Date()); }
  function addDays(ds, n) { var d = new Date(ds + 'T12:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); }
  function mondayOf(ds) { var d = new Date(ds + 'T12:00:00Z'); return addDays(ds, -((d.getUTCDay() + 6) % 7)); }
  function pill(s) { return h('span', { class: 'pill ' + s }, String(s).replace('_', ' ')); }
  function cname(c) { return ((c.first_name || '') + ' ' + (c.last_name || '')).trim() || c.email || 'Unnamed'; }
  function field(label, input) { return h('label', null, label, input); }
  function chk(label, name, val) { return h('label', { class: 'chk' }, h('input', { type: 'checkbox', name: name, checked: val }), label); }

  // ---------- dialog ----------
  var dlg = $('dlg');
  function modal(title, body) {
    var b = clear($('dlgBody'));
    b.appendChild(h('div', { class: 'dlg-head' }, h('h2', null, title), h('button', { class: 'x', 'aria-label': 'Close', onclick: closeModal }, '×')));
    add(b, body);
    if (!dlg.open) dlg.showModal();
  }
  function closeModal() { if (dlg.open) dlg.close(); }
  dlg.addEventListener('click', function (e) { if (e.target === dlg) closeModal(); });

  // ---------- auth ----------
  function logout() { TOKEN = null; try { sessionStorage.removeItem('anv_tok'); } catch (e) {} $('app').hidden = true; $('login').hidden = false; }
  $('logout').addEventListener('click', logout);
  $('loginForm').addEventListener('submit', function (e) {
    e.preventDefault();
    var f = e.target, err = $('loginErr'); err.hidden = true;
    fetch('/api/admin/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: f.email.value, password: f.password.value }) })
      .then(function (r) { return r.json().then(function (d) { if (!r.ok) throw new Error(d.detail || 'Sign-in failed'); return d; }); })
      .then(function (d) { TOKEN = d.access_token; try { sessionStorage.setItem('anv_tok', TOKEN); } catch (x) {} f.password.value = ''; boot(); })
      .catch(function (x) { err.textContent = x.message; err.hidden = false; });
  });

  function boot() {
    if (!TOKEN) { $('login').hidden = false; return; }
    api('/me').then(function (me) {
      ME = me; TZ = me.timezone || TZ;
      $('login').hidden = true; $('app').hidden = false; $('who').textContent = me.email;
      var b = clear($('banner'));
      if (me.dry_run) b.appendChild(h('div', { class: 'banner warn' }, 'Dry-run mode is ON — messages are logged but not actually sent. Set OUTREACH_DRY_RUN=false in Render when you are ready to go live.'));
      if (!me.business_address_set) b.appendChild(h('div', { class: 'banner warn' }, 'BUSINESS_ADDRESS is not set. Outreach emails are blocked until you add the practice mailing address (required by CAN-SPAM).'));
      if (!me.ghl) b.appendChild(h('div', { class: 'banner info' }, 'Go High Level is not connected yet (GHL_TOKEN / GHL_LOCATION_ID). Emails and texts will not send until it is.'));
      route();
    }).catch(function () { logout(); });
  }

  // ---------- router ----------
  var routes = { dashboard: vDashboard, calendar: vCalendar, clients: vClients, prospects: vProspects, outreach: vOutreach, messages: vMessages, settings: vSettings };
  function route() {
    var r = (location.hash.replace('#/', '') || 'dashboard').split('?')[0];
    if (!routes[r]) r = 'dashboard';
    Array.prototype.forEach.call($('nav').children, function (a) { a.classList.toggle('on', a.dataset.r === r); });
    var v = clear($('view'));
    routes[r](v);
  }
  window.addEventListener('hashchange', route);

  function head(title, tools) { return h('div', { class: 'head' }, h('h1', null, title), h('div', { class: 'tools' }, tools)); }
  function empty(t) { return h('div', { class: 'empty' }, t); }

  // ---------- dashboard ----------
  function vDashboard(v) {
    v.appendChild(head('Dashboard', h('button', { class: 'btn gold', onclick: function () { newAppt(); } }, '+ New appointment')));
    api('/dashboard').then(function (d) {
      var s = d.stats;
      v.appendChild(h('div', { class: 'cards' }, [['Today', s.today], ['Next 7 days', s.week], ['New leads', s.new_leads], ['Active clients', s.active_clients], ['Open prospects', s.prospects_open], ['Messages today', s.messages_today]]
        .map(function (x) { return h('div', { class: 'stat' }, h('b', null, x[1]), h('span', null, x[0])); })));
      function apptTable(list, none) {
        if (!list.length) return empty(none);
        return h('table', null, list.map(function (a) {
          return h('tr', { class: 'click', onclick: function () { apptDialog(a.id, a); } }, h('td', null, fmtDT(a.start_at)), h('td', null, a.client_name), h('td', { class: 'muted' }, a.type_name), h('td', null, pill(a.status)));
        }));
      }
      v.appendChild(h('div', { class: 'grid2' },
        h('div', { class: 'panel' }, h('h3', null, "Today's appointments"), apptTable(d.today, 'Nothing scheduled today.')),
        h('div', { class: 'panel' }, h('h3', null, 'Upcoming'), apptTable(d.upcoming, 'No upcoming appointments.'))));
      v.appendChild(h('div', { class: 'panel' }, h('h3', null, 'Newest clients & leads'),
        d.recent_clients.length ? h('table', null, d.recent_clients.map(function (c) {
          return h('tr', { class: 'click', onclick: function () { clientDialog(c.id); } }, h('td', null, cname(c)), h('td', { class: 'muted' }, c.email || c.phone || ''), h('td', { class: 'muted' }, c.source), h('td', null, pill(c.status)));
        })) : empty('No clients yet.')));
    }).catch(fail);
  }

  // ---------- calendar ----------
  var weekStart = null, H0 = 7, H1 = 20;
  function vCalendar(v) {
    weekStart = weekStart || mondayOf(todayStr());
    var tools = [
      h('button', { class: 'btn', onclick: function () { weekStart = addDays(weekStart, -7); route(); } }, '‹ Prev'),
      h('button', { class: 'btn', onclick: function () { weekStart = mondayOf(todayStr()); route(); } }, 'This week'),
      h('button', { class: 'btn', onclick: function () { weekStart = addDays(weekStart, 7); route(); } }, 'Next ›'),
      h('button', { class: 'btn gold', onclick: function () { newAppt(); } }, '+ New appointment')];
    v.appendChild(head('Calendar', tools));
    var end = addDays(weekStart, 6);
    api('/appointments?start=' + weekStart + '&end=' + end).then(function (d) {
      var hrs = H1 - H0, today = todayStr();
      var grid = h('div', { class: 'wk-grid', style: '--hrs:' + hrs });
      grid.appendChild(h('div', { class: 'wk-h' }));
      var days = [];
      for (var i = 0; i < 7; i++) {
        var ds = addDays(weekStart, i); days.push(ds);
        var dt = new Date(ds + 'T12:00:00Z');
        grid.appendChild(h('div', { class: 'wk-h' + (ds === today ? ' today' : '') }, dt.toLocaleDateString('en-US', { weekday: 'short', timeZone: 'UTC' }), h('b', null, dt.getUTCDate())));
      }
      var tcol = h('div', { class: 'wk-t' });
      for (var k = 0; k < hrs; k++) tcol.appendChild(h('span', { style: 'top:' + (k * 52) + 'px' }, k === 0 ? '' : new Date(Date.UTC(2000, 0, 1, H0 + k)).toLocaleTimeString('en-US', { hour: 'numeric', timeZone: 'UTC' })));
      grid.appendChild(tcol);
      days.forEach(function (ds) {
        var col = h('div', { class: 'wk-c' });
        function place(start, endIso, cls, content, onclick) {
          var s = localParts(start), e = localParts(endIso);
          if (s.date !== ds) return;
          var top = (s.min - H0 * 60) / 60 * 52, dur = (new Date(endIso) - new Date(start)) / 60000;
          if (top + dur / 60 * 52 < 0) return;
          col.appendChild(h('div', { class: 'ev ' + cls, style: 'top:' + Math.max(0, top) + 'px;height:' + Math.max(20, dur / 60 * 52 - 2) + 'px', onclick: onclick }, content));
        }
        d.appointments.forEach(function (a) {
          place(a.start_at, a.end_at, a.status, [h('b', null, a.client_name), fmtT(a.start_at) + ' · ' + a.type_name], function () { apptDialog(a.id, a); });
        });
        d.time_off.forEach(function (o) {
          var s = localParts(o.start_at), e = localParts(o.end_at);
          if (s.date <= ds && e.date >= ds) {
            var a0 = s.date === ds ? s.min : 0, a1 = e.date === ds ? e.min : 24 * 60;
            col.appendChild(h('div', { class: 'ev off', style: 'top:' + Math.max(0, (a0 - H0 * 60) / 60 * 52) + 'px;height:' + Math.max(18, (a1 - a0) / 60 * 52) + 'px' }, o.reason || 'Time off'));
          }
        });
        grid.appendChild(col);
      });
      v.appendChild(h('div', { class: 'week' }, grid));
      v.appendChild(h('p', { class: 'muted' }, 'Times shown in ' + TZ.replace('_', ' ') + '. Click an appointment to view, reschedule or update it. Set working hours and time off in Settings.'));
    }).catch(fail);
  }

  function slotPicker(typeSlug, dateStr, onPick, box) {
    clear(box);
    if (!typeSlug || !dateStr) return;
    fetch('/api/public/slots?type=' + encodeURIComponent(typeSlug) + '&start=' + dateStr + '&days=1').then(function (r) { return r.json(); }).then(function (d) {
      var list = d.days && d.days[dateStr];
      if (!list) { box.appendChild(h('p', { class: 'muted' }, 'No open times that day.')); return; }
      var wrap = h('div', { class: 'slots' });
      list.forEach(function (iso) {
        var b = h('button', { type: 'button' }, fmtT(iso));
        b.addEventListener('click', function () { Array.prototype.forEach.call(wrap.children, function (x) { x.classList.remove('on'); }); b.classList.add('on'); onPick(iso); });
        wrap.appendChild(b);
      });
      box.appendChild(wrap);
    });
  }

  function newAppt(prefillClient) {
    Promise.all([api('/schedule'), prefillClient ? Promise.resolve(null) : api('/clients?limit=500')]).then(function (res) {
      var types = res[0].types.filter(function (t) { return t.active; }), clients = res[1] ? res[1].clients.filter(function (c) { return c.status !== 'archived'; }) : [];
      var picked = null, startIso = null;
      var sel = h('select', { name: 'client' }, h('option', { value: '' }, '— New client —'), clients.map(function (c) { return h('option', { value: c.id, selected: prefillClient === c.id }, cname(c) + (c.email ? ' · ' + c.email : '')); }));
      var ty = h('select', { name: 'type' }, types.map(function (t) { return h('option', { value: t.id, 'data-slug': t.slug, 'data-mode': t.mode }, t.name + ' (' + t.duration_min + ' min)'); }));
      var date = h('input', { type: 'date', name: 'date', value: todayStr() });
      var slots = h('div');
      var newBox = h('div', { class: 'row' }, field('First name', h('input', { name: 'fn' })), field('Last name', h('input', { name: 'ln' })), field('Email', h('input', { name: 'em', type: 'email' })), field('Phone', h('input', { name: 'ph' })));
      var mode = h('select', { name: 'mode' }, h('option', { value: 'telehealth' }, 'Telehealth'), h('option', { value: 'in_person' }, 'In person'));
      var notes = h('textarea', { name: 'notes', placeholder: 'Internal notes (no clinical details)' });
      var notify = chk('Email the client a confirmation', 'notify', true);
      function refresh() { startIso = null; var o = ty.options[ty.selectedIndex]; slotPicker(o && o.dataset.slug, date.value, function (iso) { startIso = iso; }, slots); }
      ty.addEventListener('change', refresh); date.addEventListener('change', refresh);
      sel.addEventListener('change', function () { newBox.hidden = !!sel.value; });
      newBox.hidden = !!(sel.value);
      var err = h('p', { class: 'err', hidden: true });
      var save = h('button', { class: 'btn primary', onclick: function () {
        err.hidden = true;
        if (!startIso) { err.textContent = 'Pick a time.'; err.hidden = false; return; }
        var f = function (n) { return newBox.querySelector('[name=' + n + ']').value.trim(); };
        api('/appointments', { method: 'POST', body: { client_id: sel.value || null, first_name: f('fn'), last_name: f('ln'), email: f('em'), phone: f('ph'), type_id: ty.value, start: startIso, mode: mode.value, notes: notes.value, notify: notify.firstChild.checked } })
          .then(function () { closeModal(); toast('Appointment booked'); route(); }).catch(function (e) { err.textContent = e.message; err.hidden = false; });
      } }, 'Book appointment');
      modal('New appointment', [field('Client', sel), newBox, h('div', { class: 'row' }, field('Visit type', ty), field('Date', date)), h('label', null, 'Open times'), slots, h('div', { class: 'row', style: 'margin-top:14px' }, field('Format', mode)), field('Notes', notes), notify, err, h('div', { class: 'actions' }, save, h('button', { class: 'btn', onclick: closeModal }, 'Cancel'))]);
      refresh();
    }).catch(fail);
  }

  function apptDialog(id, a) {
    var notes = h('textarea', { value: a.notes || '' });
    function setStatus(s) { api('/appointments/' + id, { method: 'PATCH', body: { status: s, notes: notes.value } }).then(function () { closeModal(); toast('Updated'); route(); }).catch(fail); }
    var rbox = h('div'), rdate = h('input', { type: 'date', value: localParts(a.start_at).date }), newStart = null, rWrap = h('div', { hidden: true });
    api('/schedule').then(function (s) {
      var t = s.types.filter(function (x) { return x.id === a.type_id; })[0];
      if (!t) return;
      function load() { slotPicker(t.slug, rdate.value, function (iso) { newStart = iso; }, rbox); }
      rdate.addEventListener('change', load); load();
    });
    rWrap.appendChild(h('div', null, field('New date', rdate), rbox, h('div', { class: 'actions' }, h('button', { class: 'btn primary sm', onclick: function () {
      if (!newStart) return toast('Pick a new time', true);
      api('/appointments/' + id, { method: 'PATCH', body: { start: newStart } }).then(function () { closeModal(); toast('Rescheduled'); route(); }).catch(fail);
    } }, 'Move appointment'))));
    modal(a.type_name, [
      h('p', null, h('strong', null, fmtDT(a.start_at) + ' – ' + fmtT(a.end_at)), ' ', pill(a.status)),
      h('p', null, h('a', { href: '#', onclick: function (e) { e.preventDefault(); clientDialog(a.client_id); } }, a.client_name), h('span', { class: 'muted' }, ' · ' + (a.client_email || '') + ' ' + (a.client_phone || '') + ' · ' + (a.mode === 'telehealth' ? 'Telehealth' : 'In person'))),
      a.client_message ? h('p', null, h('span', { class: 'muted' }, 'Client note: '), a.client_message) : null,
      field('Internal notes', notes),
      h('div', { class: 'actions' },
        h('button', { class: 'btn primary', onclick: function () { api('/appointments/' + id, { method: 'PATCH', body: { notes: notes.value } }).then(function () { toast('Saved'); }).catch(fail); } }, 'Save notes'),
        h('button', { class: 'btn', onclick: function () { rWrap.hidden = !rWrap.hidden; } }, 'Reschedule'),
        h('button', { class: 'btn', onclick: function () { setStatus('completed'); } }, 'Mark completed'),
        h('button', { class: 'btn', onclick: function () { setStatus('no_show'); } }, 'No-show'),
        h('button', { class: 'btn danger', onclick: function () { setStatus('cancelled'); } }, 'Cancel appointment')),
      rWrap]);
  }

  // ---------- clients ----------
  function vClients(v) {
    var q = h('input', { placeholder: 'Search name, email, phone…', style: 'width:260px' });
    var st = h('select', { style: 'width:150px' }, ['', 'lead', 'active', 'inactive', 'archived'].map(function (s) { return h('option', { value: s }, s ? s : 'All statuses'); }));
    var body = h('div', { class: 'panel' });
    function load() {
      api('/clients?q=' + encodeURIComponent(q.value) + '&status=' + st.value).then(function (d) {
        clear(body);
        if (!d.clients.length) return body.appendChild(empty('No clients match.'));
        body.appendChild(h('table', null, h('tr', null, ['Name', 'Contact', 'Status', 'Source', 'Consent'].map(function (x) { return h('th', null, x); })),
          d.clients.map(function (c) {
            return h('tr', { class: 'click', onclick: function () { clientDialog(c.id); } }, h('td', null, cname(c)), h('td', { class: 'muted' }, [c.email, c.phone].filter(Boolean).join(' · ')), h('td', null, pill(c.status)), h('td', { class: 'muted' }, c.source),
              h('td', { class: 'muted' }, (c.do_not_contact ? 'DNC ' : '') + (c.email_consent ? '✉ ' : '') + (c.sms_consent ? '✆' : '')));
          })));
      }).catch(fail);
    }
    var t;
    q.addEventListener('input', function () { clearTimeout(t); t = setTimeout(load, 250); }); st.addEventListener('change', load);
    v.appendChild(head('Clients', [q, st, h('button', { class: 'btn', onclick: function () { download('/export/clients.csv', 'clients.csv'); } }, 'Export CSV'), h('button', { class: 'btn gold', onclick: function () { clientDialog(null); } }, '+ Add client')]));
    v.appendChild(body); load();
  }
  function download(path, name) {
    fetch('/api/admin' + path, { headers: { Authorization: 'Bearer ' + TOKEN } }).then(function (r) { return r.blob(); }).then(function (b) {
      var a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = name; a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
    }).catch(fail);
  }

  function clientDialog(id) {
    var p = id ? api('/clients/' + id) : Promise.resolve({ client: { status: 'lead', tags: [], source: 'manual' }, appointments: [], notes: [], messages: [] });
    p.then(function (d) {
      var c = d.client, f = h('form', null);
      f.appendChild(h('div', { class: 'row' }, field('First name', h('input', { name: 'first_name', value: c.first_name || '' })), field('Last name', h('input', { name: 'last_name', value: c.last_name || '' }))));
      f.appendChild(h('div', { class: 'row' }, field('Email', h('input', { name: 'email', type: 'email', value: c.email || '' })), field('Phone', h('input', { name: 'phone', value: c.phone || '' }))));
      f.appendChild(h('div', { class: 'row' }, field('Status', h('select', { name: 'status' }, ['lead', 'active', 'inactive', 'archived'].map(function (s) { return h('option', { value: s, selected: c.status === s }, s); }))), field('Tags (comma separated)', h('input', { name: 'tags', value: (c.tags || []).join(', ') }))));
      f.appendChild(h('div', { class: 'row' }, chk('Agreed to emails', 'email_consent', c.email_consent), chk('Agreed to texts (SMS)', 'sms_consent', c.sms_consent)));
      f.appendChild(chk('Do not contact', 'do_not_contact', c.do_not_contact));
      f.appendChild(field('Notes (no clinical details)', h('textarea', { name: 'notes', value: c.notes || '' })));
      var save = h('button', { class: 'btn primary', type: 'submit' }, id ? 'Save changes' : 'Create client');
      f.appendChild(h('div', { class: 'actions' }, save,
        id ? h('button', { class: 'btn', type: 'button', onclick: function () { closeModal(); newAppt(id); } }, 'Book appointment') : null,
        id ? h('button', { class: 'btn', type: 'button', onclick: function () { closeModal(); outreachPrefill = { type: 'client', id: id }; location.hash = '#/outreach'; } }, 'Send message') : null,
        id && c.status !== 'archived' ? h('button', { class: 'btn danger', type: 'button', onclick: function () { api('/clients/' + id, { method: 'DELETE' }).then(function () { closeModal(); toast('Archived'); route(); }).catch(fail); } }, 'Archive') : null));
      f.addEventListener('submit', function (e) {
        e.preventDefault();
        var g = function (n) { return f.elements[n]; };
        var body = { first_name: g('first_name').value.trim(), last_name: g('last_name').value.trim(), email: g('email').value.trim(), phone: g('phone').value.trim(), status: g('status').value,
          tags: g('tags').value.split(',').map(function (x) { return x.trim(); }).filter(Boolean), email_consent: g('email_consent').checked, sms_consent: g('sms_consent').checked, do_not_contact: g('do_not_contact').checked, notes: g('notes').value };
        (id ? api('/clients/' + id, { method: 'PATCH', body: body }) : api('/clients', { method: 'POST', body: body })).then(function () { closeModal(); toast('Saved'); route(); }).catch(fail);
      });
      var extra = [];
      if (id) {
        var nt = h('input', { placeholder: 'Add a note…' });
        extra.push(h('h3', { style: 'margin-top:26px' }, 'Notes'),
          h('div', { class: 'row', style: 'grid-template-columns:1fr auto;margin-top:8px' }, nt, h('button', { class: 'btn', type: 'button', onclick: function () { if (!nt.value.trim()) return; api('/clients/' + id + '/notes', { method: 'POST', body: { body: nt.value } }).then(function () { clientDialog(id); }).catch(fail); } }, 'Add')),
          h('div', { class: 'timeline' }, d.notes.map(function (n) { return h('div', { class: 'tl' }, n.body, h('small', null, fmtDT(n.created_at) + (n.created_by ? ' · ' + n.created_by : ''))); })),
          h('h3', { style: 'margin-top:22px' }, 'Appointments'),
          d.appointments.length ? h('table', null, d.appointments.map(function (a) { return h('tr', { class: 'click', onclick: function () { apptDialog(a.id, Object.assign({ client_name: cname(c), client_email: c.email, client_phone: c.phone }, a)); } }, h('td', null, fmtDT(a.start_at)), h('td', { class: 'muted' }, a.type_name), h('td', null, pill(a.status))); })) : h('p', { class: 'muted' }, 'None yet.'),
          h('h3', { style: 'margin-top:22px' }, 'Messages'),
          d.messages.length ? h('table', null, d.messages.slice(0, 10).map(function (m) { return h('tr', null, h('td', null, fmtDT(m.created_at)), h('td', { class: 'muted' }, m.channel + ' · ' + m.kind), h('td', null, m.subject || m.body.slice(0, 40)), h('td', null, pill(m.status))); })) : h('p', { class: 'muted' }, 'None yet.'));
      }
      modal(id ? cname(c) : 'Add client', [f, extra]);
    }).catch(fail);
  }

  // ---------- prospects ----------
  var CATS = ['provider', 'attorney', 'pt', 'pcp', 'organization', 'other'], PST = ['new', 'contacted', 'replied', 'meeting', 'won', 'lost'];
  function vProspects(v) {
    var q = h('input', { placeholder: 'Search…', style: 'width:220px' });
    var st = h('select', { style: 'width:140px' }, [''].concat(PST).map(function (s) { return h('option', { value: s }, s || 'All statuses'); }));
    var ct = h('select', { style: 'width:150px' }, [''].concat(CATS).map(function (s) { return h('option', { value: s }, s || 'All categories'); }));
    var body = h('div', { class: 'panel' });
    function load() {
      api('/prospects?q=' + encodeURIComponent(q.value) + '&status=' + st.value + '&category=' + ct.value).then(function (d) {
        clear(body);
        if (!d.prospects.length) return body.appendChild(empty('No prospects yet. Add one, or import a CSV.'));
        body.appendChild(h('table', null, h('tr', null, ['Name', 'Organization', 'Category', 'Email', 'Status', ''].map(function (x) { return h('th', null, x); })),
          d.prospects.map(function (p) {
            var sel = h('select', { class: 'sm', onchange: function () { api('/prospects/' + p.id, { method: 'PATCH', body: { status: sel.value } }).then(function () { toast('Updated'); }).catch(fail); } }, PST.map(function (s) { return h('option', { value: s, selected: p.status === s }, s); }));
            return h('tr', null, h('td', null, h('a', { href: '#', onclick: function (e) { e.preventDefault(); prospectDialog(p); } }, p.name), p.role ? h('div', { class: 'muted' }, p.role) : null), h('td', null, p.organization), h('td', { class: 'muted' }, p.category), h('td', { class: 'muted' }, (p.email || '') + (p.do_not_contact ? ' (DNC)' : '')), h('td', null, sel),
              h('td', null, h('button', { class: 'btn sm', onclick: function () { outreachPrefill = { type: 'prospect', id: p.id }; location.hash = '#/outreach'; } }, 'Email')));
          })));
      }).catch(fail);
    }
    var t; q.addEventListener('input', function () { clearTimeout(t); t = setTimeout(load, 250); }); st.addEventListener('change', load); ct.addEventListener('change', load);
    v.appendChild(head('Prospects', [q, st, ct, h('button', { class: 'btn', onclick: importDialog }, 'Import CSV'), h('button', { class: 'btn gold', onclick: function () { prospectDialog(null); } }, '+ Add prospect')]));
    v.appendChild(h('p', { class: 'muted' }, 'Referral partners and organizations: providers, PTs, PCPs, attorneys, employers.'));
    v.appendChild(body); load();
  }
  function prospectDialog(p) {
    var f = h('form', null);
    p = p || { category: 'provider', status: 'new' };
    f.appendChild(h('div', { class: 'row' }, field('Name', h('input', { name: 'name', value: p.name || '', required: true })), field('Organization', h('input', { name: 'organization', value: p.organization || '' }))));
    f.appendChild(h('div', { class: 'row' }, field('Role', h('input', { name: 'role', value: p.role || '' })), field('Category', h('select', { name: 'category' }, CATS.map(function (s) { return h('option', { value: s, selected: p.category === s }, s); })))));
    f.appendChild(h('div', { class: 'row' }, field('Email', h('input', { name: 'email', type: 'email', value: p.email || '' })), field('Phone', h('input', { name: 'phone', value: p.phone || '' }))));
    f.appendChild(field('Notes', h('textarea', { name: 'notes', value: p.notes || '' })));
    f.appendChild(chk('Do not contact', 'do_not_contact', p.do_not_contact));
    f.appendChild(h('div', { class: 'actions' }, h('button', { class: 'btn primary', type: 'submit' }, 'Save'),
      p.id ? h('button', { class: 'btn danger', type: 'button', onclick: function () { api('/prospects/' + p.id, { method: 'DELETE' }).then(function () { closeModal(); route(); }).catch(fail); } }, 'Delete') : null));
    f.addEventListener('submit', function (e) {
      e.preventDefault(); var g = function (n) { return f.elements[n]; };
      var body = { name: g('name').value, organization: g('organization').value, role: g('role').value, category: g('category').value, email: g('email').value, phone: g('phone').value, notes: g('notes').value, do_not_contact: g('do_not_contact').checked };
      (p.id ? api('/prospects/' + p.id, { method: 'PATCH', body: body }) : api('/prospects', { method: 'POST', body: body })).then(function () { closeModal(); toast('Saved'); route(); }).catch(fail);
    });
    modal(p.id ? p.name : 'Add prospect', f);
  }
  function importDialog() {
    var ta = h('textarea', { placeholder: 'name,organization,role,email,phone,category\nDr. Jane Lee,Lee Physical Therapy,Owner,jane@example.com,,pt', style: 'min-height:160px' });
    var file = h('input', { type: 'file', accept: '.csv,text/csv' });
    file.addEventListener('change', function () { var r = new FileReader(); r.onload = function () { ta.value = r.result; }; if (file.files[0]) r.readAsText(file.files[0]); });
    modal('Import prospects', [h('p', { class: 'muted' }, 'Paste or upload a CSV with a header row. Columns: name, organization, role, email, phone, category (provider, attorney, pt, pcp, organization, other), notes. Duplicates by email are skipped. Only import professional contacts you have a legitimate reason to email.'), file, ta,
      h('div', { class: 'actions' }, h('button', { class: 'btn primary', onclick: function () { api('/prospects/import', { method: 'POST', body: { csv: ta.value } }).then(function (r) { closeModal(); toast('Imported ' + r.added + ', skipped ' + r.skipped); route(); }).catch(fail); } }, 'Import'))]);
  }

  // ---------- outreach ----------
  var outreachPrefill = null;
  function vOutreach(v) {
    var pre = outreachPrefill; outreachPrefill = null;
    v.appendChild(head('Outreach'));
    var state = { people: [], tpls: [] };
    var channel = h('select', null, h('option', { value: 'email' }, 'Email'), h('option', { value: 'sms' }, 'Text (SMS)'));
    var aud = h('select', null, h('option', { value: 'client' }, 'Clients'), h('option', { value: 'prospect' }, 'Prospects'));
    var statusF = h('select', null, h('option', { value: '' }, 'All statuses'));
    var tplSel = h('select', null, h('option', { value: '' }, '— Start from a template —'));
    var subj = h('input', { placeholder: 'Subject' }), msg = h('textarea', { style: 'min-height:170px', placeholder: 'Hello {{first_name}}, …' });
    var list = h('div', { class: 'picklist' }), out = h('div'), count = h('span', { class: 'muted' });
    function statuses() { clear(statusF); statusF.appendChild(h('option', { value: '' }, 'All statuses')); (aud.value === 'client' ? ['lead', 'active', 'inactive'] : PST).forEach(function (s) { statusF.appendChild(h('option', { value: s }, s)); }); }
    function eligible(p) {
      if (p.do_not_contact) return 'do not contact';
      if (channel.value === 'email') { if (!p.email) return 'no email'; if (aud.value === 'client' && !p.email_consent) return 'no email consent'; }
      else { if (aud.value === 'prospect') return 'SMS to prospects disabled'; if (!p.phone) return 'no phone'; if (!p.sms_consent) return 'no SMS consent'; }
      return '';
    }
    function loadPeople() {
      api((aud.value === 'client' ? '/clients' : '/prospects') + '?status=' + statusF.value + (aud.value === 'client' && !statusF.value ? '' : '')).then(function (d) {
        state.people = (d.clients || d.prospects).filter(function (p) { return p.status !== 'archived'; }); drawList();
      }).catch(fail);
    }
    function drawList() {
      clear(list);
      if (!state.people.length) list.appendChild(empty('No one here yet.'));
      state.people.forEach(function (p) {
        var why = eligible(p), cb = h('input', { type: 'checkbox', value: p.id, disabled: !!why, checked: !why && pre && pre.id === p.id });
        cb.addEventListener('change', tally);
        list.appendChild(h('label', null, cb, h('span', null, p.name || cname(p)), h('span', { class: 'muted' }, why ? '— ' + why : (aud.value === 'client' ? p.email || p.phone : p.organization || p.email))));
      });
      tally();
    }
    function chosen() { return Array.prototype.filter.call(list.querySelectorAll('input:checked'), function (x) { return !x.disabled; }).map(function (x) { return { type: aud.value, id: x.value }; }); }
    function tally() { count.textContent = chosen().length + ' selected'; }
    function run(preview) {
      var recs = chosen();
      if (!recs.length) return toast('Select at least one recipient', true);
      if (!msg.value.trim()) return toast('Write a message first', true);
      if (!preview && !window.confirm((ME.dry_run ? '[DRY RUN — nothing will actually be sent]\n\n' : '') + 'Send to ' + recs.length + ' recipient(s)?')) return;
      api('/outreach/send', { method: 'POST', body: { channel: channel.value, subject: subj.value, body: msg.value, recipients: recs.slice(0, preview ? 3 : 200), preview: preview } }).then(function (r) {
        clear(out);
        if (preview) { r.results.forEach(function (x) { out.appendChild(h('div', { class: 'panel' }, h('strong', null, 'To: ' + x.name + ' <' + x.to + '>'), x.subject ? h('div', null, 'Subject: ' + x.subject) : null, h('pre', { class: 'preview' }, x.body))); }); return; }
        out.appendChild(h('div', { class: 'panel' }, h('h3', null, (r.dry_run ? 'Dry run complete' : 'Send complete')), h('p', null, Object.keys(r.summary).map(function (k) { return [pill(k), ' ' + r.summary[k] + '  ']; })),
          h('table', null, r.results.filter(function (x) { return x.status !== 'sent' && x.status !== 'dry_run'; }).map(function (x) { return h('tr', null, h('td', null, x.name || x.id), h('td', { class: 'muted' }, x.error)); }))));
      }).catch(fail);
    }
    channel.addEventListener('change', function () { subj.hidden = channel.value === 'sms'; loadTpls(); drawList(); });
    aud.addEventListener('change', function () { statuses(); loadPeople(); }); statusF.addEventListener('change', loadPeople);
    function loadTpls() { clear(tplSel); tplSel.appendChild(h('option', { value: '' }, '— Start from a template —')); state.tpls.filter(function (t) { return t.channel === channel.value; }).forEach(function (t) { tplSel.appendChild(h('option', { value: t.id }, t.name)); }); }
    tplSel.addEventListener('change', function () { var t = state.tpls.filter(function (x) { return x.id === tplSel.value; })[0]; if (t) { subj.value = t.subject; msg.value = t.body; } });
    api('/templates').then(function (d) { state.tpls = d.templates; loadTpls(); }).catch(fail);
    if (pre) { aud.value = pre.type; }
    statuses(); loadPeople();
    v.appendChild(h('div', { class: 'grid2' },
      h('div', { class: 'panel' }, h('h3', null, '1 · Who'), h('div', { class: 'row3' }, field('Channel', channel), field('Audience', aud), field('Status', statusF)),
        h('div', { class: 'actions', style: 'margin:0 0 8px' }, h('button', { class: 'btn sm', onclick: function () { list.querySelectorAll('input:not(:disabled)').forEach(function (x) { x.checked = true; }); tally(); } }, 'Select all eligible'), h('button', { class: 'btn sm', onclick: function () { list.querySelectorAll('input').forEach(function (x) { x.checked = false; }); tally(); } }, 'Clear'), count), list,
        h('p', { class: 'muted small' }, 'Clients must have agreed to emails/texts. People marked do-not-contact or unsubscribed are skipped automatically.')),
      h('div', { class: 'panel' }, h('h3', null, '2 · Message'), field('Template', tplSel), h('div', { style: 'height:12px' }), field('Subject', subj), h('div', { style: 'height:12px' }), field('Body', msg),
        h('p', { class: 'muted small' }, 'Merge fields: {{first_name}} {{booking_link}} {{phone}}. Never include health information. Email gets an unsubscribe link and your mailing address automatically; texts get "Reply STOP".'),
        h('div', { class: 'actions' }, h('button', { class: 'btn', onclick: function () { run(true); } }, 'Preview'), h('button', { class: 'btn primary', onclick: function () { run(false); } }, ME.dry_run ? 'Dry-run send' : 'Send')))));
    v.appendChild(out);
    v.appendChild(templatesPanel(state));
  }
  function templatesPanel(state) {
    var box = h('div', { class: 'panel' }, h('h3', null, 'Templates'));
    function draw() {
      api('/templates').then(function (d) {
        state.tpls = d.templates; var keep = box.firstChild; clear(box); box.appendChild(keep);
        box.appendChild(h('table', null, d.templates.map(function (t) { return h('tr', null, h('td', null, t.name), h('td', { class: 'muted' }, t.channel), h('td', { class: 'muted' }, t.subject), h('td', null, h('button', { class: 'btn sm', onclick: function () { tplDialog(t, draw); } }, 'Edit'))); })));
        box.appendChild(h('div', { class: 'actions' }, h('button', { class: 'btn sm', onclick: function () { tplDialog(null, draw); } }, '+ New template')));
      }).catch(fail);
    }
    draw(); return box;
  }
  function tplDialog(t, done) {
    var ch = h('select', { disabled: !!t }, h('option', { value: 'email' }, 'Email'), h('option', { value: 'sms' }, 'SMS')); if (t) ch.value = t.channel;
    var nm = h('input', { value: t ? t.name : '' }), sj = h('input', { value: t ? t.subject : '' }), bd = h('textarea', { value: t ? t.body : '', style: 'min-height:180px' });
    modal(t ? 'Edit template' : 'New template', [field('Name', nm), field('Channel', ch), field('Subject (email)', sj), field('Body', bd), h('div', { class: 'actions' },
      h('button', { class: 'btn primary', onclick: function () { (t ? api('/templates/' + t.id, { method: 'PATCH', body: { name: nm.value, subject: sj.value, body: bd.value } }) : api('/templates', { method: 'POST', body: { name: nm.value, channel: ch.value, subject: sj.value, body: bd.value } })).then(function () { closeModal(); done(); }).catch(fail); } }, 'Save'),
      t ? h('button', { class: 'btn danger', onclick: function () { api('/templates/' + t.id, { method: 'DELETE' }).then(function () { closeModal(); done(); }).catch(fail); } }, 'Delete') : null)]);
  }

  // ---------- messages ----------
  function vMessages(v) {
    v.appendChild(head('Message log'));
    api('/messages?limit=200').then(function (d) {
      v.appendChild(h('div', { class: 'panel' }, d.messages.length ? h('table', null, h('tr', null, ['When', 'To', 'Kind', 'Subject / text', 'Status'].map(function (x) { return h('th', null, x); })), d.messages.map(function (m) {
        return h('tr', null, h('td', null, fmtDT(m.created_at)), h('td', { class: 'muted' }, m.channel + ' · ' + m.to_address), h('td', { class: 'muted' }, m.kind), h('td', { title: m.error || '' }, (m.subject || m.body).slice(0, 70), m.error ? h('div', { class: 'muted small' }, m.error) : null), h('td', null, pill(m.status)));
      })) : empty('No messages yet.')));
    }).catch(fail);
  }

  // ---------- settings ----------
  var WD = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  function vSettings(v) {
    v.appendChild(head('Settings'));
    api('/schedule').then(function (s) {
      // weekly hours
      var rules = {}; WD.forEach(function (_, i) { rules[i] = []; });
      s.rules.forEach(function (r) { rules[r.weekday].push({ start: r.start_time, end: r.end_time, active: r.active }); });
      var hoursBox = h('div');
      function drawHours() {
        clear(hoursBox);
        WD.forEach(function (name, i) {
          var row = h('div', { class: 'row', style: 'grid-template-columns:110px 1fr;align-items:start;margin-bottom:8px' }, h('strong', null, name));
          var rs = h('div');
          if (!rules[i].length) rs.appendChild(h('span', { class: 'muted' }, 'Closed '));
          rules[i].forEach(function (r, j) {
            rs.appendChild(h('div', { style: 'display:flex;gap:8px;align-items:center;margin-bottom:6px' },
              h('input', { type: 'time', value: r.start, style: 'width:130px', onchange: function (e) { r.start = e.target.value; } }), '–',
              h('input', { type: 'time', value: r.end, style: 'width:130px', onchange: function (e) { r.end = e.target.value; } }),
              h('button', { class: 'btn sm', onclick: function () { rules[i].splice(j, 1); drawHours(); } }, 'Remove')));
          });
          rs.appendChild(h('button', { class: 'btn sm', onclick: function () { rules[i].push({ start: '09:00', end: '17:00', active: true }); drawHours(); } }, '+ Add hours'));
          row.appendChild(rs); hoursBox.appendChild(row);
        });
      }
      drawHours();
      v.appendChild(h('div', { class: 'panel' }, h('h3', null, 'Weekly hours'), h('p', { class: 'muted' }, 'When clients can book (' + TZ.replace('_', ' ') + '). The starter hours are placeholders — set Phillip\'s real availability, then save.'), hoursBox,
        h('div', { class: 'actions' }, h('button', { class: 'btn primary', onclick: function () {
          var out = []; WD.forEach(function (_, i) { rules[i].forEach(function (r) { out.push({ weekday: i, start_time: r.start, end_time: r.end, active: true }); }); });
          api('/schedule/rules', { method: 'PUT', body: { rules: out } }).then(function () { toast('Hours saved'); }).catch(fail);
        } }, 'Save hours'))));

      // booking rules
      var cfg = s.booking, mn = h('input', { type: 'number', value: cfg.min_notice_hours }), ma = h('input', { type: 'number', value: cfg.max_advance_days }), st = h('input', { type: 'number', value: cfg.slot_step_min });
      v.appendChild(h('div', { class: 'panel' }, h('h3', null, 'Booking rules'), h('div', { class: 'row3' }, field('Minimum notice (hours)', mn), field('Book up to (days ahead)', ma), field('Time slot spacing (minutes)', st)),
        h('div', { class: 'actions' }, h('button', { class: 'btn primary', onclick: function () { api('/schedule/booking', { method: 'PUT', body: { min_notice_hours: mn.value, max_advance_days: ma.value, slot_step_min: st.value } }).then(function () { toast('Saved'); }).catch(fail); } }, 'Save rules'))));

      // visit types
      var typeBox = h('div', { class: 'panel' }, h('h3', null, 'Visit types'), h('p', { class: 'muted' }, 'Durations are starter placeholders — set the real lengths. "Buffer" is blocked time after the visit.'));
      var tbl = h('table', null, h('tr', null, ['Name', 'For', 'Minutes', 'Buffer', 'Format', 'Online', ''].map(function (x) { return h('th', null, x); })));
      s.types.forEach(function (t) {
        var nm = h('input', { value: t.name }), du = h('input', { type: 'number', value: t.duration_min, style: 'width:80px' }), bu = h('input', { type: 'number', value: t.buffer_after_min, style: 'width:70px' });
        var au = h('select', null, ['patient', 'provider'].map(function (x) { return h('option', { value: x, selected: t.audience === x }, x); }));
        var mo = h('select', null, [['either', 'Either'], ['telehealth', 'Telehealth only'], ['in_person', 'In person only']].map(function (x) { return h('option', { value: x[0], selected: t.mode === x[0] }, x[1]); }));
        var ac = h('input', { type: 'checkbox', checked: t.active });
        tbl.appendChild(h('tr', null, h('td', null, nm), h('td', null, au), h('td', null, du), h('td', null, bu), h('td', null, mo), h('td', null, ac),
          h('td', null, h('button', { class: 'btn sm', onclick: function () { api('/types/' + t.id, { method: 'PATCH', body: { name: nm.value, audience: au.value, duration_min: du.value, buffer_after_min: bu.value, mode: mo.value, active: ac.checked } }).then(function () { toast('Saved'); }).catch(fail); } }, 'Save'))));
      });
      typeBox.appendChild(tbl);
      typeBox.appendChild(h('div', { class: 'actions' }, h('button', { class: 'btn sm', onclick: function () {
        var nm = h('input'), du = h('input', { type: 'number', value: 30 });
        modal('New visit type', [field('Name', nm), field('Minutes', du), h('div', { class: 'actions' }, h('button', { class: 'btn primary', onclick: function () { api('/types', { method: 'POST', body: { name: nm.value, duration_min: +du.value } }).then(function () { closeModal(); route(); }).catch(fail); } }, 'Create'))]);
      } }, '+ New visit type')));
      v.appendChild(typeBox);

      // time off
      var offBox = h('div', { class: 'panel' }, h('h3', null, 'Time off & blocked time'));
      var os = h('input', { type: 'datetime-local' }), oe = h('input', { type: 'datetime-local' }), orr = h('input', { placeholder: 'Reason (optional)' });
      offBox.appendChild(s.time_off.length ? h('table', null, s.time_off.map(function (o) { return h('tr', null, h('td', null, fmtDT(o.start_at) + ' → ' + fmtDT(o.end_at)), h('td', { class: 'muted' }, o.reason), h('td', null, h('button', { class: 'btn sm', onclick: function () { api('/schedule/time-off/' + o.id, { method: 'DELETE' }).then(route).catch(fail); } }, 'Remove'))); })) : h('p', { class: 'muted' }, 'Nothing scheduled.'));
      offBox.appendChild(h('div', { class: 'row3', style: 'margin-top:14px' }, field('From', os), field('To', oe), field('Reason', orr)));
      offBox.appendChild(h('div', { class: 'actions' }, h('button', { class: 'btn primary', onclick: function () { api('/schedule/time-off', { method: 'POST', body: { start: os.value, end: oe.value, reason: orr.value } }).then(function () { toast('Added'); route(); }).catch(fail); } }, 'Block this time')));
      v.appendChild(offBox);

      // integrations
      var st2 = h('p', { class: 'muted' }, 'Go High Level: ' + (ME.ghl ? 'configured' : 'not configured') + ' · Dry-run: ' + (ME.dry_run ? 'ON' : 'off') + ' · Mailing address: ' + (ME.business_address_set ? 'set' : 'missing'));
      v.appendChild(h('div', { class: 'panel' }, h('h3', null, 'Integrations'), st2, h('div', { class: 'actions' },
        h('button', { class: 'btn', onclick: function () { api('/ghl/test', { method: 'POST' }).then(function (r) { toast('Connected to GHL: ' + (r.location || 'ok')); }).catch(fail); } }, 'Test GHL connection'),
        h('button', { class: 'btn', onclick: function () { api('/ghl/sync', { method: 'POST' }).then(function (r) { toast('Synced ' + r.synced + ' clients' + (r.failed.length ? ' — ' + r.failed[0] : ''), !!r.failed.length); }).catch(fail); } }, 'Sync clients to GHL'))));
    }).catch(fail);
  }

  boot();
})();
