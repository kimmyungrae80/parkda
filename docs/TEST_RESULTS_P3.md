# 테스트 결과 (P3: 전국 구장 데이터 · 검색 · 상세 · 주변 검색)

실행 기준: 2026-10-27, 저장소 루트. 외부 요청은 테스트에서 차단하고 서버 API 는 스텁으로 응답.

| 구분 | 명령 | 결과 |
|---|---|---|
| 데이터 파이프라인 (지역 판별, 병합 규칙, 검증 규칙, 공개 데이터 무결성, 수집 파서) | `python3 tests/unit/test_pipeline.py` | 24/24 |
| 서버 API (YouTube·카카오 음식점·카페·지오코딩, 키 비노출, 할당량·오류 코드) | `node tests/unit/api_test.js` | 25/25 |
| 서버 API 확장 (반경·카테고리·구장명 검색, 입력 검증) | `node tests/unit/api_p3_test.js` | 5/5 |
| 외부 텍스트 이스케이프 헬퍼 | `node tests/unit/helpers_test.js index.html` | 8/8 |
| 서비스워커 (외부·API 응답 캐시 금지) | `node tests/unit/sw_cache_test.js sw.js` | 7/7 |
| 회귀: 경기 생성·조편성·점수·저장·결과·공유 문구·게임코드·기존 데이터 보존 | `python3 tests/e2e/test_regression.py` | 20/20 |
| P1 홈·공개 페이지 (순서, 비회원 접근, 반응형, 접근성 이름, 기존 게임 링크, ?local=1) | `python3 tests/e2e/test_p1_home.py` | 41/41 |
| P2 공개 정보 (오류 상태 안내, 외부 API 직접 호출 없음) | `python3 tests/e2e/test_p2_public.py` | 8/8 |
| P3 구장 검색·지역 필터·지도 대체 안내·즐겨찾기·상세 페이지·정보 확인 중·출처 표기·주변 검색 조건·좌표 없는 구장·관련 대회·관련 영상·대회 페이지·외부 직접 호출 없음·반응형 | `python3 tests/e2e/test_p3_courses.py` | 20/20 |

미리보기 빌드(`preview/`)에 대해서도 P1·P3 를 실행해 같은 결과를 확인했다 (`PARKDA_SERVE_DIR=preview`).

## 실행하지 않았거나 확인되지 않은 항목 (성공으로 표시하지 않음)
- 실제 카카오 음식점·카페 응답: 서버 키가 아직 설정되지 않아 스텁만 사용.
- 실제 유튜브 응답: 서버 키 미설정. 스텁만 사용.
- 지도 화면(Leaflet + OpenStreetMap 타일): 테스트에서는 외부 라이브러리가 차단되어 대체 문구만 확인.
- 실제 기기(iOS Safari, Android Chrome) 테스트.
- 좌표 정확도: 자동 지오코딩 47곳은 주소 기반이며 실제 위치와 차이가 있을 수 있음 (화면에 표시).
- 운영 Supabase 데이터베이스 (접근·변경하지 않음). 마이그레이션 SQL 은 작성만 했고 적용하지 않음.
