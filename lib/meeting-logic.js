// 함께 치기 규칙 (순수 함수): 정원, 대기자, 취소 시 승격, 신고·차단.
function createMeetup({ capacity, creatorId }) {
  if (!(capacity >= 2 && capacity <= 4)) throw new Error('invalid_capacity');
  return { capacity, creatorId, status: 'open', participants: [{ userId: creatorId, status: 'joined' }], waitlist: [], reports: [] };
}
function activeCount(m) { return m.participants.filter(p => p.status === 'joined' || p.status === 'confirmed').length; }
function join(m, userId, blocks = []) {
  if (m.status !== 'open') return { ok: false, reason: 'closed' };
  if (m.participants.some(p => p.userId === userId && p.status !== 'cancelled')) return { ok: false, reason: 'duplicate' };
  if (m.waitlist.includes(userId)) return { ok: false, reason: 'duplicate' };
  if (blocks.includes(m.creatorId)) return { ok: false, reason: 'blocked' };
  if (activeCount(m) >= m.capacity) { m.waitlist.push(userId); return { ok: true, status: 'waitlisted' }; }
  m.participants.push({ userId, status: 'joined' });
  return { ok: true, status: 'joined' };
}
// 취소하면 대기 1번이 자동으로 참가로 승격된다 (정원은 항상 트랜잭션 안에서 계산)
function cancel(m, userId) {
  const p = m.participants.find(x => x.userId === userId && x.status !== 'cancelled');
  if (!p) return { ok: false, reason: 'not_joined' };
  p.status = 'cancelled';
  const next = m.waitlist.shift();
  if (next) m.participants.push({ userId: next, status: 'joined', promoted: true });
  return { ok: true, promoted: next || null };
}
// 대기자가 대기를 취소한다 (참가자가 아니므로 승격 없음)
function cancelWait(m, userId) {
  const i = m.waitlist.indexOf(userId);
  if (i < 0) return { ok: false, reason: 'not_waiting' };
  m.waitlist.splice(i, 1);
  return { ok: true };
}
function setClosed(m, actorId, closed) {
  if (actorId !== m.creatorId) return { ok: false, reason: 'forbidden' };
  m.status = closed ? 'closed' : 'open';
  return { ok: true };
}
function confirmAll(m, actorId) {
  if (actorId !== m.creatorId) return { ok: false, reason: 'forbidden' };
  m.participants.forEach(p => { if (p.status === 'joined') p.status = 'confirmed'; });
  m.status = 'confirmed';
  return { ok: true };
}
// 신고: 같은 신고자가 같은 대상을 여러 번 신고해도 한 번으로 센다. 3명 이상이 신고하면 검토 대기로 표시.
function report(m, reporterId, reason) {
  if (!reason || reason.length > 200) return { ok: false, reason: 'invalid' };
  if (!m.reports.some(r => r.reporterId === reporterId)) m.reports.push({ reporterId, reason, at: 'now' });
  return { ok: true, needsReview: m.reports.length >= 3 };
}
// 차단: 차단한 사람에게는 그 사람의 모임이 보이지 않는다
// 차단한 사람이 만든 모임은 목록에서 숨긴다
function visibleTo(meetups, blocks) {
  return meetups.filter(m => !blocks.includes(m.creatorId));
}
const PD_MEET = { createMeetup, join, cancel, cancelWait, setClosed, confirmAll, report, visibleTo, activeCount };
if (typeof module !== 'undefined' && module.exports) module.exports = PD_MEET;
else window.PD_MEET = PD_MEET;
