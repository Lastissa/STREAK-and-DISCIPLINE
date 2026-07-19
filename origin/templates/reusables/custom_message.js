/**
 * Messages: copy all, auto-dismiss, close button.
 */
(function() {
    var container = document.getElementById('messagesContainer');
    if (!container) return;

    // ===== COPY ALL BUTTON =====
    var copyBtn = document.getElementById('msgCopyAll');
    if (copyBtn) {
        copyBtn.addEventListener('click', function() {
            var texts = [];
            container.querySelectorAll('.msg-text').forEach(function(el) {
                texts.push(el.textContent.trim());
            });
            var allText = texts.join('\n');

            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(allText).then(function() {
                    showCopied();
                });
            } else {
                // Fallback for older browsers
                var textarea = document.createElement('textarea');
                textarea.value = allText;
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                showCopied();
            }
        });
    }

    function showCopied() {
        if (!copyBtn) return;
        var span = copyBtn.querySelector('span');
        var icon = copyBtn.querySelector('i');
        var originalText = span.textContent;
        var originalIcon = icon.className;

        copyBtn.classList.add('copied');
        span.textContent = 'Copied!';
        icon.className = 'fas fa-check';

        setTimeout(function() {
            copyBtn.classList.remove('copied');
            span.textContent = originalText;
            icon.className = originalIcon;
        }, 2000);
    }

    // ===== AUTO-DISMISS + CLOSE BUTTONS =====
    var messages = container.querySelectorAll('.msg');
    messages.forEach(function(msg) {
        var timer = setTimeout(function() {
            dismiss(msg);
        }, 6000);

        var closeBtn = msg.querySelector('.msg-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                clearTimeout(timer);
                dismiss(msg);
            });
        }

        msg.addEventListener('mouseenter', function() {
            clearTimeout(timer);
        });
        msg.addEventListener('mouseleave', function() {
            timer = setTimeout(function() {
                dismiss(msg);
            }, 3000);
        });
    });

    function dismiss(msg) {
        msg.classList.add('removing');
        msg.addEventListener('transitionend', function() {
            msg.remove();
            if (container.querySelectorAll('.msg').length === 0) {
                container.remove();
            }
        }, { once: true });
    }
})();