// 파크골프 유튜브 검색 (서버 측). 키는 환경변수 YOUTUBE_API_KEY 에만 둔다.
// 응답은 6시간 캐시한다. 키가 없거나 쿼터가 초과되면 명확한 오류 코드를 돌려준다.
const CATEGORY_QUERY = {
  '대회': '파크골프 대회',
  '레슨': '파크골프 레슨',
  '장비': '파크골프 채 장비',
  '구장': '파크골프장 소개',
};
const TTL_MS = 6 * 60 * 60 * 1000;
const memo = new Map();

function send(res, status, body, cacheControl) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', cacheControl || 'no-store');
  res.end(JSON.stringify(body));
}

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') return send(res, 405, { error: 'method_not_allowed' });
  const category = new URL(req.url, 'http://localhost').searchParams.get('category') || '대회';
  const q = CATEGORY_QUERY[category];
  if (!q) return send(res, 400, { error: 'unknown_category' });

  const key = process.env.YOUTUBE_API_KEY;
  if (!key) return send(res, 503, { error: 'not_configured' });

  const hit = memo.get(category);
  if (hit && Date.now() - hit.at < TTL_MS) return send(res, 200, hit.body, 'public, s-maxage=21600');

  const params = new URLSearchParams({
    part: 'snippet', q, type: 'video', maxResults: '6', order: 'relevance',
    relevanceLanguage: 'ko', regionCode: 'KR', key,
  });
  let upstream;
  try {
    upstream = await fetch(`https://www.googleapis.com/youtube/v3/search?${params}`, { signal: AbortSignal.timeout(7000) });
  } catch (e) {
    return send(res, 502, { error: 'upstream_unreachable' });
  }
  if (upstream.status === 403 || upstream.status === 429) {
    const text = await upstream.text();
    return send(res, 429, { error: /quota/i.test(text) ? 'quota_exceeded' : 'forbidden' });
  }
  if (!upstream.ok) return send(res, 502, { error: 'upstream_error' });

  const data = await upstream.json();
  const items = (data.items || [])
    .map(v => ({
      videoId: v.id && v.id.videoId,
      title: v.snippet && v.snippet.title,
      channel: v.snippet && v.snippet.channelTitle,
      publishedAt: v.snippet && v.snippet.publishedAt,
      thumbnail: v.snippet && v.snippet.thumbnails && v.snippet.thumbnails.medium && v.snippet.thumbnails.medium.url,
      url: v.id && v.id.videoId ? `https://www.youtube.com/watch?v=${v.id.videoId}` : null,
    }))
    .filter(i => i.videoId && i.title);
  const body = { category, items, fetchedAt: new Date().toISOString(), source: 'YouTube Data API v3' };
  memo.set(category, { at: Date.now(), body });
  return send(res, 200, body, 'public, s-maxage=21600');
};
