// 스테이징 스키마·RLS·쓰기 함수 테스트. 반드시 로컬 또는 parkda-staging 전용 DB 에서만 실행한다.
// 운영 DB 연결을 거부한다. 실행: PARKDA_TEST_PG_SOCKET=~/pgsock PARKDA_TEST_PG_PORT=54329 node tests/db/staging_rls_test.js
// (PARKDA_TEST_PG_* 가 없으면 건너뛰고 종료 코드 0 — 서버 테스트를 통과한 것으로 보고하지 않는다.)
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { Client } = require('pg');

const HOST = process.env.PARKDA_TEST_PG_SOCKET || process.env.PARKDA_TEST_PG_HOST;
const PORT = Number(process.env.PARKDA_TEST_PG_PORT || 5432);
const DB = 'parkda_test';
if (!HOST) { console.log('DB tests skipped: PARKDA_TEST_PG_SOCKET 또는 PARKDA_TEST_PG_HOST 가 없습니다.'); process.exit(0); }
if (/szoxnkarkdxirbyxmzgr/.test(HOST + process.env.PARKDA_TEST_PG_HOST)) { console.error('운영 프로젝트로 보이는 주소는 거부합니다.'); process.exit(1); }

const root = path.resolve(__dirname, '../..');
const u = { owner: '00000000-0000-4000-8000-000000000001', member: '00000000-0000-4000-8000-000000000002',
  outsider: '00000000-0000-4000-8000-000000000003', manager: '00000000-0000-4000-8000-000000000004' };
const conn = async () => { const c = new Client({ host: HOST, port: PORT, user: 'postgres', database: DB }); await c.connect(); return c; };
// 사용자 세션으로 실행: 성공하면 커밋, 오류면 되돌린다 (테스트 준비 데이터는 다음 테스트 전 seed() 가 지운다)
async function asUser(uid, fn) {
  const c = await conn();
  try {
    await c.query('begin');
    await c.query("set local role authenticated");
    await c.query("select set_config('request.jwt.claim.sub', $1, true)", [uid]);
    const out = await fn(c);
    await c.query('commit');
    return out;
  } catch (e) { await c.query('rollback').catch(() => {}); throw e; }
  finally { await c.end(); }
}
// 트랜잭션 안에서 오류를 기대할 때: 세이브포인트로 감싸 나머지 작업이 이어지게 한다
async function expectSP(c, sql, params, code) {
  await c.query('savepoint sp');
  try { await c.query(sql, params); } catch (e) {
    await c.query('rollback to savepoint sp');
    if (code && !String(e.message).includes(code)) throw new Error(`expected ${code}, got ${e.message}`);
    return;
  }
  throw new Error('expected error ' + (code || '') + ' but succeeded');
}
async function admin(fn) { const c = await conn(); try { return await fn(c); } finally { await c.end(); } }
const results = []; let failed = 0;
async function test(name, fn) {
  try { await fn(); results.push(['PASS', name]); console.log('PASS ' + name); }
  catch (e) { failed++; results.push(['FAIL', name, e.message]); console.log('FAIL ' + name + ' — ' + e.message); }
}
async function expectError(promise, code) {
  try { await promise; } catch (e) { if (code && !String(e.message).includes(code)) throw new Error(`expected ${code}, got ${e.message}`); return; }
  throw new Error('expected error ' + (code || '') + ' but succeeded');
}

async function seed() {
  await admin(async c => {
    await c.query(`truncate public.club_members, public.clubs, public.meetup_participants, public.meetups, public.game_scores, public.score_audit_logs, public.games, public.admin_audit_logs cascade`);
    await c.query(`delete from auth.users`);
    for (const [k, id] of Object.entries(u)) await c.query('insert into auth.users (id, name) values ($1, $2)', [id, k]);
    const r = await c.query(`insert into public.clubs (name, region, created_by) values ('테스트회', '부산', $1) returning id`, [u.owner]);
    await c.query(`insert into public.club_members (club_id, user_id, role, status) values ($1, $2, 'owner', 'approved')`, [r.rows[0].id, u.owner]);
    globalThis.CLUB = r.rows[0].id;
  });
}

(async () => {
  // 스키마 적용 (이미 적용돼 있으면 건너뛴다)
  await admin(async c => {
    const has = await c.query("select to_regclass('public.clubs') is not null as ok");
    if (!has.rows[0].ok) {
      await c.query(fs.readFileSync(path.join(root, 'supabase/staging/0001_platform_schema.sql'), 'utf8'));
      await c.query(fs.readFileSync(path.join(root, 'supabase/staging/0002_write_functions.sql'), 'utf8'));
    }
  });

  await seed();

  await test('RLS: 외부인은 동호회 회원 목록(본인 외 행)을 볼 수 없다', async () => {
    const n = await asUser(u.outsider, c => c.query('select count(*)::int n from public.club_members where club_id = $1', [CLUB]));
    assert.equal(n.rows[0].n, 0);
  });

  await test('RLS: 회원 신청은 pending 으로만 가능 (직접 approved 삽입 거부)', async () => {
    await expectError(asUser(u.member, c => c.query(
      `insert into public.club_members (club_id, user_id, role, status) values ($1, $2, 'member', 'approved')`, [CLUB, u.member])), 'row-level');
  });

  await test('RLS: 운영자 승인은 직접 UPDATE 로 불가 (행 0건) → 함수로만 가능', async () => {
    await asUser(u.member, c => c.query(`select public.request_join($1)`, [CLUB]));
    const r = await asUser(u.owner, c => c.query(`update public.club_members set status='approved' where club_id=$1 and user_id=$2 and status='pending' returning 1`, [CLUB, u.member]));
    assert.equal(r.rowCount, 0);
  });

  await test('함수: 운영자 승인 → 회원 승격, 감사 로그 기록', async () => {
    await seed();
    await asUser(u.member, c => c.query(`select public.request_join($1)`, [CLUB]));
    await asUser(u.owner, c => c.query(`select public.decide_member($1, $2, true)`, [CLUB, u.member]));
    const s = await admin(c => c.query('select status from public.club_members where club_id=$1 and user_id=$2', [CLUB, u.member]));
    assert.equal(s.rows[0].status, 'approved');
    const a = await admin(c => c.query("select count(*)::int n from public.admin_audit_logs where action='member_approved'"));
    assert.equal(a.rows[0].n, 1);
  });

  await test('함수: 일반 회원은 승인할 수 없다 (forbidden)', async () => {
    await seed();
    await asUser(u.member, c => c.query(`select public.request_join($1)`, [CLUB]));
    await expectError(asUser(u.outsider, c => c.query(`select public.decide_member($1, $2, true)`, [CLUB, u.member])), 'forbidden');
  });

  // 모임: 회원 2명 승인 후 생성
  async function meetupWithMembers(capacity) {
    await seed();
    await admin(c => c.query(`insert into public.club_members (club_id, user_id, role, status) values ($1,$2,'member','approved'), ($1,$3,'member','approved')`, [CLUB, u.member, u.manager]));
    const r = await asUser(u.owner, c => c.query(`select public.create_meetup($1,'venue-1', '2026-11-05', '08:00', $2) as id`, [CLUB, capacity]));
    return r.rows[0].id;
  }

  await test('정원 초과 방지: 정원 2 모임에 동시에 10명이 신청해도 참가 2명을 넘지 않는다', async () => {
    await seed();
    const mid = await asUser(u.owner, c => c.query(`select public.create_meetup(null,'venue-1','2026-11-05','08:00', 2) as id`)).then(r => r.rows[0].id);
    // 생성자 1명이 이미 참가. 동시에 10명이 신청하면 1명만 참가, 9명 대기여야 한다.
    const ids = Array.from({ length: 10 }, (_, i) => `00000000-0000-4000-8000-0000000001${String(i).padStart(2, '0')}`);
    await admin(c => c.query(`insert into auth.users (id, name) select unnest($1::uuid[]), 'p'`, [ids]));
    const outs = await Promise.allSettled(ids.map(id => asUser(id, c => c.query('select public.join_meetup($1) as s', [mid])).then(r => r.rows[0].s)));
    const statuses = outs.filter(o => o.status === 'fulfilled').map(o => o.value);
    const errors = outs.filter(o => o.status === 'rejected');
    const active = await admin(c => c.query(`select count(*)::int n from public.meetup_participants where meetup_id=$1 and status in ('joined','confirmed')`, [mid]));
    assert.ok(errors.length === 0, 'unexpected errors: ' + errors.map(e => e.reason.message).join(';'));
    assert.equal(active.rows[0].n, 2, 'active participants must not exceed capacity');
    assert.equal(statuses.filter(s => s === 'waitlisted').length, 9);
  });

  await test('대기 승격: 참가자가 취소하면 가장 먼저 기다린 사람이 올라간다', async () => {
    await seed();
    const mid = await asUser(u.owner, c => c.query(`select public.create_meetup(null,'venue-1','2026-11-05','08:00', 2) as id`)).then(r => r.rows[0].id);
    await asUser(u.member, c => c.query('select public.join_meetup($1)', [mid]));
    await asUser(u.manager, c => c.query('select public.join_meetup($1)', [mid]));  // 대기 1번
    const outsider2 = '00000000-0000-4000-8000-000000000009';
    await admin(c => c.query(`insert into auth.users (id, name) values ($1,'late')`, [outsider2]));
    await asUser(outsider2, c => c.query('select public.join_meetup($1)', [mid]));  // 대기 2번
    const promoted = await asUser(u.member, c => c.query('select public.cancel_join($1) as p', [mid]));
    assert.equal(promoted.rows[0].p, u.manager);
    const s = await admin(c => c.query(`select status from public.meetup_participants where meetup_id=$1 and user_id=$2`, [mid, u.manager]));
    assert.equal(s.rows[0].status, 'joined');
  });

  await test('함께 치기: 같은 사람 중복 참가 거부', async () => {
    const mid = await meetupWithMembers(4);
    await asUser(u.member, c => c.query('select public.join_meetup($1)', [mid]));
    await expectError(asUser(u.member, c => c.query('select public.join_meetup($1)', [mid])), 'duplicate');
  });

  await test('동호회 모임: 외부인은 참가할 수 없다', async () => {
    const mid = await meetupWithMembers(4);
    await expectError(asUser(u.outsider, c => c.query('select public.join_meetup($1)', [mid])), 'forbidden');
  });

  // 경기: 생성자 + 2명
  async function gameWithPlayers(holes = 9) {
    const mid = await meetupWithMembers(4);
    const g = await asUser(u.owner, c => c.query(`select public.create_game($1, $2, $3, $4::uuid[]) as id`,
      [CLUB, mid, holes, [u.owner, u.member]]));
    return g.rows[0].id;
  }

  await test('점수 입력: 범위 밖 타수·홀·선수는 거부', async () => {
    const g = await gameWithPlayers(9);
    await expectError(asUser(u.owner, c => c.query('select public.submit_score($1,$2,1,0)', [g, u.owner])), 'invalid_strokes');
    await expectError(asUser(u.owner, c => c.query('select public.submit_score($1,$2,1,16)', [g, u.owner])), 'invalid_strokes');
    await expectError(asUser(u.owner, c => c.query('select public.submit_score($1,$2,10,3)', [g, u.owner])), 'invalid_hole');
    await expectError(asUser(u.owner, c => c.query('select public.submit_score($1,$2,1,3)', [g, u.manager])), 'unknown_player');
  });

  await test('점수 입력: 외부인은 점수를 넣을 수 없고 점수 조회도 0건', async () => {
    const g = await gameWithPlayers(9);
    await expectError(asUser(u.outsider, c => c.query('select public.submit_score($1,$2,1,3)', [g, u.owner])), 'forbidden');
    const n = await asUser(u.outsider, c => c.query('select count(*)::int n from public.game_scores where game_id=$1', [g]));
    assert.equal(n.rows[0].n, 0);
  });

  await test('점수 이력: 수정 전 값과 수정 후 값이 감사 로그에 남는다', async () => {
    const g = await gameWithPlayers(9);
    const r = await asUser(u.owner, async c => {
      await c.query('select public.submit_score($1,$2,1,4)', [g, u.owner]);
      const old = await c.query('select public.submit_score($1,$2,1,5) as old', [g, u.owner]);
      const logs = await c.query(`select count(*)::int n from public.score_audit_logs where game_id=$1 and action='score' and (detail->>'to')::int=5 and (detail->>'from')::int=4`, [g]);
      return { old: old.rows[0].old, n: logs.rows[0].n };
    });
    assert.equal(r.old, 4);
    assert.equal(r.n, 1);
  });

  await test('경기 중단: 중단 중에는 점수 입력 불가, 재개 후 가능', async () => {
    const g = await gameWithPlayers(9);
    await asUser(u.owner, async c => {
      await c.query('select public.set_game_paused($1, true)', [g]);
      await expectSP(c, 'select public.submit_score($1,$2,1,3)', [g, u.owner], 'game_not_editable');
      await c.query('select public.set_game_paused($1, false)', [g]);
      await c.query('select public.submit_score($1,$2,1,3)', [g, u.owner]);
    });
  });

  await test('결과 확정: 점수가 모두 있어야 하며, 확정 후 점수 입력은 거부된다', async () => {
    const g = await gameWithPlayers(9);
    await asUser(u.owner, async c => {
      await expectSP(c, 'select public.confirm_result($1)', [g], 'incomplete_scores');
    });
  });

  await test('결과 확정: 총타수 순위(동점은 같은 순위), 확정 후 수정은 잠금 해제 사유가 있어야 한다', async () => {
    const g = await gameWithPlayers(9);
    await asUser(u.owner, async c => {
      for (let h = 1; h <= 9; h++) {
        await c.query('select public.submit_score($1,$2,$3,4)', [g, u.owner, h]);
        await c.query('select public.submit_score($1,$2,$3,4)', [g, u.member, h]);
      }
      const res = await c.query('select public.confirm_result($1) as r', [g]);
      const rows = res.rows[0].r;
      assert.equal(rows.length, 2);
      assert.equal(rows[0].rank, 1); assert.equal(rows[1].rank, 1);  // 동점 공동 1위
      await expectSP(c, 'select public.submit_score($1,$2,1,3)', [g, u.owner], 'game_not_editable');
      await expectSP(c, 'select public.unlock_final($1, $2)', [g, ''], 'reason_required');
      await c.query('select public.unlock_final($1, $2)', [g, '입력 오류 정정']);
      await c.query('select public.submit_score($1,$2,1,3)', [g, u.owner]);
    });
  });

  await test('비회원·익명 사용자는 쓰기 함수를 호출할 수 없다', async () => {
    const c = await conn();
    try {
      await c.query('begin'); await c.query('set local role anon');
      await expectError(c.query(`select public.request_join($1)`, [CLUB]), 'permission denied');
    } finally { await c.query('rollback').catch(() => {}); await c.end(); }
  });

  console.log(`\nDB tests: PASS ${results.filter(r => r[0] === 'PASS').length} / FAIL ${failed}`);
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error('DB test setup failed:', e.message); process.exit(1); });
