// PARKDA 서비스워커
// 같은 출처(origin)의 GET 응답만 캐시한다.
// Supabase·YouTube·카카오 등 외부 API 응답과 POST·인증 요청은 캐시하지 않는다.
const CACHE = 'parkda-v2';
const ASSETS = ['/', '/index.html', '/manifest.json', '/icon-192.png', '/icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  // 이전 버전(parkda-v1) 캐시는 외부 API 응답까지 담고 있었으므로 모두 삭제
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin) return; // 외부 요청: 브라우저 기본 동작
  if (url.pathname.startsWith('/api/')) return; // 서버 API 응답(외부 API 기반)은 캐시하지 않음
  e.respondWith(
    fetch(req)
      .then(res => {
        if (res.ok && res.type === 'basic') {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy));
        }
        return res;
      })
      .catch(() => caches.match(req))
  );
});
