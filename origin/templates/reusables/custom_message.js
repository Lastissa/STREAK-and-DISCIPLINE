(function() {
    var container = document.getElementById('messagesContainer');
    if (!container) return;

    // Copy all button
    var copyAllBtn = document.getElementById('msgCopyAll');
    if (copyAllBtn) {
        copyAllBtn.addEventListener('click', function() {
            var texts = [];
            container.querySelectorAll('.msg-text').forEach(function(el) {
                texts.push(el.textContent.trim());
            });
            var allText = texts.join('\n');
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(allText).then(function() {
                    showCopied(copyAllBtn);
                });
            } else {
                var ta = document.createElement('textarea');
                ta.value = allText;
                ta.style.position = 'fixed';
                ta.style.opacity = '0';
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                showCopied(copyAllBtn);
            }
        });
    }

    function showCopied(btn) {
        if (!btn) return;
        var span = btn.querySelector('span');
        var icon = btn.querySelector('i');
        var origText = span.textContent;
        var origIcon = icon.className;
        btn.classList.add('copied');
        span.textContent = 'Copied!';
        icon.className = 'fas fa-check';
        setTimeout(function() {
            btn.classList.remove('copied');
            span.textContent = origText;
            icon.className = origIcon;
        }, 1800);
    }

    // Per-message copy buttons
    container.querySelectorAll('.msg-copy-single').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            var msgText = this.closest('.msg').querySelector('.msg-text').textContent.trim();
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(msgText).then(function() {
                    btn.classList.add('copied');
                    setTimeout(function() { btn.classList.remove('copied'); }, 1500);
                });
            }
        });
    });

    // Close buttons with physics animation
    var msgs = container.querySelectorAll('.msg');
    msgs.forEach(function(msg) {
        var closeBtn = msg.querySelector('.msg-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                dismiss(msg);
            });
        }
    });

    function dismiss(msg) {
        if (msg.classList.contains('removing')) return;
        msg.classList.add('removing');
        
        // Remove after animation completes
        var onTransitionEnd = function() {
            msg.remove();
            if (!container.querySelector('.msg')) {
                container.remove();
            }
        };
        
        msg.addEventListener('transitionend', onTransitionEnd, { once: true });
        
        // Safety timeout in case transitionend doesn't fire
        setTimeout(function() {
            if (msg.parentNode) {
                msg.remove();
                if (!container.querySelector('.msg')) {
                    container.remove();
                }
            }
        }, 500);
    }
})();