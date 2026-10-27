// 구장 주변 음식점·카페 검색 (카카오 로컬 API). 반경 1·3·5km, 카테고리 FD6(음식점)·CE7(카페).
// REST 키는 환경변수 KAKAO_REST_KEY 에만 둔다. 결과는 24시간 캐시한다.
const TTL_MS = 24 * 60 * 60 * 1000;
const memo = new Map();

function send(res, status, body, cacheControl) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', cacheControl || 'no-store');
  res.end(JSON.stringify(body));
}

// 대한민국 범위 밖 좌표는 거부 (잘못된 요청으로 API 할당량을 쓰지 않도록)
function parseCoord(params) {
  const x = Number(params.get('x'));
  const y = Number(params.get('y'));
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
  if (x < 124 || x > 132 || y < 33 || y > 39) return null;
  const radius = Number(params.get('radius') || 1000);
  const category = params.get('category') || 'FD6';
  if (![1000, 3000, 5000].includes(radius)) return null;
  if (!['FD6', 'CE7'].includes(category)) return null;
  return { x, y, radius, category };
}

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') return send(res, 405, { error: 'method_not_allowed' });
  const params = new URL(req.url, 'http://localhost').searchParams;
  const pos = parseCoord(params);
  if (!pos) return send(res, 400, { error: 'invalid_coordinates' });

  const key = process.env.KAKAO_REST_KEY;
  if (!key) return send(res, 503, { error: 'not_configured' });

  const cacheKey = `${pos.x.toFixed(4)},${pos.y.toFixed(4)},${pos.radius},${pos.category}`;
  const hit = memo.get(cacheKey);
  if (hit && Date.now() - hit.at < TTL_MS) return send(res, 200, hit.body, 'public, s-maxage=86400');

  const qs = new URLSearchParams({
    category_group_code: pos.category, x: String(pos.x), y: String(pos.y),
    radius: String(pos.radius), sort: 'distance', size: '15',
  });
  let upstream;
  try {
    upstream = await fetch(`https://dapi.kakao.com/v2/local/search/category.json?${qs}`, {
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
  const items = (data.documents || []).map(d => ({
    name: d.place_name,
    category: (d.category_name || '').split('>').pop().trim(),
    distanceM: Number(d.distance) || null,
    phone: d.phone || '',
    address: d.road_address_name || d.address_name || '',
    url: d.place_url || '',
  }));
  const body = { items, radius: pos.radius, category: pos.category, fetchedAt: new Date().toISOString(),
    source: '카카오 로컬 API 일반 검색 결과 (광고·제휴 표시 구분 없음)' };
  memo.set(cacheKey, { at: Date.now(), body });
  return send(res, 200, body, 'public, s-maxage=86400');
};
