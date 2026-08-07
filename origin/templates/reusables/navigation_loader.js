(function () {
    const loader = document.getElementById("navLoader");
    if (!loader) return;

    const messages = loader.querySelectorAll(".loader-text");
    const cancelBtn = document.getElementById("navLoaderCancelBtn");
    const progressFill = document.getElementById("navLoaderProgressFill");
    const cancelConfirm = document.getElementById("navLoaderCancelConfirm");

    // How long the user has to hit "Cancel" before we actually navigate away.
    // Kept short so it never feels like it's slowing down a real navigation,
    // but long enough for a misclick to be caught and reversed.
    const GRACE_MS = 1100;

    let msgIndex = 0;
    let msgTimer = null;
    let graceTimer = null;
    let visible = false;
    let pendingAction = null; // set only for navigations WE intercepted (link/form)

    if (progressFill) {
        loader.style.setProperty("--nav-grace-ms", GRACE_MS + "ms");
    }

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

    // cancelable = true when this show() came from a link click / form submit
    // that we intercepted (and can therefore actually cancel). It's false for
    // genuine browser-level unloads (typed URL, refresh, closing the tab),
    // where no custom UI can stop the navigation, so we don't offer a button
    // that would silently do nothing.
    function showLoader(cancelable) {
        loader.classList.remove("loader-hidden");
        loader.classList.remove("loader-just-canceled");
        loader.setAttribute("aria-hidden", "false");
        loader.classList.toggle("loader-cancelable", !!cancelable);

        if (!visible) {
            visible = true;
            msgTimer = setInterval(rotateMessages, 1800);
        }
    }

    function hideLoader() {
        visible = false;
        loader.classList.add("loader-hidden");
        loader.classList.remove("loader-cancelable");
        loader.setAttribute("aria-hidden", "true");

        if (msgTimer) {
            clearInterval(msgTimer);
            msgTimer = null;
        }
        clearGraceTimer();

        messages.forEach((el, i) => {
            el.classList.remove("active", "exit");
            if (i === 0) el.classList.add("active");
        });

        msgIndex = 0;
        pendingAction = null;
    }

    function clearGraceTimer() {
        if (graceTimer) {
            clearTimeout(graceTimer);
            graceTimer = null;
        }
    }

    // Begin an interceptable navigation: show the loader + cancel button,
    // and only actually run the navigation after GRACE_MS unless the user
    // cancels first.
    function beginInterceptable(run) {
        pendingAction = run;
        showLoader(true);
        clearGraceTimer();
        graceTimer = setTimeout(function () {
            graceTimer = null;
            const action = pendingAction;
            pendingAction = null;
            if (action) action();
        }, GRACE_MS);
    }

    function cancelPendingNavigation() {
        if (!pendingAction && graceTimer === null) return; // nothing to cancel
        clearGraceTimer();
        pendingAction = null;

        loader.classList.add("loader-just-canceled");
        if (cancelConfirm) cancelConfirm.textContent = "Cancelled — you're still here.";

        // Give the confirmation a beat to be visible, then fully hide.
        setTimeout(hideLoader, 550);
    }

    if (cancelBtn) {
        cancelBtn.addEventListener("click", cancelPendingNavigation);
    }

    // Escape also cancels, for keyboard users who fat-fingered a link.
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && loader.classList.contains("loader-cancelable")) {
            cancelPendingNavigation();
        }
    });

    // Hide on normal page load
    window.addEventListener("load", hideLoader);

    // Hide when returning with the Back/Forward button
    window.addEventListener("pageshow", hideLoader);

    // Intercept internal link clicks so the navigation can be cancelled.
    // IMPORTANT: if another script on the page already handled this click
    // (e.g. an AJAX-driven link that called preventDefault()), we leave it
    // completely alone — no interception, no forced navigation later. We
    // only take over plain links that were going to navigate natively.
    document.addEventListener("click", function (e) {
        const a = e.target.closest("a");
        if (!a) return;
        if (a.hasAttribute("data-nav-skip")) return;

        if (a.target === "_blank") return;
        if (a.hasAttribute("download")) return;

        const href = a.getAttribute("href");
        if (!href || href.startsWith("#") || href.startsWith("javascript:") || href.startsWith("mailto:") || href.startsWith("tel:")) return;

        const url = new URL(a.href, window.location.origin);
        if (url.origin !== window.location.origin) return;

        if (e.defaultPrevented) {
            // Some other handler already owns this click (custom AJAX nav).
            // Just show the cosmetic, non-cancelable loader as before.
            showLoader(false);
            return;
        }

        e.preventDefault();
        beginInterceptable(function () {
            window.location.href = a.href;
        });
    });

    // Intercept form submissions the same way. Forms that already handle
    // their own submit (fetch/AJAX, calling preventDefault themselves) are
    // left untouched — we never re-trigger a native submit on top of them.
    document.addEventListener("submit", function (e) {
        const form = e.target;
        if (!form || form.hasAttribute("data-nav-skip")) return;

        if (e.defaultPrevented) {
            showLoader(false);
            return;
        }

        e.preventDefault();
        beginInterceptable(function () {
            form.submit();
        });
    });

    // Genuine browser-level unload (typed URL, refresh, closing tab, external
    // link via address bar). This CANNOT be cancelled by custom UI, so we show
    // the loader without the cancel option — purely a "please wait" cue for
    // the brief moment before the browser actually leaves.
    window.addEventListener("beforeunload", function () {
        showLoader(false);
    });
})();
