(function () {
  'use strict';
  var f = document.getElementById('contactForm');
  if (!f) return;
  var status = document.getElementById('cfStatus');
  f.addEventListener('submit', function (e) {
    e.preventDefault();
    status.style.color = '';
    var name = f.name.value.trim(), email = f.email.value.trim(), phone = f.phone.value.trim();
    if (!name || !/^\S+@\S+\.\S+$/.test(email) || !phone) { status.textContent = 'Please fill in your name, a valid email, and phone.'; status.style.color = '#B85A5A'; return; }
    var btn = f.querySelector('button[type=submit]'); btn.disabled = true;
    var msg = '[' + f.pathway.value + '] ' + f.message.value.trim();
    fetch('/api/public/contact', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name, email: email, phone: phone, message: msg, website: f.website.value }) })
      .then(function (r) { if (!r.ok) throw new Error(); f.reset(); status.textContent = 'Thank you — we’ll be in touch soon.'; status.style.color = '#4a6b3a'; })
      .catch(function () { status.textContent = 'Something went wrong. Please call (216) 625-0028 or email Scherb@anavah-institute.org.'; status.style.color = '#B85A5A'; })
      .then(function () { btn.disabled = false; });
  });
})();
