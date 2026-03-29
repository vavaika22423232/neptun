self.addEventListener('install', function(e) {
  self.skipWaiting();
});

self.addEventListener('activate', function(e) {
  e.waitUntil(
    self.registration.unregister().then(function() {
      return self.clients.matchAll();
    }).then(function(clients) {
      clients.forEach(client => client.navigate(client.url));
    })
  );
});

self.addEventListener('fetch', function(e) {
  // Do nothing. Allow network.
});
