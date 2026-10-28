// Club Pro 집계 (순수 함수). 회비 장부는 운영자가 입력하는 기록이며 실제 금융거래가 아니다.
function duesStatus(dues, payments, members) {
  // dues: [{id, amount}], payments: [{userId, duesId, amount}], members: [{userId}]
  return dues.map(d => {
    const paid = new Map();
    payments.filter(p => p.duesId === d.id).forEach(p => paid.set(p.userId, (paid.get(p.userId) || 0) + p.amount));
    const unpaid = members.filter(m => (paid.get(m.userId) || 0) < d.amount).map(m => m.userId);
    return { duesId: d.id, title: d.title, expected: d.amount * members.length, collected: [...paid.values()].reduce((a, b) => a + b, 0), unpaid };
  });
}
function ledgerMonthly(tx) {
  const out = {};
  tx.forEach(t => {
    const key = t.date.slice(0, 7);
    out[key] = out[key] || { income: 0, expense: 0 };
    out[key][t.kind] += t.amount;
  });
  return Object.entries(out).sort().map(([month, v]) => ({ month, ...v, net: v.income - v.expense }));
}
function playerStats(games) {
  // games: [{date, course, players:[{userId,total}]}]
  const acc = {};
  games.forEach(g => g.players.forEach(p => {
    const a = acc[p.userId] = acc[p.userId] || { games: 0, sum: 0, recent: [] };
    a.games += 1; a.sum += p.total; a.recent.push({ date: g.date, course: g.course, total: p.total });
  }));
  return Object.entries(acc).map(([userId, a]) => ({ userId, games: a.games, average: +(a.sum / a.games).toFixed(1),
    recent: a.recent.sort((x, y) => (x.date < y.date ? 1 : -1)).slice(0, 5) }));
}
function courseRanking(games) {
  const by = {};
  games.forEach(g => { by[g.course] = by[g.course] || { games: 0, sum: 0 };
    g.players.forEach(p => { by[g.course].games += 1; by[g.course].sum += p.total; }); });
  return Object.entries(by).map(([course, v]) => ({ course, average: +(v.sum / v.games).toFixed(1), games: v.games }))
    .sort((a, b) => a.average - b.average);
}
function monthlyActivity(meetups) {
  const out = {};
  meetups.filter(m => m.status === 'held').forEach(m => { const k = m.date.slice(0, 7); out[k] = (out[k] || 0) + 1; });
  return Object.entries(out).sort().map(([month, held]) => ({ month, held }));
}
function duesCsv(rows) {
  const head = '항목,예정금액,수납금액,미납자수';
  const lines = rows.map(r => [r.title, r.expected, r.collected, r.unpaid.length].map(v => `"${String(v).replace(/"/g, '""')}"`).join(','));
  return [head, ...lines].join('\n');
}
const PRO_FEATURES = ['regular_meetup_auto', 'advanced_members', 'attendance_dues_stats', 'monthly_report', 'export', 'advanced_game_stats'];
const FREE_FEATURES = ['basic_club', 'join_meetup', 'basic_game'];
function canUse(plan, feature) { return plan === 'club_pro' ? [...PRO_FEATURES, ...FREE_FEATURES].includes(feature) : FREE_FEATURES.includes(feature); }
const PD_PRO = { duesStatus, ledgerMonthly, playerStats, courseRanking, monthlyActivity, duesCsv, canUse, PRO_FEATURES, FREE_FEATURES };
if (typeof module !== 'undefined' && module.exports) module.exports = PD_PRO;
else window.PD_PRO = PD_PRO;
