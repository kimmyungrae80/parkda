// 결제 서버 처리 (토스페이먼츠 테스트 환경 전용). 실결제 키(live_)는 거부한다.
// - confirm: 브라우저가 보낸 결제 결과를 신뢰하지 않고, 주문 금액을 서버 기록과 대조한 뒤 토스 API로 승인한다.
// - webhook: 본문을 믿지 않는다. paymentKey 로 토스 API 를 다시 조회해 상태를 정한다.
// - 같은 orderId 는 한 번만 처리한다 (중복 결제 방지).
// 비밀키는 환경변수 TOSS_SECRET_KEY 에만 둔다. 이 파일에 키를 쓰지 않는다.
const PRICES = require('../config/pricing.json');
const TOSS = 'https://api.tosspayments.com/v1';

function send(res, status, body) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end(JSON.stringify(body));
}
function secretKey() {
  const k = process.env.TOSS_SECRET_KEY || '';
  if (!k) return { error: 'not_configured' };
  if (!k.startsWith('test_sk_')) return { error: 'live_key_refused' };  // 실결제 키는 어떤 경우에도 사용하지 않음
  return { key: k };
}
function auth(key) { return 'Basic ' + Buffer.from(key + ':').toString('base64'); }

// store 인터페이스: get(orderId), put(orderId, row). 테스트에서는 메모리 구현, 실제 배포에서는 staging DB(서비스 역할) 구현을 주입.
async function confirm({ body, store, fetchImpl = fetch }) {
  const k = secretKey(); if (k.error) return { status: 503, body: { error: k.error } };
  const { paymentKey, orderId, amount } = body || {};
  if (!paymentKey || !orderId) return { status: 400, body: { error: 'invalid_request' } };
  const order = await store.get(orderId);
  if (!order) return { status: 404, body: { error: 'unknown_order' } };
  if (order.status === 'done') return { status: 200, body: { status: 'done', duplicate: true } };  // 중복 승인 방지
  if (Number(amount) !== Number(order.amount)) return { status: 400, body: { error: 'amount_mismatch' } };
  const r = await fetchImpl(`${TOSS}/payments/confirm`, {
    method: 'POST', headers: { Authorization: auth(k.key), 'Content-Type': 'application/json' },
    body: JSON.stringify({ paymentKey, orderId, amount: order.amount }),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    await store.put(orderId, { ...order, status: 'failed', failure: data.code || 'confirm_failed' });
    return { status: 402, body: { error: 'payment_failed', code: data.code || null } };
  }
  await store.put(orderId, { ...order, status: 'done', providerPaymentKey: paymentKey });
  return { status: 200, body: { status: 'done' } };
}

// 웹훅: 본문 대신 토스 조회 결과로 상태를 정한다.
async function webhook({ body, store, fetchImpl = fetch }) {
  const k = secretKey(); if (k.error) return { status: 503, body: { error: k.error } };
  const paymentKey = body && body.data && body.data.paymentKey;
  if (!paymentKey) return { status: 400, body: { error: 'invalid_request' } };
  const r = await fetchImpl(`${TOSS}/payments/${encodeURIComponent(paymentKey)}`, { headers: { Authorization: auth(k.key) } });
  if (!r.ok) return { status: 502, body: { error: 'verify_failed' } };
  const p = await r.json();
  const order = await store.get(p.orderId);
  if (!order) return { status: 404, body: { error: 'unknown_order' } };
  const map = { DONE: 'done', CANCELED: 'canceled', PARTIAL_CANCELED: 'canceled', ABORTED: 'failed', EXPIRED: 'failed' };
  const next = map[p.status] || order.status;
  if (next !== order.status) await store.put(p.orderId, { ...order, status: next });
  return { status: 200, body: { status: next } };
}

module.exports = { confirm, webhook, PRICES, _secretKey: secretKey };
