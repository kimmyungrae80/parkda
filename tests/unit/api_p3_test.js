// 사용법: node tests/unit/api_p3_test.js  (반경·카테고리·구장명 검색. 실제 외부 호출 없음)
const path = require('path');
const root = path.resolve(__dirname, '../..');
const realFetch = globalThis.fetch;
const SECRET_K = 'TEST_KAKAO_KEY_654321';
const SECRET_Y = 'TEST_YT_KEY_123456';
function fakeRes() { return { statusCode: 0, headers: {}, body: '', setHeader(k, v) { this.headers[k.toLowerCase()] = v; }, end(b) { this.body = b; } }; }
const req = (url, method = 'GET') => ({ url, method });
let pass = 0, fail = 0;
const check = (name, cond) => { cond ? pass++ : fail++; console.log((cond ? 'PASS ' : 'FAIL ') + name); };
const food = require(path.join(root, 'api/food.js'));
const youtube = require(path.join(root, 'api/youtube.js'));

(async () => {
  process.env.KAKAO_REST_KEY = SECRET_K;
  const urls = [];
  globalThis.fetch = async (url) => { urls.push(String(url)); return { ok: true, status: 200, json: async () => ({ documents: [] }) }; };
  let r = fakeRes(); await food(req('/api/food?x=128.9&y=35.2&radius=3000&category=CE7'), r);
  check('맛집: 반경 3km·카페(CE7) 요청 전달', r.statusCode === 200 && urls[0].includes('radius=3000') && urls[0].includes('category_group_code=CE7'));
  r = fakeRes(); await food(req('/api/food?x=128.9&y=35.2&radius=2000'), r);
  check('맛집: 허용되지 않은 반경 400', r.statusCode === 400);
  r = fakeRes(); await food(req('/api/food?x=128.9&y=35.2&category=AT4'), r);
  check('맛집: 허용되지 않은 카테고리 400', r.statusCode === 400);

  process.env.YOUTUBE_API_KEY = SECRET_Y;
  const yurls = [];
  globalThis.fetch = async (url) => { yurls.push(String(url)); return { ok: true, status: 200, json: async () => ({ items: [] }) }; };
  r = fakeRes(); await youtube(req('/api/youtube?q=' + encodeURIComponent('대저생태공원')), r);
  check('유튜브: 구장명 검색 질의 전달', r.statusCode === 200 && new URL(yurls[0]).searchParams.get('q') === '파크골프 대저생태공원');
  r = fakeRes(); await youtube(req('/api/youtube?q=' + encodeURIComponent('<script>')), r);
  check('유튜브: 허용되지 않은 문자 질의 400 (주입 방지)', r.statusCode === 400);
  globalThis.fetch = realFetch;
  console.log(`\nAPI P3 tests: PASS ${pass} / FAIL ${fail}`);
  process.exit(fail ? 1 : 0);
})();
