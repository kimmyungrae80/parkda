# parkda-staging 연결 안내

운영 프로젝트(`szoxnkarkdxirbyxmzgr`)는 이 작업에서 사용하지 않는다. staging 만 사용한다.

## 1. staging 프로젝트 생성 (소유자 작업)
- Supabase 대시보드에서 `parkda-staging` 생성 (리전 ap-northeast-2 권장)
- 이 작업에서는 Claude 가 프로젝트를 만들 권한이 거부되어 생성하지 못했다. 생성 후 아래 값을 준비한다.

## 2. 환경변수 (저장소에 넣지 않음)
| 이름 | 용도 | 어디에 |
|---|---|---|
| `STAGING_SUPABASE_URL` | staging 프로젝트 주소 (`https://xxxx.supabase.co`) | 로컬 셸 또는 Vercel 미리보기 환경변수 |
| `STAGING_SUPABASE_ANON_KEY` | 브라우저용 공개 키 (anon) | 위와 같음 |
| `SUPABASE_SERVICE_ROLE_KEY` | 서버 함수 전용 (절대 브라우저에 노출 금지) | 서버 환경변수만 |
| `TOSS_SECRET_KEY` | 토스페이먼츠 **테스트** 비밀키 (`test_sk_`) | 서버 환경변수만 |
| `KAKAO_REST_KEY` | 카카오 로컬 API (기존) | 서버 환경변수만 |
| `YOUTUBE_API_KEY` | 유튜브 검색 (기존) | 서버 환경변수만 |

## 3. 클라이언트 설정 생성
```bash
PARKDA_ENV=staging STAGING_SUPABASE_URL=https://xxxx.supabase.co STAGING_SUPABASE_ANON_KEY=... node tools/build_client_config.js
```
- 운영 주소를 넣으면 스크립트가 거부한다.
- `config/client.js` 는 커밋하지 않는다 (`.gitignore`).

## 4. 마이그레이션 적용 (staging 에서만)
1. `supabase/staging/0001_platform_schema.sql` 을 staging SQL Editor 에서 실행
2. `tests/sql/rls_staging_tests.sql` 의 케이스를 채운 뒤 실행
3. 카카오 로그인: 카카오 개발자 앱 등록 → Supabase Auth 의 Kakao 공급자 설정 → 리다이렉트 주소 등록

## 5. 환경 분리 검사
- `node tools/check_env.js` : 배포 파일에 운영 주소·실결제 키가 없는지 확인
- `node tests/unit/kakao_auth_test.js`, `node tests/unit/payments_test.js` : 인증·결제 서버 로직 검사

## 6. 아직 실행하지 않은 것
- staging DB 적용과 RLS 검증 (프로젝트 생성 후)
- 카카오 실제 로그인 (앱 등록 후)
- 토스 테스트 결제 실제 호출 (테스트 키 발급 후)
