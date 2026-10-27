// 사용법: node tests/unit/payments_test.js  (토스 API 는 가짜 fetch. 실제 결제 없음)
const path = require('path');
const pay = require(path.join(__dirname, '../../api/payments.js'));
let pass = 0, fail = 0;
const check = (n, c) => { c ? pass++ : fail++; console.log((c ? 'PASS ' : 'FAIL ') + n); };
const memStore = (rows) => ({ get: async (id) => rows[id] || null, put: async (id, r) => { rows[id] = r; } });
const resp = (ok, body) => ({ ok, status: ok ? 200 : 400, json: async () => body });
const orderRow = { status: 'requested', amount: pay.PRICES.plans.club_pro.monthly, clubId: 'c1' };

(async () => {
  const realKey = process.env.TOSS_SECRET_KEY;
  delete process.env.TOSS_SECRET_KEY;
  let r = await pay.confirm({ body: { paymentKey: 'p', orderId: 'o1', amount: 14900 }, store: memStore({ o1: orderRow }) });
  check('키 없으면 503 (서버 설정 필요)', r.status === 503);

  process.env.TOSS_SECRET_KEY = 'live_sk_THIS_IS_NOT_REAL_123';
  r = await pay.confirm({ body: { paymentKey: 'p', orderId: 'o1', amount: 14900 }, store: memStore({ o1: orderRow }) });
  check('실결제 키(live_)는 거부', r.status === 503 && r.body.error === 'live_key_refused');

  process.env.TOSS_SECRET_KEY = 'test_sk_TEST_ONLY_000000';
  let calls = 0;
  const fetchOk = async () => { calls++; return resp(true, { status: 'DONE' }); };
  let rows = { o1: { ...orderRow } };
  r = await pay.confirm({ body: { paymentKey: 'pk1', orderId: 'o1', amount: 1 }, store: memStore(rows), fetchImpl: fetchOk });
  check('브라우저가 보낸 금액이 서버 기록과 다르면 거부', r.status === 400 && r.body.error === 'amount_mismatch' && calls === 0);

  r = await pay.confirm({ body: { paymentKey: 'pk1', orderId: 'o1', amount: 14900 }, store: memStore(rows), fetchImpl: fetchOk });
  check('정상 승인 → done', r.status === 200 && r.body.status === 'done' && calls === 1);
  r = await pay.confirm({ body: { paymentKey: 'pk1', orderId: 'o1', amount: 14900 }, store: memStore(rows), fetchImpl: fetchOk });
  check('같은 주문 중복 승인 요청은 재호출 없이 처리', r.body.duplicate === true && calls === 1);

  rows = { o2: { ...orderRow } };
  r = await pay.confirm({ body: { paymentKey: 'pk2', orderId: 'o2', amount: 14900 }, store: memStore(rows),
    fetchImpl: async () => resp(false, { code: 'REJECT_CARD_PAYMENT' }) });
  check('토스 승인 실패 → failed 기록', r.status === 402 && rows.o2.status === 'failed');

  // 웹훅: 본문 상태를 믿지 않고 토스 조회 결과를 사용
  rows = { o3: { ...orderRow, status: 'done' } };
  r = await pay.webhook({ body: { data: { paymentKey: 'pk3' }, status: 'DONE' }, store: memStore(rows),
    fetchImpl: async () => resp(true, { orderId: 'o3', status: 'CANCELED' }) });
  check('웹훅: 조회 결과가 취소이면 canceled', r.body.status === 'canceled' && rows.o3.status === 'canceled');
  rows = { o4: { ...orderRow } };
  r = await pay.webhook({ body: { data: { paymentKey: 'pk4' }, status: 'DONE' }, store: memStore(rows),
    fetchImpl: async () => resp(false, {}) });
  check('웹훅: 토스 조회 실패 시 상태를 바꾸지 않음', r.status === 502 && rows.o4.status === 'requested');

  check('가격은 테스트 가설 14,900원 (실과금 아님)', pay.PRICES.plans.club_pro.status === 'test_hypothesis');
  if (realKey) process.env.TOSS_SECRET_KEY = realKey; else delete process.env.TOSS_SECRET_KEY;
  console.log(`\npayments tests: PASS ${pass} / FAIL ${fail}`);
  process.exit(fail ? 1 : 0);
})();
