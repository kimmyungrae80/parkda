// 미리보기 빌드: index.html 복사본에서 운영 연결 정보를 제거한다.
// 사용법: node tools/make_preview.js  → preview/ 폴더 생성
// - Supabase URL·키 제거, Supabase 호출 전면 비활성화 (운영 DB 연결 없음)
// - 유튜브 키·카카오 REST 키 제거, 관리자 비밀번호 제거 (관리자 로그인 불가)
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'preview');
fs.mkdirSync(out, { recursive: true });

let html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const rules = [
  [/const SB_URL = '[^']*';/, "const SB_URL = '';"],
  [/const SB_KEY = '[^']*';/, "const SB_KEY = '';"],
  [/const SB_OK  = \(\) => !new URLSearchParams\(location\.search\)\.has\('local'\);[^\n]*/, "const SB_OK  = () => false; // 미리보기: 운영 DB 연결 없음"],
  [/const KAKAO_REST_KEY = '[^']*';/, "const KAKAO_REST_KEY = '';"],
  [/const YOUTUBE_KEY\s*= '[^']*';/, "const YOUTUBE_KEY    = '';"],
  [/const ADMIN_PW = '[^']*';/, "const ADMIN_PW = null; // 미리보기: 관리자 로그인 불가"],
];
for (const [re, rep] of rules) {
  if (!re.test(html)) throw new Error('규칙 불일치: ' + re);
  html = html.replace(re, () => rep);
}
// 실제 키 값이 남아 있으면 빌드 실패
const leftovers = [/eyJhbGciOi/, /AIza[0-9A-Za-z_-]{20,}/, /szoxnkarkdxirbyxmzgr/, /PARKDA2024/, /059a7981fef/];
for (const re of leftovers) if (re.test(html)) throw new Error('미리보기에 운영 값이 남아 있음: ' + re);

fs.writeFileSync(path.join(out, 'index.html'), html, 'utf8');
for (const f of ['sw.js', 'manifest.json', 'icon-192.png', 'icon-512.png']) {
  fs.copyFileSync(path.join(root, f), path.join(out, f));
}
console.log('preview 생성 완료:', out);
