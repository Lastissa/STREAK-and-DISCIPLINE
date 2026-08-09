/* ============================================================
   PUSH NOTIFICATIONS — enable/disable browser push reminders
   Include this on any page with a button/toggle that has
   id="pushEnableBtn" (or call SDPush.enable() / SDPush.disable()
   yourself). Talks to:
     GET  {% url 'origin_push_vapid_public_key' %}
     POST {% url 'origin_push_subscribe' %}
     POST {% url 'origin_push_unsubscribe' %}
   ============================================================ */
window.SDPush = (function () {
  'use strict';

  function getCookie(n) {
    var m = document.cookie.match('(?:^|;)\\s?' + n + '=([^;]*)');
    return m ? decodeURIComponent(m[1]) : '';
  }

  function urlBase64ToUint8Array(base64String) {
    var padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    var base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    var rawData = window.atob(base64);
    var outputArray = new Uint8Array(rawData.length);
    for (var i = 0; i < rawData.length; ++i) outputArray[i] = rawData.charCodeAt(i);
    return outputArray;
  }

  function supported() {
    return 'serviceWorker' in navigator && 'PushManager' in window;
  }

  function registerServiceWorker() {
    return navigator.serviceWorker.register('/sw.js');
  }

  /* ============================================================
   PUSH NOTIFICATIONS — enable/disable browser push reminders
   Include this on any page with a button/toggle that has
   id="pushEnableBtn" (or call SDPush.enable() / SDPush.disable()
   yourself). Talks to:
     GET  {% url 'origin_push_vapid_public_key' %}
     POST {% url 'origin_push_subscribe' %}
     POST {% url 'origin_push_unsubscribe' %}
   ============================================================ */
window.SDPush = (function () {
  'use strict';

  function getCookie(n) {
    var m = document.cookie.match('(?:^|;)\\s?' + n + '=([^;]*)');
    return m ? decodeURIComponent(m[1]) : '';
  }

  function urlBase64ToUint8Array(base64String) {
    var padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    var base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    var rawData = window.atob(base64);
    var outputArray = new Uint8Array(rawData.length);
    for (var i = 0; i < rawData.length; ++i) outputArray[i] = rawData.charCodeAt(i);
    return outputArray;
  }

  function supported() {
    return 'serviceWorker' in navigator && 'PushManager' in window;
  }

  function registerServiceWorker() {
    return navigator.serviceWorker.register('/sw.js');
  }

  function enable() {
    if (!supported()) {
      return Promise.reject(new Error('Push notifications are not supported in this browser.'));
    }

    return registerServiceWorker()
      .then(function (registration) { return registration; })
      .then(function (registration) {
        return fetch('{% url "origin_push_vapid_public_key" %}', { credentials: 'include' })
          .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
          .then(function (res) {
            if (!res.ok) throw new Error(res.d.message || 'Push is not configured on this server.');
            return registration.pushManager.subscribe({
              userVisibleOnly: true,
              applicationServerKey: urlBase64ToUint8Array(res.d.vapid_public_key)
            });
          });
      })
      .then(function (subscription) {
        return fetch('{% url "origin_push_subscribe" %}', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
          body: JSON.stringify(subscription.toJSON())
        }).then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); });
      })
      .then(function (res) {
        if (!res.ok) throw new Error(res.d.message || 'Could not save your push subscription.');
        return res.d;
      });
  }

  function disable() {
    if (!supported()) return Promise.resolve();

    return navigator.serviceWorker.getRegistration().then(function (registration) {
      if (!registration) return;
      return registration.pushManager.getSubscription().then(function (subscription) {
        if (!subscription) return;
        var endpoint = subscription.endpoint;
        return subscription.unsubscribe().then(function () {
          return fetch('{% url "origin_push_unsubscribe" %}', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ endpoint: endpoint })
          });
        });
      });
    });
  }

  function isEnabled() {
    if (!supported()) return Promise.resolve(false);
    return navigator.serviceWorker.getRegistration().then(function (registration) {
      if (!registration) return false;
      return registration.pushManager.getSubscription().then(function (sub) { return !!sub; });
    });
  }

  // Optional auto-wire: if a button with id="pushEnableBtn" exists on the page,
  // clicking it toggles push on/off and reflects state via data-enabled + text.
  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.getElementById('pushEnableBtn');
    if (!btn) return;

    function reflect(on) {
      btn.dataset.enabled = on ? 'true' : 'false';
      btn.textContent = on ? 'Push notifications on' : 'Enable push notifications';
    }

    isEnabled().then(reflect);

    btn.addEventListener('click', function () {
      var currentlyOn = btn.dataset.enabled === 'true';
      btn.disabled = true;
      var action = currentlyOn ? disable() : enable();
      action
        .then(function () { reflect(!currentlyOn); })
        .catch(function (err) { alert(err.message || 'Something went wrong with push notifications.'); })
        .finally(function () { btn.disabled = false; });
    });
  });

  return { enable: enable, disable: disable, isEnabled: isEnabled, supported: supported };
})();


  function disable() {
    if (!supported()) return Promise.resolve();

    return navigator.serviceWorker.getRegistration().then(function (registration) {
      if (!registration) return;
      return registration.pushManager.getSubscription().then(function (subscription) {
        if (!subscription) return;
        var endpoint = subscription.endpoint;
        return subscription.unsubscribe().then(function () {
          return fetch('{% url "origin_push_unsubscribe" %}', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ endpoint: endpoint })
          });
        });
      });
    });
  }

  function isEnabled() {
    if (!supported()) return Promise.resolve(false);
    return navigator.serviceWorker.getRegistration().then(function (registration) {
      if (!registration) return false;
      return registration.pushManager.getSubscription().then(function (sub) { return !!sub; });
    });
  }

  // Optional auto-wire: if a button with id="pushEnableBtn" exists on the page,
  // clicking it toggles push on/off and reflects state via data-enabled + text.
  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.getElementById('pushEnableBtn');
    if (!btn) return;

    function reflect(on) {
      btn.dataset.enabled = on ? 'true' : 'false';
      btn.textContent = on ? 'Push notifications on' : 'Enable push notifications';
    }

    isEnabled().then(reflect);

    btn.addEventListener('click', function () {
      var currentlyOn = btn.dataset.enabled === 'true';
      btn.disabled = true;
      var action = currentlyOn ? disable() : enable();
      action
        .then(function () { reflect(!currentlyOn); })
        .catch(function (err) { alert(err.message || 'Something went wrong with push notifications.'); })
        .finally(function () { btn.disabled = false; });
    });
  });

  return { enable: enable, disable: disable, isEnabled: isEnabled, supported: supported };
})();
