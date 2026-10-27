// 사용법: node tests/unit/sw_cache_test.js sw.js
// 서비스워커 캐싱 규칙 검증: 같은 출처 GET만 캐시, 외부 API·POST는 캐시하지 않음.
const fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');
const listeners = {};
const store = new Map();
const cacheStore = new Map();
const fakeCaches = {
  open: async (name) => { if (!cacheStore.has(name)) cacheStore.set(name, new Map()); const c = cacheStore.get(name);
    return { addAll: async () => {}, put: async (req, res) => { c.set(req.url, res); } }; },
  keys: async () => [...cacheStore.keys()],
  delete: async (k) => cacheStore.delete(k),
  match: async (req) => { for (const c of cacheStore.values()) if (c.has(req.url)) return c.get(req.url); return undefined; },
};
let fetchCalls = [];
const ORIGIN = 'https://parkda.example';
const sandbox = {
  self: { location: { origin: ORIGIN }, clients: { claim: async () => {} }, skipWaiting: () => {},
    addEventListener: (t, f) => { listeners[t] = f; } },
  caches: fakeCaches, URL, Promise, console,
  fetch: async (req) => { fetchCalls.push(req.url); return { ok: true, type: req.url.startsWith(ORIGIN) ? 'basic' : 'cors', clone() { return this; }, body: req.url }; },
};
new Function(...Object.keys(sandbox), src)(...Object.values(sandbox));

let pass = 0, fail = 0;
const check = (name, cond) => { cond ? pass++ : fail++; console.log((cond ? 'PASS ' : 'FAIL ') + name); };
const runFetch = async (url, method = 'GET') => {
  let p; const e = { request: { url, method }, respondWith: (x) => { p = x; } };
  listeners.fetch(e); return p ? p : null;
};
(async () => {
  // 같은 출처 GET → 캐시에 저장
  await runFetch(ORIGIN + '/index.html').then(p => p);
  await new Promise(r => setTimeout(r, 0));
  check('같은 출처 GET 정적 파일은 캐시됨', cacheStore.get('parkda-v2') && cacheStore.get('parkda-v2').has(ORIGIN + '/index.html'));

  // 외부 API → respondWith 호출 안 함, 캐시 안 됨
  const extUrls = ['https://szoxnkarkdxirbyxmzgr.supabase.co/rest/v1/parkda_store?key=eq.x',
                   'https://www.googleapis.com/youtube/v3/search?q=test', 'https://dapi.kakao.com/v2/local/search/keyword.json'];
  for (const u of extUrls) {
    const p = await runFetch(u);
    check('외부 API는 서비스워커가 가로채지 않음: ' + new URL(u).hostname, p === null);
  }
  const allCached = [...cacheStore.values()].flatMap(c => [...c.keys()]);
  check('외부 API 응답은 어떤 캐시에도 없음', !allCached.some(k => !k.startsWith(ORIGIN)));

  // POST 요청 → 가로채지 않음
  const postP = await runFetch(ORIGIN + '/api/x', 'POST');
  check('POST 요청은 캐시·가로채기 대상이 아님', postP === null);

  console.log(`\nSW cache tests: PASS ${pass} / FAIL ${fail}`);
  process.exit(fail ? 1 : 0);
})();
