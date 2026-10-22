/**
 * Anavah Institute — Main JS
 * Nav scroll state + reveal-on-scroll animations
 */
(function() {
  'use strict';

  // Nav scroll state
  const nav = document.getElementById('nav') || document.querySelector('.site-nav');
  if (nav) {
    window.addEventListener('scroll', function() {
      nav.classList.toggle('scrolled', window.scrollY > 20);
    }, { passive: true });
  }

  // Hero video (optional): plays only if the clip exists, motion is allowed, and the connection is not slow or data-saving.
  // Otherwise the animated clouds image stays as the hero background.
  var hv = document.querySelector('.hero-video');
  if (hv) {
    var conn = navigator.connection || {};
    var slow = conn.saveData || /(^|-)2g$|3g/.test(conn.effectiveType || '');
    var calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!slow && !calm) {
      var src = hv.canPlayType('video/webm; codecs="vp9"') ? hv.dataset.webm : hv.dataset.mp4;
      hv.addEventListener('playing', function () { hv.classList.add('on'); }, { once: true });
      hv.src = src;
      var pr = hv.play(); if (pr && pr.catch) pr.catch(function () {});
    }
  }

  // Reveal on scroll
  const observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -60px 0px' });

  document.querySelectorAll('.reveal').forEach(function(el) {
    observer.observe(el);
  });
})();
