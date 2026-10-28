// 점수·결과 규칙 (순수 함수). 결과 계산과 확정은 서버 검증을 전제로 한다.
// 점수 수정은 모두 이력에 남고, 확정된 경기는 운영자 승인 없이는 바꿀 수 없다.
function createGame({ holes, players, creatorId }) {
  if (![9, 18].includes(holes)) throw new Error('invalid_holes');
  return { holes, players: players.map(p => ({ id: p.id, name: p.name, scores: {} })), status: 'in_progress',
    history: [], creatorId, approvedEdits: new Set() };
}
function setScore(g, actorId, playerId, hole, strokes, reason = '') {
  if (g.status === 'final') return { ok: false, reason: 'final' };
  if (!Number.isInteger(strokes) || strokes < 1 || strokes > 15) return { ok: false, reason: 'invalid_strokes' };
  if (hole < 1 || hole > g.holes) return { ok: false, reason: 'invalid_hole' };
  const p = g.players.find(x => x.id === playerId);
  if (!p) return { ok: false, reason: 'unknown_player' };
  const from = p.scores[hole] ?? null;
  p.scores[hole] = strokes;
  g.history.push({ actorId, playerId, hole, from, to: strokes, reason, seq: g.history.length + 1 });
  return { ok: true };
}
function pause(g, actorId) { if (actorId !== g.creatorId || g.status !== 'in_progress') return { ok: false }; g.status = 'paused'; return { ok: true }; }
function resume(g, actorId) { if (actorId !== g.creatorId || g.status !== 'paused') return { ok: false }; g.status = 'in_progress'; return { ok: true }; }
function total(p, holes) { let t = 0; for (let h = 1; h <= holes; h++) { if (p.scores[h] == null) return null; t += p.scores[h]; } return t; }
// 결과 계산: 총타수 오름차순. 같으면 뒤 9홀 타수 → 마지막 홀 → 같은 순위(공동).
function standings(g) {
  const rows = g.players.map(p => ({ id: p.id, name: p.name, total: total(p, g.holes),
    back9: g.holes === 18 ? [10, 11, 12, 13, 14, 15, 16, 17, 18].reduce((s, h) => s + (p.scores[h] || 0), 0) : null,
    last: p.scores[g.holes] ?? null }));
  if (rows.some(r => r.total === null)) return { complete: false, rows };
  rows.sort((a, b) => a.total - b.total || (a.back9 ?? 0) - (b.back9 ?? 0) || (a.last ?? 0) - (b.last ?? 0));
  let rank = 0, prev = null;
  rows.forEach((r, i) => {
    const same = prev && r.total === prev.total && r.back9 === prev.back9 && r.last === prev.last;
    r.rank = same ? prev.rank : i + 1; prev = r;
  });
  return { complete: true, rows };
}
function confirmResult(g, actorId) {
  if (actorId !== g.creatorId) return { ok: false, reason: 'forbidden' };
  const s = standings(g);
  if (!s.complete) return { ok: false, reason: 'incomplete' };
  g.status = 'final'; g.final = s.rows.map(r => ({ id: r.id, total: r.total, rank: r.rank }));
  return { ok: true };
}
// 확정 후 수정: 운영자 승인 기록이 있어야 한다
function editAfterFinal(g, actorRole, playerId, hole, strokes, approvedBy) {
  if (g.status !== 'final') return setScore(g, g.creatorId, playerId, hole, strokes, 'edit');
  if (!['owner', 'manager'].includes(actorRole) || !approvedBy) return { ok: false, reason: 'approval_required' };
  g.status = 'in_progress';
  const r = setScore(g, approvedBy, playerId, hole, strokes, 'post_final_edit');
  g.status = 'final';
  if (r.ok) g.final = standings(g).rows.map(x => ({ id: x.id, total: x.total, rank: x.rank }));
  return r;
}
module.exports = { createGame, setScore, pause, resume, standings, confirmResult, editAfterFinal };
