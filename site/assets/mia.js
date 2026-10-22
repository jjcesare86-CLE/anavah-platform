/**
 * Mia — Anavah Institute assistant widget (text + voice).
 * Text:  POST /api/chat  (Claude + knowledge base, server-side)
 * Voice: ElevenLabs Agents via @elevenlabs/client; session credentials from GET /api/voice/session.
 * Voice client tools the agent can call: navigate_to({section}), open_booking({type_slug})
 */
(function () {
  'use strict';
  var PHONE = '(216) 625-0028', TEL = 'tel:+12166250028';
  var SDK = 'https://cdn.jsdelivr.net/npm/@elevenlabs/client@1.27.0/+esm';
  var SECTIONS = ['top', 'mission', 'services', 'about', 'appointments', 'insurance', 'contact'];

  var root = document.createElement('div'); root.id = 'mia';
  root.innerHTML =
    '<button class="mia-fab" id="miaFab" aria-label="Chat with Mia" aria-expanded="false"><span class="mia-fab-ring"></span><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 12a8 8 0 0 1-8 8H8l-5 3 1.2-4.2A8 8 0 1 1 21 12z"/></svg><span class="mia-fab-label">Talk to Mia</span></button>' +
    '<div class="mia-panel" id="miaPanel" role="dialog" aria-label="Mia assistant" hidden>' +
      '<div class="mia-head"><div class="mia-avatar">M</div><div><div class="mia-name">Mia</div><div class="mia-sub">Anavah Institute · AI assistant</div></div><button class="mia-close" id="miaClose" aria-label="Close">×</button></div>' +
      '<div class="mia-crisis">Not for emergencies. Call 911, or call/text 988 for crisis support. Please don\u2019t share health details here.</div>' +
      '<div class="mia-log" id="miaLog" aria-live="polite"></div>' +
      '<div class="mia-chips" id="miaChips">' +
        '<button data-q="How do I schedule a consultation?">Schedule a consultation</button>' +
        '<button data-q="What services do you offer?">Services</button>' +
        '<button data-q="Do you take insurance?">Insurance</button>' +
        '<button data-q="How can I contact the office?">Contact</button>' +
      '</div>' +
      '<form class="mia-input" id="miaForm"><input id="miaText" type="text" placeholder="Ask Mia anything…" autocomplete="off" maxlength="500" aria-label="Message"><button type="submit" aria-label="Send"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4z"/></svg></button></form>' +
      '<div class="mia-voice"><button id="miaVoice" class="mia-voice-btn" type="button"><span class="mia-mic"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/></svg></span><span id="miaVoiceLabel">Talk with Mia by voice</span></button><span class="mia-voice-note">AI assistant. Please don’t share health details. Emergency? Call 911 / 988.</span></div>' +
    '</div>';
  document.body.appendChild(root);

  var fab = root.querySelector('#miaFab'), panel = root.querySelector('#miaPanel'), log = root.querySelector('#miaLog'),
      form = root.querySelector('#miaForm'), input = root.querySelector('#miaText'), chips = root.querySelector('#miaChips'),
      voiceBtn = root.querySelector('#miaVoice'), voiceLabel = root.querySelector('#miaVoiceLabel');
  var history = [], open = false;

  function togglePanel(state) {
    open = state === undefined ? !open : state;
    panel.hidden = !open; fab.classList.toggle('open', open); fab.setAttribute('aria-expanded', String(open));
    if (open && !log.children.length) add('mia', "Hi, I'm Mia, Anavah's virtual assistant. I can help you find your way around, answer questions, or get a visit booked. What would be helpful?");
    if (open) setTimeout(function () { input.focus(); }, 50);
  }
  fab.addEventListener('click', function () { togglePanel(); });
  root.querySelector('#miaClose').addEventListener('click', function () { togglePanel(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && open) togglePanel(false); });

  function add(role, text, actions) {
    var el = document.createElement('div'); el.className = 'mia-msg ' + role;
    var b = document.createElement('div'); b.className = 'mia-bubble'; b.textContent = text; el.appendChild(b);
    if (actions && actions.length) {
      var row = document.createElement('div'); row.className = 'mia-actions';
      actions.forEach(function (a) {
        var l = document.createElement('a'); l.className = 'mia-action'; l.textContent = a.label; l.href = a.href || '#';
        if (a.onclick) l.addEventListener('click', a.onclick);
        row.appendChild(l);
      });
      el.appendChild(row);
    }
    log.appendChild(el); log.scrollTop = log.scrollHeight; return el;
  }
  function typing() { var el = add('mia', ''); el.classList.add('typing'); el.firstChild.innerHTML = '<span></span><span></span><span></span>'; return el; }

  // ---------- navigation helpers ----------
  function goSection(id) {
    id = String(id || '').replace(/^#/, '');
    if (SECTIONS.indexOf(id) < 0) return false;
    var target = document.getElementById(id);
    if (target) { target.scrollIntoView({ behavior: 'smooth', block: 'start' }); return true; }
    location.href = '/#' + id; return true;
  }
  function bookUrl() { return '/book'; }  // consultation page; it links to the Google Calendar scheduler

  function toActions(tokens) {
    var out = [];
    (tokens || []).forEach(function (t) {
      if (t.indexOf('nav:') === 0) { var id = t.slice(4); out.push({ label: 'Show me ↓', href: '/' + id, onclick: function (e) { e.preventDefault(); goSection(id); } }); goSection(id); }
      else if (t.indexOf('book') === 0) out.push({ label: 'Schedule a consultation →', href: bookUrl(t.split(':')[1]) });
      else if (t === 'call') out.push({ label: 'Call ' + PHONE, href: TEL });
    });
    return out;
  }

  // ---------- text ----------
  function send(q) {
    q = (q || '').trim(); if (!q) return;
    add('user', q); history.push({ role: 'user', content: q }); chips.hidden = true;
    var t = typing();
    fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ messages: history.slice(-12) }) })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(function (d) { t.remove(); add('mia', d.reply, toActions(d.actions)); history.push({ role: 'assistant', content: d.reply }); })
      .catch(function () { t.remove(); add('mia', "I'm having trouble right now. You can call the office at " + PHONE + " or schedule a consultation online.", [{ label: 'Call ' + PHONE, href: TEL }, { label: 'Schedule online →', href: '/book' }]); });
  }
  form.addEventListener('submit', function (e) { e.preventDefault(); var v = input.value; input.value = ''; send(v); });
  chips.addEventListener('click', function (e) { var b = e.target.closest('button'); if (b) send(b.dataset.q); });

  // ---------- voice (ElevenLabs Agents) ----------
  var conv = null, starting = false;
  function setIdle() { conv = null; voiceBtn.classList.remove('live'); voiceLabel.textContent = 'Talk with Mia by voice'; }
  function lastRole(p) { return (p.source === 'user' || p.role === 'user') ? 'user' : 'mia'; }

  voiceBtn.addEventListener('click', function () {
    if (conv) { conv.endSession(); return; }
    if (starting) return;
    starting = true; voiceLabel.textContent = 'Connecting…';
    var fail = function (msg) { starting = false; setIdle(); add('mia', msg, [{ label: 'Call ' + PHONE, href: TEL }]); };
    fetch('/api/voice/session').then(function (r) { return r.json(); }).then(function (s) {
      if (!s.enabled) return fail('Voice isn’t available right now. I’m happy to help by text, or you can call the office.');
      return Promise.all([import(SDK), navigator.mediaDevices.getUserMedia({ audio: true })]).then(function (res) {
        var cfg = {
          clientTools: {
            navigate_to: function (p) { return goSection(p && p.section) ? 'Scrolled to ' + p.section : 'Unknown section'; },
            open_booking: function (p) { var u = bookUrl(p && p.type_slug); add('mia', 'Here’s the scheduling page.', [{ label: 'Schedule a consultation →', href: u }]); setTimeout(function () { location.href = u; }, 1500); return 'Opening the booking page'; }
          },
          onConnect: function () { starting = false; voiceBtn.classList.add('live'); voiceLabel.textContent = 'Listening… tap to end'; },
          onDisconnect: function () { setIdle(); add('mia', 'Voice conversation ended. I’m still here by text if you need me.'); },
          onError: function () { fail('Voice ran into a problem. Let’s continue by text, or call the office.'); },
          onMessage: function (p) { if (p && p.message) add(lastRole(p), p.message); },
          onModeChange: function (m) { if (conv) voiceLabel.textContent = (m.mode === 'speaking' ? 'Mia is speaking…' : 'Listening…') + ' tap to end'; }
        };
        if (s.signedUrl) cfg.signedUrl = s.signedUrl; else { cfg.agentId = s.agentId; cfg.connectionType = 'webrtc'; }
        return res[0].Conversation.startSession(cfg).then(function (c) { conv = c; starting = false; });
      });
    }).catch(function (e) {
      var denied = e && (e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError');
      fail(denied ? 'I need microphone access to talk. You can allow it in your browser, or we can chat by text.' : 'I couldn’t start voice just now. Let’s continue by text.');
    });
  });

  document.addEventListener('click', function (e) { var t = e.target.closest('[data-mia="open"]'); if (t) { e.preventDefault(); togglePanel(true); } });
})();
