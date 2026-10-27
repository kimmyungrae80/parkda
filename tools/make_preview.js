// 미리보기 빌드: index.html 복사본에서 운영 연결 정보를 제거한다.
// 사용법: node tools/make_preview.js  → preview/ 폴더 생성
// - Supabase URL·키 제거, Supabase 호출 전면 비활성화 (운영 DB 연결 없음)
// - 관리자 비밀번호 제거 (관리자 로그인 불가). 유튜브·카카오 REST 키는 브라우저 코드에 없음 (서버 환경변수)
// - api/ (서버 함수)와 data/ (검증된 구장·대회 자료)를 함께 복사
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'preview');
fs.mkdirSync(out, { recursive: true });

let html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const rules = [
  [/const SB_URL = '[^']*';/, "const SB_URL = '';"],
  [/const KAKAO_KEY = '[^']*';/, "const KAKAO_KEY = ''; // 미리보기: 카카오 로그인 키 제거"],
  [/const SB_KEY = '[^']*';/, "const SB_KEY = '';"],
  [/const SB_OK  = \(\) => !new URLSearchParams\(location\.search\)\.has\('local'\);[^\n]*/, "const SB_OK  = () => false; // 미리보기: 운영 DB 연결 없음"],
  [/const ADMIN_PW = '[^']*';/, "const ADMIN_PW = null; // 미리보기: 관리자 로그인 불가"],
];
for (const [re, rep] of rules) {
  if (!re.test(html)) throw new Error('규칙 불일치: ' + re);
  html = html.replace(re, () => rep);
}
// 실제 키 값이 남아 있으면 빌드 실패
const leftovers = [/eyJhbGciOi/, /AIza[0-9A-Za-z_-]{20,}/, /szoxnkarkdxirbyxmzgr/, /PARKDA2024/, /059a7981fef/, /1f61ed2143bb/, /eabfd4e97064/];
for (const re of leftovers) if (re.test(html)) throw new Error('미리보기에 운영 값이 남아 있음: ' + re);

fs.writeFileSync(path.join(out, 'index.html'), html, 'utf8');
for (const f of ['sw.js', 'manifest.json', 'icon-192.png', 'icon-512.png']) {
  fs.copyFileSync(path.join(root, f), path.join(out, f));
}
for (const dir of ['api', 'data']) {
  fs.rmSync(path.join(out, dir), { recursive: true, force: true });
  fs.cpSync(path.join(root, dir), path.join(out, dir), { recursive: true });
}
console.log('preview 생성 완료:', out);
