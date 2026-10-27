// 사용법: node tests/unit/api_test.js
// 서버 API 핸들러를 가짜 fetch 로 검증한다 (실제 외부 호출 없음).
const path = require('path');
const root = path.resolve(__dirname, '../..');
const youtube = require(path.join(root, 'api/youtube.js'));
const food = require(path.join(root, 'api/food.js'));

function fakeRes() {
  return { statusCode: 0, headers: {}, body: '',
    setHeader(k, v) { this.headers[k.toLowerCase()] = v; },
    end(b) { this.body = b; } };
}
const req = (url, method = 'GET') => ({ url, method });
let pass = 0, fail = 0;
const check = (name, cond, detail = '') => { cond ? pass++ : fail++; console.log((cond ? 'PASS ' : 'FAIL ') + name + (detail ? `  [${detail}]` : '')); };
const realFetch = globalThis.fetch;
const SECRET_Y = 'TEST_YT_KEY_123456';
const SECRET_K = 'TEST_KAKAO_KEY_654321';

(async () => {
  // ── YouTube ──
  delete process.env.YOUTUBE_API_KEY;
  let r = fakeRes(); await youtube(req('/api/youtube?category=대회'), r);
  check('YouTube: 키 없으면 503 not_configured', r.statusCode === 503 && JSON.parse(r.body).error === 'not_configured');

  process.env.YOUTUBE_API_KEY = SECRET_Y;
  globalThis.fetch = async (url) => {
    if (!String(url).includes('googleapis.com/youtube/v3/search')) throw new Error('unexpected ' + url);
    return { ok: true, status: 200, json: async () => ({ items: [
      { id: { videoId: 'AAAAAAAAAAA' }, snippet: { title: '가상 영상', channelTitle: '채널', publishedAt: '2026-01-01T00:00:00Z', thumbnails: { medium: { url: 'https://i.ytimg.com/x.jpg' } } } },
      { id: {}, snippet: { title: '영상ID 없음' } },
    ] }) };
  };
  r = fakeRes(); await youtube(req('/api/youtube?category=레슨'), r);
  const yb = JSON.parse(r.body);
  check('YouTube: 정상 응답 200 + 6시간 캐시 헤더', r.statusCode === 200 && r.headers['cache-control'] === 'public, s-maxage=21600');
  check('YouTube: 영상 ID 없는 항목 제외, 필수 필드 포함', yb.items.length === 1 && yb.items[0].url.endsWith('AAAAAAAAAAA') && yb.items[0].title === '가상 영상');
  check('YouTube: 응답에 API 키가 없음', !r.body.includes(SECRET_Y));

  globalThis.fetch = async () => ({ ok: false, status: 403, text: async () => '{"error":{"message":"quotaExceeded"}}' });
  r = fakeRes(); await youtube(req('/api/youtube?category=장비'), r);
  check('YouTube: 쿼터 초과 → 429 quota_exceeded', r.statusCode === 429 && JSON.parse(r.body).error === 'quota_exceeded');

  r = fakeRes(); await youtube(req('/api/youtube?category=없는분류'), r);
  check('YouTube: 허용되지 않은 분류 400', r.statusCode === 400);

  r = fakeRes(); await youtube(req('/api/youtube?category=대회', 'POST'), r);
  check('YouTube: GET 외 메서드 405', r.statusCode === 405);

  globalThis.fetch = async () => { throw new Error('network down'); };
  r = fakeRes(); await youtube(req('/api/youtube?category=대회'), r);
  check('YouTube: 네트워크 오류 → 502 (키 노출 없음)', r.statusCode === 502 && !r.body.includes(SECRET_Y));

  // ── 카카오 맛집 ──
  delete process.env.KAKAO_REST_KEY;
  r = fakeRes(); await food(req('/api/food?x=128.9&y=35.2'), r);
  check('맛집: 키 없으면 503 not_configured', r.statusCode === 503);

  process.env.KAKAO_REST_KEY = SECRET_K;
  r = fakeRes(); await food(req('/api/food?x=abc&y=35'), r);
  check('맛집: 좌표 숫자 아님 → 400', r.statusCode === 400);
  r = fakeRes(); await food(req('/api/food?x=10&y=35'), r);
  check('맛집: 한국 범위 밖 좌표 → 400', r.statusCode === 400);

  let calledUrl = '', calledHeaders = {};
  globalThis.fetch = async (url, opts) => { calledUrl = String(url); calledHeaders = opts.headers;
    return { ok: true, status: 200, json: async () => ({ documents: [
      { place_name: '가상식당', category_name: '음식점 > 한식', distance: '120', phone: '', road_address_name: '가상로 1', place_url: 'https://place.map.kakao.com/1' },
    ] }) }; };
  r = fakeRes(); await food(req('/api/food?x=128.9&y=35.2'), r);
  const fb = JSON.parse(r.body);
  check('맛집: 카테고리 FD6·반경 1km·선택 좌표 기준 요청', calledUrl.includes('category_group_code=FD6') && calledUrl.includes('radius=1000') && calledUrl.includes('x=128.9') && calledUrl.includes('y=35.2'));
  check('맛집: 인증은 서버 헤더로만 전달', calledHeaders.Authorization === 'KakaoAK ' + SECRET_K && !r.body.includes(SECRET_K));
  check('맛집: 결과 정규화 (이름·분류·거리·주소·링크)', fb.items.length === 1 && fb.items[0].category === '한식' && fb.items[0].distanceM === 120 && fb.items[0].address === '가상로 1');
  check('맛집: 광고·제휴 표시 구분 없음을 출처에 명시', /광고·제휴 표시 구분 없음/.test(fb.source));
  check('맛집: 24시간 캐시 헤더', r.headers['cache-control'] === 'public, s-maxage=86400');

  globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => ({ documents: [] }) });
  r = fakeRes(); await food(req('/api/food?x=127.0&y=37.0'), r);
  check('맛집: 검색 결과 없음 → 200, items 빈 배열', r.statusCode === 200 && JSON.parse(r.body).items.length === 0);

  globalThis.fetch = async () => ({ ok: false, status: 429, json: async () => ({}) });
  r = fakeRes(); await food(req('/api/food?x=127.1&y=37.1'), r);
  check('맛집: 할당량 초과 → 429 quota_exceeded', r.statusCode === 429 && JSON.parse(r.body).error === 'quota_exceeded');

  globalThis.fetch = async () => ({ ok: false, status: 401, json: async () => ({}) });
  r = fakeRes(); await food(req('/api/food?x=127.2&y=37.2'), r);
  check('맛집: 인증 실패 → 503 kakao_auth (키 노출 없음)', r.statusCode === 503 && JSON.parse(r.body).error === 'kakao_auth' && !r.body.includes(SECRET_K));

  // ── 주소 → 좌표 (지오코딩) ──
  const geocode = require(path.join(root, 'api/geocode.js'));
  delete process.env.KAKAO_REST_KEY;
  r = fakeRes(); await geocode(req('/api/geocode?address=' + encodeURIComponent('부산광역시 북구 화명동 1718-11')), r);
  check('지오코딩: 키 없으면 503', r.statusCode === 503);
  process.env.KAKAO_REST_KEY = SECRET_K;
  r = fakeRes(); await geocode(req('/api/geocode?address=ab'), r);
  check('지오코딩: 너무 짧은 주소 400', r.statusCode === 400);
  globalThis.fetch = async (url, opts) => { check('지오코딩: 주소 검색 엔드포인트 호출', String(url).includes('/v2/local/search/address.json') && opts.headers.Authorization === 'KakaoAK ' + SECRET_K);
    return { ok: true, status: 200, json: async () => ({ documents: [{ x: '129.0067', y: '35.2143' }] }) }; };
  r = fakeRes(); await geocode(req('/api/geocode?address=' + encodeURIComponent('부산광역시 북구 화명동 1718-11')), r);
  const gb = JSON.parse(r.body);
  check('지오코딩: 카카오 응답 좌표를 그대로 사용 (y=위도, x=경도)', r.statusCode === 200 && gb.lat === 35.2143 && gb.lng === 129.0067);
  check('지오코딩: 30일 캐시, 키 미노출', r.headers['cache-control'] === 'public, s-maxage=2592000' && !r.body.includes(SECRET_K));
  globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => ({ documents: [] }) });
  r = fakeRes(); await geocode(req('/api/geocode?address=' + encodeURIComponent('없는주소 0000번지')), r);
  check('지오코딩: 결과 없음 404', r.statusCode === 404);
  globalThis.fetch = realFetch;
  globalThis.fetch = realFetch;
  console.log(`\nAPI tests: PASS ${pass} / FAIL ${fail}`);
  process.exit(fail ? 1 : 0);
})();
