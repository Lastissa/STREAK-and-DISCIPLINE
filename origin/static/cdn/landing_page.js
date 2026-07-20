/**
 * ADVANCED JS â€” STREAK & DISCIPLINE
 * Loaded after page is interactive.
 * Features: theme toggle with cookie, mobile menu, scatter animations,
 *           scroll progress, intersection observer reveals, smooth scroll.
 */
(function() {
    'use strict';

    // ===== DOM ELEMENTS =====
    const body = document.body;
    const header = document.getElementById('siteHeader');
    const themeToggle = document.getElementById('themeToggle');
    const mobileToggle = document.getElementById('mobileToggle');
    const navLinks = document.getElementById('navLinks');
    const mobileOverlay = document.getElementById('mobileOverlay');
    const scatterElements = document.querySelectorAll('[data-scatter]');
    const lazySections = document.querySelectorAll('.lazy-section');
    const lazyImages = document.querySelectorAll('img.lazy-img');

    // ===== THEME TOGGLE WITH COOKIE =====
    const THEME_COOKIE = 'sd-theme';
    
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }
    
    function setCookie(name, value, days = 365) {
        const d = new Date();
        d.setTime(d.getTime() + (days * 86400000));
        document.cookie = `${name}=${value};expires=${d.toUTCString()};path=/;SameSite=Lax`;
    }

    // Apply saved theme immediately
    const savedTheme = getCookie(THEME_COOKIE);
    if (savedTheme === 'light') {
        body.classList.add('light-mode');
        themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
    } else {
        themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
    }
    
    // Show toggle button now that JS is ready
    themeToggle.style.display = 'flex';
    
    themeToggle.addEventListener('click', () => {
        if (body.classList.contains('light-mode')) {
            body.classList.remove('light-mode');
            setCookie(THEME_COOKIE, 'dark');
            themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
        } else {
            body.classList.add('light-mode');
            setCookie(THEME_COOKIE, 'light');
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
        }
    });

    // ===== MOBILE MENU =====
    function openMenu() {
        navLinks.classList.add('active');
        mobileOverlay.classList.add('active');
        mobileToggle.classList.add('active');
        body.style.overflow = 'hidden';
    }
    
    function closeMenu() {
        navLinks.classList.remove('active');
        mobileOverlay.classList.remove('active');
        mobileToggle.classList.remove('active');
        body.style.overflow = '';
    }
    
    mobileToggle.addEventListener('click', () => {
        if (navLinks.classList.contains('active')) {
            closeMenu();
        } else {
            openMenu();
        }
    });
    
    mobileOverlay.addEventListener('click', closeMenu);
    
    // Close menu when a link is clicked
    navLinks.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth <= 767) closeMenu();
        });
    });

    // ===== SCATTER & RESET ANIMATION =====
    function triggerScatter() {
        scatterElements.forEach(el => {
            // Random scatter values
            const sx = (Math.random() - 0.5) * 60;
            const sy = (Math.random() - 0.5) * 60;
            const sr = (Math.random() - 0.5) * 30;
            el.style.setProperty('--sx', sx + 'px');
            el.style.setProperty('--sy', sy + 'px');
            el.style.setProperty('--sr', sr + 'deg');
            el.classList.add('scattering');
        });
        
        // Reset after a short delay
        setTimeout(() => {
            scatterElements.forEach(el => {
                el.classList.remove('scattering');
                el.classList.add('resetting');
            });
            setTimeout(() => {
                scatterElements.forEach(el => {
                    el.classList.remove('resetting');
                });
            }, 600);
        }, 400);
    }

    // Trigger scatter when user scrolls to features section for the first time
    let scattered = false;
    const featuresSection = document.getElementById('features');
    
    const scatterObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !scattered) {
                scattered = true;
                setTimeout(triggerScatter, 500);
                scatterObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.3 });
    
    if (featuresSection) scatterObserver.observe(featuresSection);

    // ===== INTERSECTION OBSERVER FOR LAZY SECTIONS =====
    const sectionObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
                sectionObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    
    lazySections.forEach(section => sectionObserver.observe(section));

    // ===== LAZY LOAD IMAGES =====
    const imageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    img.addEventListener('load', () => img.classList.add('loaded'));
                }
                imageObserver.unobserve(img);
            }
        });
    }, { rootMargin: '150px' });
    
    lazyImages.forEach(img => imageObserver.observe(img));

    // ===== SCROLL PROGRESS BAR =====
    const progressBar = document.createElement('div');
    progressBar.classList.add('scroll-progress');
    document.body.prepend(progressBar);
    
    window.addEventListener('scroll', () => {
        const scrollTop = window.scrollY;
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        const scrolled = (scrollTop / docHeight) * 100;
        progressBar.style.width = scrolled + '%';
    });

    // ===== HEADER SCROLL EFFECT =====
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            header.style.boxShadow = '0 8px 40px rgba(0,0,0,0.4)';
        } else {
            header.style.boxShadow = '0 8px 32px rgba(0,0,0,0.3)';
        }
    });

    // ===== SMOOTH SCROLL FOR ANCHOR LINKS =====
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            const target = document.querySelector(targetId);
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // ===== ESC KEY CLOSES MOBILE MENU =====
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && navLinks.classList.contains('active')) {
            closeMenu();
        }
    });

    console.log(' STREAK & DISCIPLINE â€” Advanced JS loaded');
})();

// ===== EXPERIENCE MODE TOGGLE =====
(function() {
    const toggle = document.getElementById('experienceToggle');
    const body = document.body;
    const rainContainer = document.getElementById('rainContainer');
    const emberContainer = document.getElementById('emberContainer');
    const STORAGE_KEY = 'sd-experience-mode';
    
    if (!toggle) return;
    
    // Check saved preference
    const savedMode = localStorage.getItem(STORAGE_KEY);
    if (savedMode === 'active') {
        body.classList.add('experience-active');
        toggle.classList.add('active');
        startRain();
        startEmbers();
    }
    
    toggle.addEventListener('click', () => {
        if (body.classList.contains('experience-active')) {
            // TURN OFF
            body.classList.remove('experience-active');
            toggle.classList.remove('active');
            localStorage.setItem(STORAGE_KEY, 'inactive');
            stopRain();
            stopEmbers();
        } else {
            // TURN ON
            body.classList.add('experience-active');
            toggle.classList.add('active');
            localStorage.setItem(STORAGE_KEY, 'active');
            startRain();
            startEmbers();
        }
    });
    
    // ===== RAIN GENERATOR =====
    let rainInterval;
    const raindrops = [];
    const MAX_RAINDROPS = 60;
    
    function createRaindrop() {
        const drop = document.createElement('div');
        drop.className = 'raindrop';
        
        const left = Math.random() * 100;
        const duration = 0.5 + Math.random() * 0.8;
        const delay = Math.random() * 2;
        const size = 1 + Math.random() * 2;
        const opacity = 0.1 + Math.random() * 0.3;
        
        drop.style.cssText = `
            position: absolute;
            left: ${left}%;
            top: -40px;
            width: ${size}px;
            height: ${15 + Math.random() * 25}px;
            background: linear-gradient(to bottom, transparent, rgba(147, 197, 253, ${opacity}));
            border-radius: 0 0 3px 3px;
            animation: rainFall ${duration}s linear ${delay}s infinite;
            pointer-events: none;
        `;
        
        return drop;
    }
    
    function startRain() {
        if (!rainContainer) return;
        rainContainer.innerHTML = '';
        
        // Add CSS keyframe if not exists
        if (!document.getElementById('rain-keyframes')) {
            const style = document.createElement('style');
            style.id = 'rain-keyframes';
            style.textContent = `
                @keyframes rainFall {
                    0%   { transform: translateY(-40px) translateX(0); opacity: 0; }
                    10%  { opacity: 1; }
                    90%  { opacity: 1; }
                    100% { transform: translateY(100vh) translateX(${20 + Math.random() * 30}px); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
        
        for (let i = 0; i < MAX_RAINDROPS; i++) {
            const drop = createRaindrop();
            rainContainer.appendChild(drop);
            raindrops.push(drop);
        }
    }
    
    function stopRain() {
        if (!rainContainer) return;
        rainContainer.innerHTML = '';
        raindrops.length = 0;
    }
    
    // ===== EMBER / SPARK GENERATOR =====
    let emberInterval;
    const embers = [];
    const MAX_EMBERS = 25;
    
    function createEmber() {
        const ember = document.createElement('div');
        ember.className = 'ember';
        
        const left = Math.random() * 100;
        const size = 2 + Math.random() * 4;
        const duration = 3 + Math.random() * 5;
        const delay = Math.random() * 4;
        const color = Math.random() > 0.5 ? '147, 197, 253' : '96, 165, 250'; // Blue tones
        
        ember.style.cssText = `
            position: absolute;
            left: ${left}%;
            bottom: -10px;
            width: ${size}px;
            height: ${size}px;
            background: rgba(${color}, 0.6);
            border-radius: 50%;
            box-shadow: 0 0 ${size * 2}px rgba(${color}, 0.4);
            animation: emberRise ${duration}s linear ${delay}s infinite;
            pointer-events: none;
        `;
        
        return ember;
    }
    
    function startEmbers() {
        if (!emberContainer) return;
        emberContainer.innerHTML = '';
        
        if (!document.getElementById('ember-keyframes')) {
            const style = document.createElement('style');
            style.id = 'ember-keyframes';
            style.textContent = `
                @keyframes emberRise {
                    0%   { transform: translateY(0) translateX(0) scale(1); opacity: 0.8; }
                    50%  { transform: translateY(-50vh) translateX(${10 + Math.random() * 40}px) scale(0.6); opacity: 0.4; }
                    100% { transform: translateY(-100vh) translateX(${-10 - Math.random() * 30}px) scale(0); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
        
        for (let i = 0; i < MAX_EMBERS; i++) {
            const ember = createEmber();
            emberContainer.appendChild(ember);
            embers.push(ember);
        }
    }
    
    function stopEmbers() {
        if (!emberContainer) return;
        emberContainer.innerHTML = '';
        embers.length = 0;
    }
    
})();
