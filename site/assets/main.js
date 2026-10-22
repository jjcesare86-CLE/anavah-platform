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
