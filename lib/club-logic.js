// 동호회 규칙 (순수 함수). 실제 권한은 서버 함수에서 다시 검증해야 한다 (docs/CLUB_AUTH_DESIGN.md).
// 여기서는 상태 전이와 회원 목록·출석 계산만 한다. 입력 role 은 서버가 확인한 값이라고 가정한다.
const STAFF = ['owner', 'manager', 'treasurer'];
const isStaff = (role) => STAFF.includes(role);

function createClub({ name, region, intro, ownerId }) {
  if (!name || name.length < 2 || name.length > 40) throw new Error('invalid_name');
  return { id: 'c-' + Math.random().toString(36).slice(2, 8), name, region, intro: intro || '',
    members: [{ userId: ownerId, role: 'owner', status: 'approved' }], meetups: [] };
}
function findMember(club, userId) { return club.members.find(m => m.userId === userId); }
function requestJoin(club, userId) {
  const cur = findMember(club, userId);
  if (cur && ['pending', 'approved'].includes(cur.status)) return { ok: false, reason: 'already' };
  if (cur) cur.status = 'pending'; else club.members.push({ userId, role: 'member', status: 'pending' });
  return { ok: true };
}
// actorRole: 서버가 판정한 호출자 역할
function decide(club, actorRole, targetUserId, approve) {
  if (!isStaff(actorRole)) return { ok: false, reason: 'forbidden' };
  const m = findMember(club, targetUserId);
  if (!m || m.status !== 'pending') return { ok: false, reason: 'not_pending' };
  m.status = approve ? 'approved' : 'rejected';
  return { ok: true };
}
function leave(club, userId) {
  const m = findMember(club, userId);
  if (!m || m.status !== 'approved') return { ok: false, reason: 'not_member' };
  if (m.role === 'owner') return { ok: false, reason: 'owner_cannot_leave' };  // 운영자는 권한을 넘긴 뒤 탈퇴
  m.status = 'left';
  return { ok: true };
}
function removeMember(club, actorRole, targetUserId) {
  if (!isStaff(actorRole)) return { ok: false, reason: 'forbidden' };
  const m = findMember(club, targetUserId);
  if (!m || m.status !== 'approved' || m.role === 'owner') return { ok: false, reason: 'cannot_remove' };
  m.status = 'removed';
  return { ok: true };
}
function listMembers(club, viewerRole) {
  // 일반 회원에게는 이름 목록과 역할만 보이고, 상태(대기·탈퇴 등) 세부는 운영자에게만 보인다.
  return club.members.filter(m => viewerRole && (isStaff(viewerRole) || m.status === 'approved'))
    .map(m => ({ userId: m.userId, role: m.role, status: isStaff(viewerRole) ? m.status : 'approved' }));
}
function recordAttendance(meetup, actorRole, attendance) {
  if (!isStaff(actorRole)) return { ok: false, reason: 'forbidden' };
  meetup.attendance = { ...(meetup.attendance || {}), ...attendance };
  return { ok: true };
}
function attendanceRate(meetups, userId) {
  const held = meetups.filter(m => m.attendance && userId in m.attendance);
  if (!held.length) return null;
  return Math.round(100 * held.filter(m => m.attendance[userId]).length / held.length);
}
module.exports = { STAFF, isStaff, findMember, createClub, requestJoin, decide, leave, removeMember, listMembers, recordAttendance, attendanceRate };
