const CACHE_NAME = "spendsmart-static-v1";
const STATIC_ASSETS = [
  "/",
  "/index.html",
  "/login.html",
  "/app.html",
  "/manifest.webmanifest",
  "/css/style.css",
  "/css/theme.css",
  "/css/landing.css",
  "/css/app.css",
  "/js/theme.js",
  "/js/icons.js",
  "/js/landing.js",
  "/js/theme-init.js",
  "/js/forms.js",
  "/js/app.js",
  "/js/auth.js",
  "/js/ui.js",
  "/js/api.js",
  "/js/charts.js",
  "/js/pages/dashboard.js",
  "/js/pages/settings.js",
  "/js/pages/transactions.js",
  "/js/pages/goals.js",
  "/js/pages/budgets.js",
  "/js/pages/recurring.js",
  "/assets/favicon.svg",
  "/assets/icon-192.png",
  "/assets/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;

  if (request.mode === "navigate") {
    event.respondWith(fetch(request).then((response) => {
      if (response.ok) caches.open(CACHE_NAME).then((cache) => cache.put(request, response.clone()));
      return response;
    }).catch(async () => (await caches.match(request)) || (await caches.match("/index.html"))));
    return;
  }

  if (STATIC_ASSETS.includes(url.pathname)) {
    event.respondWith(caches.match(request).then((cached) => cached || fetch(request).then((response) => {
      if (response.ok) caches.open(CACHE_NAME).then((cache) => cache.put(request, response.clone()));
      return response;
    })));
  }
});
