/* ============================================================
   SITE GUIDE — interactions
   Kept intentionally simple/flat (no build step, no framework):
     1. theme toggle - same cookie pattern as every other page
     2. search        - filters the card grid by title/description
   ============================================================ */
(function () {
    'use strict';

    function getCookie(name) {
        var v = '; ' + document.cookie;
        var parts = v.split('; ' + name + '=');
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }
    function setCookie(name, value, days) {
        document.cookie = name + '=' + value + ';path=/;max-age=' + (days * 86400) + ';SameSite=Lax';
    }

    /* ---- 1. theme toggle (same pattern as privacy_etc.html etc.) ---- */
    (function themeToggle() {
        var saved = getCookie('sd-theme');
        var body = document.body;
        var btn = document.getElementById('themeToggle');
        if (!btn) return;
        if (saved === 'light') { body.classList.add('light-mode'); btn.innerHTML = '<i class="fas fa-sun"></i>'; }
        btn.addEventListener('click', function () {
            if (body.classList.contains('light-mode')) {
                body.classList.remove('light-mode');
                setCookie('sd-theme', 'dark', 365);
                btn.innerHTML = '<i class="fas fa-moon"></i>';
            } else {
                body.classList.add('light-mode');
                setCookie('sd-theme', 'light', 365);
                btn.innerHTML = '<i class="fas fa-sun"></i>';
            }
        });
    })();

    /* ---- 2. search: filters the card grid by title/description ---- */
    (function search() {
        var input = document.getElementById('navSearch');
        var noMatch = document.getElementById('navNoMatch');
        if (!input) return;
        var cards = Array.prototype.slice.call(document.querySelectorAll('.nav-card[data-search]'));

        input.addEventListener('input', function () {
            var q = input.value.toLowerCase().trim();
            var visibleCount = 0;

            cards.forEach(function (card) {
                var haystack = card.getAttribute('data-search').toLowerCase();
                var match = q === '' || haystack.indexOf(q) !== -1;
                card.classList.toggle('is-search-hidden', !match);
                if (match) visibleCount += 1;
            });

            if (noMatch) noMatch.hidden = visibleCount !== 0;
        });
    })();
})();
