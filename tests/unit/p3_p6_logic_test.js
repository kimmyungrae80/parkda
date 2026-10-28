// P3~P6 순수 규칙 테스트 (데모·테스트 전용). 실행: node tests/unit/p3_p6_logic_test.js
const assert = require('assert');
const club = require('../../lib/club-logic');
const meet = require('../../lib/meeting-logic');
const score = require('../../lib/score-logic');
const pro = require('../../lib/pro-logic');
let n = 0; const t = (name, fn) => { fn(); n++; console.log('ok -', name); };

t('동호회: 가입 신청 후 운영자만 승인할 수 있다', () => {
  const c = club.createClub({ name: '테스트클럽', region: '부산', ownerId: 'o' });
  assert.deepEqual(club.requestJoin(c, 'a'), { ok: true });
  assert.equal(club.requestJoin(c, 'a').reason, 'already');
  assert.equal(club.decide(c, 'member', 'a', true).reason, 'forbidden');
  assert.deepEqual(club.decide(c, 'manager', 'a', false), { ok: true });
  assert.equal(club.findMember(c, 'a').status, 'rejected');
});
t('동호회: 운영자는 탈퇴할 수 없고 일반 회원은 탈퇴 가능', () => {
  const c = club.createClub({ name: '테스트클럽', region: '부산', ownerId: 'o' });
  club.requestJoin(c, 'a'); club.decide(c, 'owner', 'a', true);
  assert.equal(club.leave(c, 'o').reason, 'owner_cannot_leave');
  assert.deepEqual(club.leave(c, 'a'), { ok: true });
});
t('동호회: 일반 회원 목록은 승인 회원만, 운영자는 상태까지', () => {
  const c = club.createClub({ name: '테스트클럽', region: '부산', ownerId: 'o' });
  club.requestJoin(c, 'a');
  assert.equal(club.listMembers(c, 'member').length, 1);
  assert.equal(club.listMembers(c, 'manager').length, 2);
  assert.equal(club.listMembers(c, 'manager')[1].status, 'pending');
});
t('동호회: 출석률은 출석 기록이 있는 모임만 센다', () => {
  const ms = [{ attendance: { a: true } }, { attendance: { a: false } }, {}];
  assert.equal(club.attendanceRate(ms, 'a'), 50);
  assert.equal(club.attendanceRate([{}], 'a'), null);
  assert.equal(club.recordAttendance(ms[2], 'member', { a: true }).reason, 'forbidden');
});

t('함께 치기: 정원 초과는 대기, 취소하면 대기 1번이 승격', () => {
  const m = meet.createMeetup({ capacity: 2, creatorId: 'h' });
  assert.equal(meet.join(m, 'a').status, 'joined');
  assert.equal(meet.join(m, 'b').status, 'waitlisted');
  assert.equal(meet.join(m, 'c').status, 'waitlisted');
  const r = meet.cancel(m, 'a');
  assert.equal(r.promoted, 'b');
  assert.equal(meet.activeCount(m), 2);
  assert.equal(m.waitlist[0], 'c');
});
t('함께 치기: 중복 참가·차단 사용자·마감 모임은 거절', () => {
  const m = meet.createMeetup({ capacity: 4, creatorId: 'h' });
  assert.equal(meet.join(m, 'a').ok, true);
  assert.equal(meet.join(m, 'a').reason, 'duplicate');
  assert.equal(meet.join(m, 'x', ['h']).reason, 'blocked');
  meet.setClosed(m, 'h', true);
  assert.equal(meet.join(m, 'b').reason, 'closed');
  assert.equal(meet.setClosed(m, 'a', false).reason, 'forbidden');
});
t('함께 치기: 같은 사람의 중복 신고는 한 번, 3명이면 검토 대기', () => {
  const m = meet.createMeetup({ capacity: 4, creatorId: 'h' });
  meet.report(m, 'a', '욕설'); meet.report(m, 'a', '욕설');
  assert.equal(m.reports.length, 1);
  meet.report(m, 'b', '노쇼');
  assert.equal(meet.report(m, 'c', '노쇼').needsReview, true);
  assert.equal(meet.report(m, 'd', 'x'.repeat(201)).reason, 'invalid');
});
t('함께 치기: 확정 시 참가자 전원이 confirmed 로 바뀐다', () => {
  const m = meet.createMeetup({ capacity: 4, creatorId: 'h' });
  meet.join(m, 'a'); meet.confirmAll(m, 'h');
  assert.ok(m.participants.every(p => p.status === 'confirmed'));
});

t('점수: 잘못된 타수·홀·선수는 거절, 모든 수정은 이력에 남는다', () => {
  const g = score.createGame({ holes: 9, players: [{ id: 'p1', name: '가' }], creatorId: 'o' });
  assert.equal(score.setScore(g, 'o', 'p1', 1, 0).reason, 'invalid_strokes');
  assert.equal(score.setScore(g, 'o', 'p1', 10, 3).reason, 'invalid_hole');
  assert.equal(score.setScore(g, 'o', 'zz', 1, 3).reason, 'unknown_player');
  score.setScore(g, 'o', 'p1', 1, 4); score.setScore(g, 'o', 'p1', 1, 3, '정정');
  assert.equal(g.history.length, 2);
  assert.deepEqual([g.history[1].from, g.history[1].to], [4, 3]);
});
t('점수: 일시 중단·재개는 생성자만 가능', () => {
  const g = score.createGame({ holes: 9, players: [], creatorId: 'o' });
  assert.equal(score.pause(g, 'x').ok, false);
  assert.equal(score.pause(g, 'o').ok, true);
  assert.equal(score.resume(g, 'o').ok, true);
});
t('점수: 결과는 총타수 → 뒤 9홀 → 마지막 홀 순, 같으면 공동 순위', () => {
  const g = score.createGame({ holes: 9, players: [{ id: 'a', name: 'A' }, { id: 'b', name: 'B' }, { id: 'c', name: 'C' }], creatorId: 'o' });
  for (let h = 1; h <= 9; h++) { score.setScore(g, 'o', 'a', h, 4); score.setScore(g, 'o', 'b', h, 4); score.setScore(g, 'o', 'c', h, 5); }
  const s = score.standings(g);
  assert.equal(s.complete, true);
  assert.equal(s.rows[0].rank, 1); assert.equal(s.rows[1].rank, 1);
  assert.equal(s.rows[2].rank, 3);
});
t('점수: 미완료 경기는 결과 확정 불가, 확정 후 수정은 운영자 승인 필요', () => {
  const g = score.createGame({ holes: 9, players: [{ id: 'a', name: 'A' }], creatorId: 'o' });
  assert.equal(score.confirmResult(g, 'o').reason, 'incomplete');
  for (let h = 1; h <= 9; h++) score.setScore(g, 'o', 'a', h, 3);
  assert.equal(score.confirmResult(g, 'x').reason, 'forbidden');
  assert.equal(score.confirmResult(g, 'o').ok, true);
  assert.equal(score.setScore(g, 'o', 'a', 1, 5).reason, 'final');
  assert.equal(score.editAfterFinal(g, 'member', 'a', 1, 5, 'o').reason, 'approval_required');
  assert.equal(score.editAfterFinal(g, 'manager', 'a', 1, 5, null).reason, 'approval_required');
  assert.equal(score.editAfterFinal(g, 'manager', 'a', 1, 5, 'o').ok, true);
  assert.equal(g.status, 'final');
  assert.equal(g.final[0].total, 27 + 2);
});

t('Club Pro: 회비 미납자 계산, 월별 장부, CSV 이스케이프', () => {
  const d = pro.duesStatus([{ id: 'd1', title: '5월 회비', amount: 10000 }],
    [{ userId: 'a', duesId: 'd1', amount: 10000 }], [{ userId: 'a' }, { userId: 'b' }]);
  assert.deepEqual(d[0].unpaid, ['b']);
  assert.equal(d[0].collected, 10000);
  const l = pro.ledgerMonthly([{ date: '2026-05-01', kind: 'income', amount: 5 }, { date: '2026-05-09', kind: 'expense', amount: 2 }]);
  assert.deepEqual(l, [{ month: '2026-05', income: 5, expense: 2, net: 3 }]);
  assert.match(pro.duesCsv([{ title: '회비"x', expected: 1, collected: 0, unpaid: [] }]), /"회비""x"/);
});
t('Club Pro: 개인 평균·코스 순위·월 활동 집계', () => {
  const games = [{ date: '2026-05-01', course: 'A', players: [{ userId: 'u', total: 30 }] },
    { date: '2026-05-08', course: 'B', players: [{ userId: 'u', total: 28 }] }];
  assert.equal(pro.playerStats(games)[0].average, 29);
  assert.equal(pro.courseRanking(games)[0].course, 'B');
  assert.deepEqual(pro.monthlyActivity([{ status: 'held', date: '2026-05-02' }, { status: 'open', date: '2026-05-03' }]), [{ month: '2026-05', held: 1 }]);
});
t('Club Pro: 무료 플랜은 유료 기능을 쓸 수 없다', () => {
  assert.equal(pro.canUse('free', 'monthly_report'), false);
  assert.equal(pro.canUse('club_pro', 'monthly_report'), true);
  assert.equal(pro.canUse('free', 'join_meetup'), true);
});
console.log(`\n${n} passed`);
