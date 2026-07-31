(function () {
    const loader = document.getElementById("navLoader");
    if (!loader) return;

    const messages = loader.querySelectorAll(".loader-text");
    let msgIndex = 0;
    let msgTimer = null;
    let visible = false;

    function rotateMessages() {
        if (!visible || messages.length <= 1) return;

        messages[msgIndex].classList.remove("active");
        messages[msgIndex].classList.add("exit");

        msgIndex = (msgIndex + 1) % messages.length;

        messages[msgIndex].classList.remove("exit");
        messages[msgIndex].classList.add("active");

        setTimeout(() => {
            messages.forEach((el, i) => {
                if (i !== msgIndex) el.classList.remove("exit");
            });
        }, 400);
    }

    function showLoader() {
        if (visible) return;
        visible = true;
        loader.classList.remove("loader-hidden");
        loader.setAttribute("aria-hidden", "false");

        msgTimer = setInterval(rotateMessages, 1800);
    }

    function hideLoader() {
        visible = false;
        loader.classList.add("loader-hidden");
        loader.setAttribute("aria-hidden", "true");

        if (msgTimer) {
            clearInterval(msgTimer);
            msgTimer = null;
        }

        messages.forEach((el, i) => {
            el.classList.remove("active", "exit");
            if (i === 0) el.classList.add("active");
        });
        msgIndex = 0;
    }

    // Hide on page load
    window.addEventListener("load", hideLoader);

    // Show for internal navigation links
    document.addEventListener("click", function (e) {
        const a = e.target.closest("a");
        if (!a) return;

        if (a.target === "_blank") return;
        if (a.hasAttribute("download")) return;

        const href = a.getAttribute("href");
        if (!href || href.startsWith("#") || href.startsWith("javascript:")) return;

        const url = new URL(a.href, window.location.origin);
        if (url.origin !== window.location.origin) return;

        showLoader();
    });

    // Show for form submissions
    document.addEventListener("submit", function () {
        showLoader();
    });

    // Browser refresh / navigation away
    window.addEventListener("beforeunload", showLoader);

    // Hide if page is restored from bfcache
    window.addEventListener("pageshow", hide);
})();