// Service worker minimal : rend l'app installable et charge vite la coquille.
// Le traitement audio nécessite le serveur : on ne met en cache que l'interface.
const CACHE = "choir-parts-v1";
const SHELL = ["/", "/static/manifest.webmanifest",
               "/static/icon-192.png", "/static/icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  // POST (analyse) et audio : toujours réseau.
  if (req.method !== "GET" || req.url.includes("/audio/") || req.url.includes("/analyser")) {
    return;
  }
  // GET de la coquille : réseau d'abord, cache en secours (hors-ligne).
  e.respondWith(
    fetch(req).then((r) => {
      const copy = r.clone();
      caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
      return r;
    }).catch(() => caches.match(req).then((m) => m || caches.match("/")))
  );
});
