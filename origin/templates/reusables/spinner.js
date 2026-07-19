// ===== LOADER WITH ROTATING TEXT & TIMEOUT =====
(function() {
    const loader = document.getElementById('loader');
    if (!loader) return;
    
    const textSpans = loader.querySelectorAll('.loader-text');
    if (!textSpans.length) {
        // No rotating text, just hide on load
        window.addEventListener('load', function() {
            setTimeout(function() {
                loader.classList.add('loader-hidden');
                loader.addEventListener('transitionend', function() {
                    loader.remove();
                }, { once: true });
            }, 400);
        });
        setTimeout(function() {
            if (!loader.classList.contains('loader-hidden')) {
                loader.classList.add('loader-hidden');
                loader.addEventListener('transitionend', function() {
                    loader.remove();
                }, { once: true });
            }
        }, 8000);
        return;
    }
    
    let currentIndex = 0;
    let rotationInterval;
    
    function rotateText() {
        textSpans[currentIndex].classList.remove('active');
        textSpans[currentIndex].classList.add('exit');
        currentIndex = (currentIndex + 1) % textSpans.length;
        textSpans[currentIndex].classList.remove('exit');
        textSpans[currentIndex].classList.add('active');
    }
    
    rotationInterval = setInterval(rotateText, 2500);
    
    function hideLoader() {
        clearInterval(rotationInterval);
        loader.classList.add('loader-hidden');
        loader.addEventListener('transitionend', function() {
            loader.remove();
        }, { once: true });
    }
    
    window.addEventListener('load', function() {
        setTimeout(hideLoader, 400);
    });
    
    setTimeout(function() {
        if (!loader.classList.contains('loader-hidden')) {
            hideLoader();
        }
    }, 8000);
})();