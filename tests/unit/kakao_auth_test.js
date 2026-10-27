// 사용법: node tests/unit/kakao_auth_test.js  (실제 로그인 없음)
const path = require('path');
let pass = 0, fail = 0;
const check = (n, c) => { c ? pass++ : fail++; console.log((c ? 'PASS ' : 'FAIL ') + n); };
const g = globalThis;
g.PARKDA_CONFIG = { supabaseUrl: '', supabaseAnonKey: '' };
const auth = require(path.join(__dirname, '../../auth/kakao-auth.js'));
check('설정 없으면 로그인 시작 안 함 (동기화 꺼짐)', auth.ready === false && auth.startKakaoLogin('https://x/').reason === 'not_configured');
const url = auth.buildAuthorizeUrl('https://abcdefgh.supabase.co', 'https://preview.example/app');
check('카카오 공급자로 Supabase 인증 주소 생성', url.startsWith('https://abcdefgh.supabase.co/auth/v1/authorize') && url.includes('provider=kakao'));
check('리다이렉트 주소 포함', url.includes('redirect_to=' + encodeURIComponent('https://preview.example/app')));
let threw = false; try { auth.buildAuthorizeUrl('http://evil.example', 'x'); } catch (e) { threw = true; }
check('https·supabase.co 형식이 아니면 거부', threw);
check('토큰·키를 주소에 넣지 않음', !url.includes('apikey') && !url.includes('anon'));
console.log(`\nkakao auth tests: PASS ${pass} / FAIL ${fail}`);
process.exit(fail ? 1 : 0);
