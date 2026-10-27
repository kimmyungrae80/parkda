# 테스트 결과 (feature/parkda-2)

실행 날짜: 2026-10-27 · 명령은 저장소 루트에서 실행.

| 구분 | 명령 | 결과 |
|---|---|---|
| JavaScript 문법 (인라인 스크립트 2개) | `node -e` `new Function` 파싱 | 통과 |
| 헬퍼 단위 (escHtml·safeUrl·safeId) | `node tests/unit/helpers_test.js index.html` | 8/8 |
| 서비스워커 캐싱 규칙 | `node tests/unit/sw_cache_test.js sw.js` | 6/6 |
| 회귀: 경기 생성·조편성·점수·저장·결과·공유 텍스트·게임코드·기존 데이터 보존 | `python3 tests/e2e/test_regression.py` | 20/20 |
| P1: 메인 순서·비회원 구장/대회/영상/맛집·회원 전용 로그인·반응형 4종·접근성 이름·기존 게임 링크·?local=1 Supabase 0건·서비스워커 캐시 외부 URL 0건·외부 뉴스 프록시 0건 | `python3 tests/e2e/test_p1_home.py` | 39/39 |

## 실행 환경
- 브라우저: 시스템 Chrome (Playwright 1.x, Python, `channel="chrome"`)
- 외부 요청: 로컬 파일 외 모두 차단. 카카오 SDK·유튜브·뉴스는 테스트 스텁으로 응답. Supabase는 항상 차단.
- 테스트 데이터: `tests/fixtures/fictional_match.json` (가상 이름만 사용)

## 결과 파일
- `tests/results/regression_latest.txt`
- `tests/results/p1_home_latest.txt`
- 스크린샷: `tests/results/p1_home_390.png`, `p1_home_1280.png`, `login_390.png`, `login_1280.png`

## 아직 검증하지 않은 것 (통과로 보고하지 않음)
- 실제 카카오·유튜브 응답 (스텁만 사용)
- 명암비 측정, axe 등 자동 접근성 도구, 스크린리더 실사용
- 실제 기기(iOS Safari·Android Chrome) 테스트
- 운영 Supabase RLS (접근 권한 없음)
- 태블릿(768px) 시각 검토
