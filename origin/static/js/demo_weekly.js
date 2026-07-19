// Trigger hand‑drawn check and scatter when visible
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
            // Scatter effect on insight cards
            if (entry.target.hasAttribute('data-scatter') && !entry.target.dataset.scattered) {
                entry.target.dataset.scattered = true;
                const sx = (Math.random() - 0.5) * 30;
                const sy = (Math.random() - 0.5) * 30;
                const sr = (Math.random() - 0.5) * 15;
                entry.target.style.setProperty('--sx', sx + 'px');
                entry.target.style.setProperty('--sy', sy + 'px');
                entry.target.style.setProperty('--sr', sr + 'deg');
                entry.target.classList.add('scattering');
                setTimeout(() => {
                    entry.target.classList.remove('scattering');
                    entry.target.classList.add('resetting');
                    setTimeout(() => entry.target.classList.remove('resetting'), 600);
                }, 400);
            }
        }
    });
}, { threshold: 0.2 });

document.querySelectorAll('.summary-card, .chart-card, .insight-card').forEach(el => observer.observe(el));