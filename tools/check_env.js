// 환경 분리 검사: 배포·저장소의 실행 파일에 운영 Supabase 참조나 실결제 키가 남아 있으면 실패한다.
// 사용법: node tools/check_env.js  (docs·tools·tests 는 가드 문자열과 테스트 값을 포함하므로 제외)
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
const PROD_REF = 'szoxnkarkdxirbyxmzgr';
const LIVE_KEY = /live_sk_|live_ck_/;
// 배포되는 실행 파일만 검사한다 (도구·테스트·문서는 가드 문자열을 포함하므로 제외)
const targets = ['index.html', 'sw.js', 'manifest.json', 'api', 'config', 'preview'];
const skip = new Set(['config/client.js']);
let bad = [];
function walk(p) {
  const rel = path.relative(root, p);
  if (skip.has(rel)) return;
  const st = fs.statSync(p);
  if (st.isDirectory()) return fs.readdirSync(p).forEach(f => walk(path.join(p, f)));
  if (!/\.(html|js|json|sql|py)$/.test(p)) return;
  const text = fs.readFileSync(p, 'utf8');
  if (text.includes(PROD_REF)) bad.push(`${rel}: 운영 Supabase 참조`);
  if (LIVE_KEY.test(text)) bad.push(`${rel}: 실결제 키 형식`);
}
targets.forEach(t => { const p = path.join(root, t); if (fs.existsSync(p)) walk(p); });
if (bad.length) { console.log('환경 분리 검사 실패:\n  ' + bad.join('\n  ')); process.exit(1); }
console.log('환경 분리 검사 통과: 실행 파일에 운영 참조·실결제 키 없음');
