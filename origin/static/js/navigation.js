/* ============================================================
   NAVIGATION GUIDE ("3D living manual") — interactions
   Kept intentionally simple/flat (no build step, no framework) so
   it's easy to read and refactor:
     1. theme toggle          - same cookie pattern as every other page
     2. advanced 3D view      - cookie + page refresh, see docstring below
     3. search                - filters the flat detail list + dims non-matching 3D cards
     4. card click/keyboard   - scrolls to + highlights the matching detail section
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

    /* ---- 2. "advanced 3D view" toggle ----
       Deliberately NOT injected via JS-only (no swapping stylesheets live) - clicking
       just flips a cookie and reloads the page. The view (NavigationGuide, in
       origin/views/normal_view.py) reads that cookie server-side and decides whether
       to <link> navigation_advanced.css at all, so someone who never clicks this
       button never downloads the heavier file - that was the whole point of making
       it opt-in. */
    (function advancedToggle() {
        var btn = document.getElementById('advanced3dBtn');
        var label = document.getElementById('advanced3dBtnLabel');
        if (!btn) return;
        var isOn = document.body.classList.contains('advanced-3d');
        btn.addEventListener('click', function () {
            if (isOn) {
                setCookie('sd-nav-advanced', '0', 365);
            } else {
                setCookie('sd-nav-advanced', '1', 365);
            }
            window.location.reload();
        });
    })();

    /* ---- ambient particle backdrop (advanced view only, pure CSS animation,
       this JS only creates the handful of <span> elements - see
       navigation_advanced.css for the actual animation) ---- */
    if (document.body.classList.contains('advanced-3d')) {
        var wrap = document.createElement('div');
        wrap.className = 'sd-nav-particles';
        wrap.setAttribute('aria-hidden', 'true');
        for (var i = 0; i < 6; i++) {
            var p = document.createElement('span');
            var size = 120 + Math.random() * 180;
            p.style.width = size + 'px';
            p.style.height = size + 'px';
            p.style.left = Math.random() * 100 + '%';
            p.style.top = Math.random() * 100 + '%';
            p.style.animationDuration = (14 + Math.random() * 10) + 's';
            wrap.appendChild(p);
        }
        document.body.appendChild(wrap);

        // stagger each card's ambient rotation so they don't all move in lockstep
        document.querySelectorAll('.nav-3d-card-inner').forEach(function (el, i) {
            el.style.setProperty('--nav-card-i', i);
        });
    }

    /* ---- 3. search: filters the flat route list + dims non-matching 3D cards ---- */
    (function search() {
        var input = document.getElementById('navSearch');
        if (!input) return;
        var routeItems = Array.prototype.slice.call(document.querySelectorAll('.nav-route-item[data-search]'));
        var cards = Array.prototype.slice.call(document.querySelectorAll('.nav-3d-card'));

        input.addEventListener('input', function () {
            var q = input.value.toLowerCase().trim();
            var sectionsWithMatch = {};

            routeItems.forEach(function (item) {
                var haystack = item.getAttribute('data-search').toLowerCase();
                var match = q === '' || haystack.indexOf(q) !== -1;
                item.classList.toggle('is-search-hidden', !match);
                item.classList.toggle('is-search-match', match && q !== '');
                if (match) {
                    var sectionEl = item.closest('.nav-detail-section');
                    if (sectionEl) sectionsWithMatch[sectionEl.dataset.section] = true;
                }
            });

            cards.forEach(function (card) {
                var key = card.dataset.section;
                var dim = q !== '' && !sectionsWithMatch[key];
                card.style.opacity = dim ? '0.35' : '1';
            });
        });
    })();

    /* ---- 4. clicking/activating a 3D card scrolls to + highlights its detail section ---- */
    (function cardLink() {
        document.querySelectorAll('.nav-3d-card').forEach(function (card) {
            function go() {
                var target = document.getElementById('section-' + card.dataset.section);
                if (!target) return;
                document.querySelectorAll('.is-highlighted').forEach(function (el) { el.classList.remove('is-highlighted'); });
                card.classList.add('is-highlighted');
                target.classList.add('is-highlighted');
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                setTimeout(function () { target.classList.remove('is-highlighted'); card.classList.remove('is-highlighted'); }, 2200);
            }
            card.addEventListener('click', go);
            card.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); }
            });
        });
    })();
})();
