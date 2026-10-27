// 주소 → 좌표 (카카오 로컬 주소 검색). 검증된 구장 주소를 좌표로 바꾸는 용도.
// 좌표는 카카오 응답을 그대로 쓰며, 직접 추정하거나 입력하지 않는다. 30일 캐시.
const TTL_MS = 30 * 24 * 60 * 60 * 1000;
const memo = new Map();

function send(res, status, body, cacheControl) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', cacheControl || 'no-store');
  res.end(JSON.stringify(body));
}

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') return send(res, 405, { error: 'method_not_allowed' });
  const address = (new URL(req.url, 'http://localhost').searchParams.get('address') || '').trim();
  if (address.length < 4 || address.length > 120) return send(res, 400, { error: 'invalid_address' });

  const key = process.env.KAKAO_REST_KEY;
  if (!key) return send(res, 503, { error: 'not_configured' });

  const hit = memo.get(address);
  if (hit && Date.now() - hit.at < TTL_MS) return send(res, 200, hit.body, 'public, s-maxage=2592000');

  let upstream;
  try {
    upstream = await fetch(`https://dapi.kakao.com/v2/local/search/address.json?query=${encodeURIComponent(address)}`, {
      headers: { Authorization: `KakaoAK ${key}` },
      signal: AbortSignal.timeout(7000),
    });
  } catch (e) {
    return send(res, 502, { error: 'upstream_unreachable' });
  }
  if (upstream.status === 401 || upstream.status === 403) return send(res, 503, { error: 'kakao_auth' });
  if (upstream.status === 429) return send(res, 429, { error: 'quota_exceeded' });
  if (!upstream.ok) return send(res, 502, { error: 'upstream_error' });

  const data = await upstream.json();
  const doc = (data.documents || [])[0];
  if (!doc) return send(res, 404, { error: 'not_found' });
  const body = { address, lat: Number(doc.y), lng: Number(doc.x), source: '카카오 로컬 주소 검색', fetchedAt: new Date().toISOString() };
  memo.set(address, { at: Date.now(), body });
  return send(res, 200, body, 'public, s-maxage=2592000');
};
