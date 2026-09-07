const CACHE='paleologos-remote-v190';
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('fetch',event=>{
  const u=new URL(event.request.url);
  if(u.pathname.startsWith('/api/') || u.pathname==='/login' || u.pathname==='/logout') return;
  event.respondWith(fetch(event.request).catch(()=>caches.match(event.request)));
});
