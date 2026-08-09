/* STREAK & DISCIPLINE — service worker
 * Only job: receive a 'push' event from the browser's push service and turn it into
 * an OS-level notification, then route a click on that notification to the dashboard
 * (or wherever the payload's `url` points).
 *
 * Served from the DOMAIN ROOT (see /sw.js in DISCIPLINEandSTREAK/urls.py, backed by
 * origin.views.ServiceWorkerFile), NOT from /static/js/sw.js directly — a service
 * worker's scope is limited to the directory it's served from, and we need it to
 * control the whole site, not just /static/.
 */

self.addEventListener('push', function (event) {
  var payload = { title: 'STREAK & DISCIPLINE', body: "You haven't checked in today.", url: '/v1/dashboard/' };
  try {
    if (event.data) payload = Object.assign(payload, event.data.json());
  } catch (e) {
    // Non-JSON push payload — fall back to the default text above rather than throwing.
  }

  var options = {
    body: payload.body,
    icon: payload.icon || '/static/img/desktop_light.png',
    badge: payload.icon || '/static/img/desktop_light.png',
    data: { url: payload.url },
    tag: 'checkin-reminder',   // collapses multiple reminders into one notification slot instead of stacking
    renotify: true
  };

  event.waitUntil(self.registration.showNotification(payload.title, options));
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  var url = (event.notification.data && event.notification.data.url) || '/v1/dashboard/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (windowClients) {
      for (var i = 0; i < windowClients.length; i++) {
        var client = windowClients[i];
        if (client.url.indexOf(url) !== -1 && 'focus' in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});
