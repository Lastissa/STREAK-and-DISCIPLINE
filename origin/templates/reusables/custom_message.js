(function() {
    var container = document.getElementById('messagesContainer');
    if (!container) return;

    // Copy all
    var copyBtn = document.getElementById('msgCopyAll');
    if (copyBtn) {
        copyBtn.addEventListener('click', function() {
            var texts = [];
            container.querySelectorAll('.msg-text').forEach(function(el) {
                texts.push(el.textContent.trim());
            });
            var allText = texts.join('\n');
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(allText).then(showCopied);
            } else {
                var ta = document.createElement('textarea');
                ta.value = allText;
                ta.style.position = 'fixed';
                ta.style.opacity = '0';
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                showCopied();
            }
        });
    }

    function showCopied() {
        if (!copyBtn) return;
        var span = copyBtn.querySelector('span');
        var icon = copyBtn.querySelector('i');
        var origText = span.textContent;
        var origIcon = icon.className;
        copyBtn.classList.add('copied');
        span.textContent = 'Copied!';
        icon.className = 'fas fa-check';
        setTimeout(function() {
            copyBtn.classList.remove('copied');
            span.textContent = origText;
            icon.className = origIcon;
        }, 1800);
    }

    // Close buttons only — no auto-dismiss
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
        msg.addEventListener('transitionend', function() {
            msg.remove();
            if (!container.querySelector('.msg')) container.remove();
        }, { once: true });
    }
})();