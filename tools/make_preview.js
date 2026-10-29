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
  [/const KAKAO_KEY = '[^']*';/, "const KAKAO_KEY = ''; // 미리보기: 카카오 로그인 키 제거"],
  [/const SB_OK\s*= \(\) => [^\n]*/, "const SB_OK  = () => false; // 미리보기: 운영 DB 연결 없음"],
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
// 미리보기는 빈 설정 (운영 연결 값 없음)
fs.mkdirSync(path.join(out, 'config'), { recursive: true });
fs.writeFileSync(path.join(out, 'config', 'client.js'), 'window.PARKDA_CONFIG = {"env":"preview","supabaseUrl":"","supabaseAnonKey":""};\n');
for (const f of ['sw.js', 'manifest.json', 'icon-192.png', 'icon-512.png', 'parkda-toss.css']) {
  fs.copyFileSync(path.join(root, f), path.join(out, f));
}
// 화면 규칙 파일 (순수 함수, 비밀값 없음). index.html 이 config/client.js 다음에 불러온다.
fs.rmSync(path.join(out, 'lib'), { recursive: true, force: true });
fs.cpSync(path.join(root, 'lib'), path.join(out, 'lib'), { recursive: true });
fs.rmSync(path.join(out, 'api'), { recursive: true, force: true });
fs.cpSync(path.join(root, 'api'), path.join(out, 'api'), { recursive: true });
// 공개 데이터는 공식 출처 확인분(verified)의 두 파일만 복사한다. raw·processed·내부 후보는 복사하지 않는다.
fs.rmSync(path.join(out, 'data'), { recursive: true, force: true });
fs.mkdirSync(path.join(out, 'data', 'verified'), { recursive: true });
for (const f of ['courses.json', 'tournaments.json']) {
  fs.copyFileSync(path.join(root, 'data', 'verified', f), path.join(out, 'data', 'verified', f));
}
console.log('preview 생성 완료:', out);
