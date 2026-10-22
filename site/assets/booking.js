/* Anavah booking + manage pages. No dependencies. */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var TZ = 'America/New_York';
  var MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];

  function api(path, opts) {
    opts = opts || {};
    if (opts.body && typeof opts.body !== 'string') { opts.body = JSON.stringify(opts.body); opts.headers = { 'Content-Type': 'application/json' }; }
    return fetch(path, opts).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (!r.ok) { var e = new Error(typeof d.detail === 'string' ? d.detail : 'Please check your details and try again.'); e.status = r.status; throw e; }
        return d;
      });
    });
  }
  function todayStr() { return new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(new Date()); }
  function fmtTime(iso) { return new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZone: TZ }); }
  function fmtLong(iso) { return new Date(iso).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', timeZone: TZ }) + ' at ' + fmtTime(iso) + ' ET'; }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function show(id, on) { $(id).hidden = !on; }

  // ---------- slot picker (month grid + times) ----------
  function Picker(slug, onPick) {
    var now = todayStr().split('-').map(Number);
    var year = now[0], month = now[1] - 1, cache = {}, loaded = {}, selDay = null;
    $('tzNote').textContent = 'All times are Eastern Time (New York).';

    function load(y, m) {
      var key = y + '-' + m;
      if (loaded[key]) return Promise.resolve();
      var first = y + '-' + String(m + 1).padStart(2, '0') + '-01';
      var start = first < todayStr() ? todayStr() : first;
      return api('/api/public/slots?type=' + encodeURIComponent(slug) + '&start=' + start + '&days=31').then(function (d) {
        Object.keys(d.days).forEach(function (k) { cache[k] = d.days[k]; });
        loaded[key] = true;
      });
    }
    function render() {
      $('calMonth').textContent = MONTHS[month] + ' ' + year;
      var grid = $('calGrid'); grid.innerHTML = '';
      var firstDow = (new Date(Date.UTC(year, month, 1)).getUTCDay() + 6) % 7; // Monday = 0
      var dim = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
      for (var i = 0; i < firstDow; i++) grid.appendChild(el('span', 'cal-pad'));
      for (var d = 1; d <= dim; d++) {
        var ds = year + '-' + String(month + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0');
        var b = el('button', 'cal-day', String(d)); b.type = 'button';
        if (cache[ds]) { b.classList.add('avail'); if (ds === selDay) b.classList.add('sel'); b.addEventListener('click', pickDay.bind(null, ds)); }
        else b.disabled = true;
        grid.appendChild(b);
      }
      var cur = now[0] * 12 + now[1] - 1;
      $('calPrev').disabled = year * 12 + month <= cur;
    }
    function pickDay(ds) {
      selDay = ds; render();
      var parts = ds.split('-').map(Number);
      $('slotDay').textContent = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2], 12)).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', timeZone: 'UTC' });
      var list = $('slotList'); list.innerHTML = '';
      cache[ds].forEach(function (iso) {
        var b = el('button', 'slot', fmtTime(iso)); b.type = 'button';
        b.addEventListener('click', function () { onPick(iso); });
        list.appendChild(b);
      });
    }
    function go(delta) {
      month += delta; if (month < 0) { month = 11; year--; } if (month > 11) { month = 0; year++; }
      $('calMonth').textContent = 'Loading…';
      load(year, month).then(render).catch(function () { render(); });
    }
    $('calPrev').onclick = function () { go(-1); };
    $('calNext').onclick = function () { go(1); };
    $('slotList').innerHTML = ''; $('slotDay').textContent = 'Select a date';
    return load(year, month).then(function () {
      // jump to the first month that has availability
      var keys = Object.keys(cache).sort();
      if (!keys.length) { return load(year + (month === 11 ? 1 : 0), (month + 1) % 12).then(function () { var k = Object.keys(cache).sort(); if (k.length) { var p = k[0].split('-'); year = +p[0]; month = +p[1] - 1; } render(); if (!k.length) $('slotDay').textContent = 'No open times right now — please call (216) 625-0028.'; }); }
      render();
    }).catch(function () { render(); $('slotDay').textContent = 'Could not load times. Please refresh or call (216) 625-0028.'; });
  }

  // ---------- booking page ----------
  function initBooking() {
    var state = { cfg: null, aud: 'patient', type: null, start: null };
    var steps = $('bkSteps').children;
    function goStep(n) {
      ['stepType', 'stepTime', 'stepDetails', 'stepDone'].forEach(function (id, i) { show(id, i + 1 === n); });
      for (var i = 0; i < steps.length; i++) steps[i].classList.toggle('on', i + 1 <= n);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    function renderTypes() {
      var list = $('typeList'); list.innerHTML = '';
      var types = state.cfg.types.filter(function (t) { return t.audience === state.aud; });
      if (!types.length) list.appendChild(el('p', 'muted', 'No online visit types are available right now. Please call (216) 625-0028.'));
      types.forEach(function (t) {
        var b = el('button', 'type-card'); b.type = 'button';
        b.appendChild(el('strong', null, t.name));
        b.appendChild(el('span', 'dur', t.duration_min + ' min'));
        if (t.description) b.appendChild(el('span', 'desc', t.description));
        b.addEventListener('click', function () { chooseType(t); });
        list.appendChild(b);
      });
    }
    function chooseType(t) {
      state.type = t; state.start = null;
      $('timeTitle').textContent = 'Pick a time — ' + t.name;
      goStep(2);
      Picker(t.slug, function (iso) {
        state.start = iso;
        $('sumBox').innerHTML = '';
        $('sumBox').appendChild(el('strong', null, t.name));
        $('sumBox').appendChild(el('span', null, fmtLong(iso) + ' · ' + t.duration_min + ' min'));
        $('modeGroup').hidden = t.mode !== 'either';
        goStep(3);
      });
    }
    document.querySelectorAll('[data-back]').forEach(function (b) { b.addEventListener('click', function () { goStep(+b.dataset.back); }); });
    $('audTabs').addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return;
      state.aud = b.dataset.aud;
      Array.prototype.forEach.call($('audTabs').children, function (x) { x.classList.toggle('on', x === b); });
      renderTypes();
    });

    $('bookForm').addEventListener('submit', function (e) {
      e.preventDefault();
      var f = e.target, err = $('bkError'); err.hidden = true;
      var body = {
        type: state.type.slug, start: state.start, first_name: f.first_name.value.trim(), last_name: f.last_name.value.trim(),
        email: f.email.value.trim(), phone: f.phone.value.trim(), message: f.message.value.trim(),
        mode: (f.mode && f.mode.value) || 'telehealth', sms_consent: f.sms_consent.checked, ack: f.ack.checked, website: f.website.value
      };
      if (!body.first_name || !body.last_name || !/^\S+@\S+\.\S+$/.test(body.email)) { err.textContent = 'Please enter your name and a valid email.'; err.hidden = false; return; }
      if (!body.ack) { err.textContent = 'Please check the box confirming this isn’t for emergencies.'; err.hidden = false; return; }
      var btn = $('bkSubmit'); btn.disabled = true; btn.firstChild.textContent = 'Booking… ';
      api('/api/public/book', { method: 'POST', body: body }).then(function (d) {
        if (!d.appointment) { goStep(4); return; }
        var a = d.appointment;
        $('doneText').textContent = a.type + ' on ' + fmtLong(a.start_at) + '.';
        $('doneIcs').href = a.ics_url; $('doneManage').href = '/manage?t=' + a.token;
        goStep(4);
      }).catch(function (ex) {
        err.textContent = ex.message; err.hidden = false;
        if (ex.status === 409) { setTimeout(function () { chooseType(state.type); }, 1800); }
      }).then(function () { btn.disabled = false; btn.firstChild.textContent = 'Confirm appointment '; });
    });

    api('/api/public/config').then(function (cfg) {
      state.cfg = cfg; TZ = cfg.timezone || TZ; renderTypes();
      var q = new URLSearchParams(location.search).get('type');
      var pre = q && cfg.types.filter(function (t) { return t.slug === q; })[0];
      if (pre) { state.aud = pre.audience; Array.prototype.forEach.call($('audTabs').children, function (x) { x.classList.toggle('on', x.dataset.aud === pre.audience); }); renderTypes(); chooseType(pre); }
    }).catch(function () { $('typeList').innerHTML = '<p class="muted">Couldn’t load visit types. Please refresh or call (216) 625-0028.</p>'; });
  }

  // ---------- manage page ----------
  function initManage() {
    var token = new URLSearchParams(location.search).get('t');
    var appt = null, armed = false;
    function panels(which) { ['mLoading', 'mMissing', 'mView', 'mPick'].forEach(function (id) { show(id, id === which); }); }
    function load() {
      if (!token) return panels('mMissing');
      api('/api/public/config').then(function (c) { TZ = c.timezone || TZ; return api('/api/public/appointment?t=' + encodeURIComponent(token)); }).then(function (a) {
        appt = a; var live = a.status === 'confirmed' || a.status === 'pending';
        var s = $('mSummary'); s.innerHTML = '';
        s.appendChild(el('strong', null, a.type));
        s.appendChild(el('span', null, fmtLong(a.start_at) + (a.mode === 'telehealth' ? ' · Telehealth' : ' · In person, Chelsea, Manhattan')));
        s.appendChild(el('span', 'status s-' + a.status, a.status === 'no_show' ? 'No show' : a.status.charAt(0).toUpperCase() + a.status.slice(1)));
        $('mActions').hidden = !live; $('mIcs').href = a.ics_url;
        $('mNote').textContent = live ? 'Need something else? Call (216) 625-0028.' : 'This appointment is no longer active. You can book a new visit anytime.';
        if (!live) { var l = el('a', 'btn btn-gold', 'Book a new visit'); l.href = '/book'; $('mNote').after(l); }
        panels('mView');
      }).catch(function () { panels('mMissing'); });
    }
    $('mCancel').addEventListener('click', function () {
      var b = $('mCancel'), err = $('mError'); err.hidden = true;
      if (!armed) { armed = true; b.textContent = 'Tap again to confirm cancellation'; setTimeout(function () { armed = false; b.textContent = 'Cancel appointment'; }, 6000); return; }
      api('/api/public/appointment/cancel?t=' + encodeURIComponent(token), { method: 'POST' }).then(function () { location.reload(); })
        .catch(function (e) { err.textContent = e.message; err.hidden = false; });
    });
    $('mResched').addEventListener('click', function () {
      panels('mPick');
      Picker(appt.type_slug, function (iso) {
        api('/api/public/appointment/reschedule?t=' + encodeURIComponent(token), { method: 'POST', body: { start: iso } })
          .then(function () { location.reload(); })
          .catch(function (e) { alert(e.message); });
      });
    });
    $('mPickBack').addEventListener('click', function () { panels('mView'); });
    load();
  }

  if ($('bookApp')) initBooking();
  if ($('manageApp')) initManage();
})();
