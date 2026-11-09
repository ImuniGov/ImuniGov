/* Only public application assets are cached. Never cache API, files, sessions or health records. */
const CACHE = 'imuniguia-public-v1'
const CORE = ['/offline.html', '/offline.css', '/manifest.webmanifest', '/icons/icon-192.png', '/icons/icon-512.png']
self.addEventListener('install', event => { event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(CORE))) })
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('imuniguia-public-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()))
})
self.addEventListener('message', event => { if (event.data?.type === 'ACTIVATE_UPDATE') self.skipWaiting() })
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url)
  if (url.origin !== self.location.origin || request.method !== 'GET' || url.pathname.startsWith('/api/')) return
  if (request.mode === 'navigate') { event.respondWith(fetch(request).catch(() => caches.match('/offline.html'))); return }
  if (url.pathname.startsWith('/assets/') || CORE.includes(url.pathname) || url.pathname.startsWith('/icons/')) {
    event.respondWith(caches.match(request).then(hit => hit || fetch(request).then(response => { if (response.ok && response.type === 'basic') { const copy = response.clone(); event.waitUntil(caches.open(CACHE).then(cache => cache.put(request, copy))) }; return response })))
  }
})
self.addEventListener('push', event => {
  // The lock screen never receives names, vaccine names, dates or medical content.
  event.waitUntil(self.registration.showNotification('ImuniGuia', { body: 'Há uma atualização no acompanhamento da sua família. Abra o aplicativo para conferir.', icon: '/icons/icon-192.png', badge: '/icons/icon-192.png', tag: 'imuniguia-care-update', data: { url: '/?view=notifications' } }))
})
self.addEventListener('notificationclick', event => {
  event.notification.close()
  event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(async windows => { const existing = windows.find(w => new URL(w.url).origin === self.location.origin); if (existing) { await existing.navigate('/?view=notifications'); return existing.focus() }; return self.clients.openWindow('/?view=notifications') }))
})
