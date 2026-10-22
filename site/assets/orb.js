/**
 * Anavah — Interactive Orb v1.2
 * Nodes orbit the core continuously. Hover/click/focus a node → orbit pauses,
 * its ring lights up, info card appears. Leave → card hides, orbit resumes.
 * Click locks; click again (or click elsewhere) releases.
 */
(function () {
  'use strict';
  var stage = document.getElementById('orbStage');
  if (!stage) return;
  var orb = document.getElementById('orb'), card = document.getElementById('orbCard');
  var label = document.getElementById('orbCardLabel'), title = document.getElementById('orbCardTitle'), text = document.getElementById('orbCardText');

  var CONTENT = {
    mind:  { label: '01 \u00b7 Mind', title: 'Integrative Psychiatry',
             text: 'PMHNP-led evaluations, medication management, and lifestyle psychiatry \u2014 every decision informed by the patient\u2019s full physical picture.' },
    body:  { label: '02 \u00b7 Body', title: 'Physical Medicine',
             text: 'Exercise physiology, functional nutrition, and physical-therapy alignment \u2014 movement and fuel prescribed like medicine.' },
    coord: { label: '03 \u00b7 Coordination', title: 'The Anavah Signature',
             text: 'Structured hand-offs between psychiatry, PT, PCP, and attorneys, with shared documentation so nothing falls through the cracks.' }
  };

  // Orbit paths: radius x/y (px at 300px orb), tilt (deg), period (s), starting phase
  var ORBITS = {
    mind:  { rx: 205, ry: 70,  tilt: -18, period: 22, phase: 0 },
    body:  { rx: 150, ry: 118, tilt: 55,  period: 17, phase: 2.1 },
    coord: { rx: 108, ry: 44,  tilt: 20,  period: 12, phase: 4.2 }
  };

  var nodes = {}, hovered = null, locked = null, paused = false;
  stage.querySelectorAll('.orb-node').forEach(function (n) { nodes[n.dataset.node] = n; });

  function scale() { return orb.getBoundingClientRect().width / 300; }

  var t0 = performance.now();
  function frame(now) {
    if (!paused) {
      var t = (now - t0) / 1000, k = scale();
      for (var key in ORBITS) {
        var o = ORBITS[key], a = (t / o.period) * Math.PI * 2 + o.phase;
        var x = Math.cos(a) * o.rx * k, y = Math.sin(a) * o.ry * k;
        var r = o.tilt * Math.PI / 180;
        var X = x * Math.cos(r) - y * Math.sin(r), Y = x * Math.sin(r) + y * Math.cos(r);
        var depth = (Math.sin(a) + 1) / 2;               // 0 = back, 1 = front
        var n = nodes[key];
        n.style.transform = 'translate(-50%,-50%) translate(' + X.toFixed(1) + 'px,' + Y.toFixed(1) + 'px) scale(' + (0.8 + depth * 0.35).toFixed(3) + ')';
        n.style.zIndex = depth > 0.5 ? 5 : 3;
        n.style.opacity = stage.hasAttribute('data-active') && !n.classList.contains('active') ? 0.3 : (0.55 + depth * 0.45).toFixed(2);
      }
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  function show(node) {
    stage.setAttribute('data-active', node);
    for (var k in nodes) nodes[k].classList.toggle('active', k === node);
    var c = CONTENT[node]; label.textContent = c.label; title.textContent = c.title; text.textContent = c.text;
    paused = true;
  }
  function hide() {
    stage.removeAttribute('data-active');
    for (var k in nodes) nodes[k].classList.remove('active');
    paused = false;
  }

  for (var key in nodes) (function (node, el) {
    el.addEventListener('mouseenter', function () { hovered = node; show(node); });
    el.addEventListener('mouseleave', function () { hovered = null; if (!locked) hide(); });
    el.addEventListener('focus', function () { show(node); });
    el.addEventListener('blur',  function () { if (!locked) hide(); });
    el.addEventListener('click', function (e) {
      e.preventDefault(); e.stopPropagation();
      if (locked === node) { locked = null; hide(); } else { locked = node; show(node); }
    });
  })(key, nodes[key]);

  document.addEventListener('click', function (e) {
    if (locked && !stage.contains(e.target)) { locked = null; hide(); }
  });

  // Cursor tilt on the whole orb (desktop)
  if (window.matchMedia('(pointer:fine)').matches) {
    stage.addEventListener('mousemove', function (e) {
      var r = stage.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
      orb.style.transform = 'rotateY(' + (x * 24) + 'deg) rotateX(' + (-y * 24) + 'deg)';
    });
    stage.addEventListener('mouseleave', function () { orb.style.transform = ''; });
  }
})();

/* --- 3D tilt for service figures --- */
(function () {
  if (!window.matchMedia('(pointer:fine)').matches) return;
  document.querySelectorAll('[data-tilt]').forEach(function (el) {
    el.addEventListener('mousemove', function (e) {
      var r = el.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
      el.style.transform = 'rotateY(' + (x * 14) + 'deg) rotateX(' + (-y * 14) + 'deg)';
    });
    el.addEventListener('mouseleave', function () { el.style.transform = ''; });
  });
})();
