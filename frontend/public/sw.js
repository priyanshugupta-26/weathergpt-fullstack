// WeatherGPT Progressive Web App Service Worker
// Features: Stale-While-Revalidate shell caching, Emergency Web Push Handling, Geo-alert routing

const SHELL_CACHE = 'weathergpt-shell-v2';
const WEATHER_CACHE = 'weathergpt-data-v2';

const STATIC_ASSETS = [
  '/',
  '/offline.html',
  '/icon.svg',
  '/favicon.svg',
  '/manifest.webmanifest',
];

// Install: Pre-cache application shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(STATIC_ASSETS)).catch((err) => {
      console.warn('PWA Pre-cache failed for some assets', err);
    })
  );
  self.skipWaiting();
});

// Activate: Clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== SHELL_CACHE && k !== WEATHER_CACHE)
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// Fetch: Stale-While-Revalidate for static & ordinary weather, strictly network-first for live alerts
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Skip non-GET and third-party
  if (event.request.method !== 'GET' || url.origin !== location.origin) return;

  // Never cache authentication or real-time mutation
  if (url.pathname.startsWith('/api/auth') || url.pathname.startsWith('/api/chat')) {
    return;
  }

  // Critical alerts & notifications: Network only, do NOT serve stale emergency warnings
  if (url.pathname.startsWith('/api/alerts') || url.pathname.startsWith('/api/notifications')) {
    event.respondWith(
      fetch(event.request).catch(() => {
        return new Response(JSON.stringify({ alerts: [], status: 'offline', offline: true }), {
          headers: { 'Content-Type': 'application/json' },
        });
      })
    );
    return;
  }

  // Ordinary forecast: Stale-While-Revalidate
  if (url.pathname.startsWith('/api/weather/forecast')) {
    event.respondWith(
      caches.open(WEATHER_CACHE).then((cache) =>
        cache.match(event.request).then((cachedResponse) => {
          const fetchPromise = fetch(event.request)
            .then((networkResponse) => {
              if (networkResponse.ok) {
                cache.put(event.request, networkResponse.clone());
              }
              return networkResponse;
            })
            .catch(() => cachedResponse);

          return cachedResponse || fetchPromise;
        })
      )
    );
    return;
  }

  // App shell navigation & static assets
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() =>
        caches.match('/offline.html').then((res) => res || fetch(event.request))
      )
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});

// ========================================================
// Web Push Notifications Handling (NDMA CAP & Emergency Push)
// ========================================================

self.addEventListener('push', (event) => {
  let data = {
    title: '⚠ WeatherGPT Emergency Alert',
    body: 'Severe weather or disaster update for your region.',
    action_url: '/alerts',
    id: 'alert-' + Date.now(),
  };

  if (event.data) {
    try {
      data = event.data.json();
    } catch {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body || 'Immediate action or safety advisory recommended.',
    icon: '/icon.svg',
    badge: '/icon.svg',
    vibrate: [300, 100, 300],
    data: {
      url: data.action_url || '/alerts',
      timestamp: Date.now(),
    },
    tag: data.id || 'weathergpt-emergency',
    renotify: true,
    requireInteraction: true,
  };

  event.waitUntil(self.registration.showNotification(data.title || 'WeatherGPT Warning', options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const urlToOpen = (event.notification.data && event.notification.data.url) || '/alerts';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.includes(location.origin) && 'focus' in client) {
          client.navigate(urlToOpen);
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});
