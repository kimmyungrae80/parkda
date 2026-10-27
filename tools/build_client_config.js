// 환경별 클라이언트 설정 생성: config/client.js (저장소에 커밋하지 않음, .gitignore 처리)
// 사용법: PARKDA_ENV=staging STAGING_SUPABASE_URL=... STAGING_SUPABASE_ANON_KEY=... node tools/build_client_config.js
// 값이 없으면 빈 설정을 만든다 → 동기화 꺼짐(이 기기 저장). 운영 값은 이 스크립트에 넣지 않는다.
const fs = require('fs');
const path = require('path');
const env = process.env.PARKDA_ENV || 'local';
if (!['local', 'staging'].includes(env)) { console.error('PARKDA_ENV 는 local 또는 staging 만 허용'); process.exit(1); }
const url = env === 'staging' ? (process.env.STAGING_SUPABASE_URL || '') : '';
const key = env === 'staging' ? (process.env.STAGING_SUPABASE_ANON_KEY || '') : '';
// 운영 프로젝트 참조값이면 거부 (운영 DB 연결 차단)
const PROD_REF = 'szoxnkarkdxirbyxmzgr';
if (url.includes(PROD_REF) || key.includes(PROD_REF)) { console.error('운영 Supabase 주소는 staging 설정에 쓸 수 없습니다.'); process.exit(1); }
if (env === 'staging' && url && !/^https:\/\/[a-z0-9]+\.supabase\.co$/.test(url)) { console.error('STAGING_SUPABASE_URL 형식이 올바르지 않습니다.'); process.exit(1); }
const out = path.resolve(__dirname, '..', 'config', 'client.js');
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, `// 자동 생성 (${env}). 커밋 금지.\nwindow.PARKDA_CONFIG = ${JSON.stringify({ env, supabaseUrl: url, supabaseAnonKey: key })};\n`);
console.log(`config/client.js 생성 (env=${env}, 동기화 ${url ? '사용' : '꺼짐'})`);
