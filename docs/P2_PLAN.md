# P2 구현 순서: 구장·대회·영상·맛집 연동

전제: P1 완료 (홈·공개 페이지 39/39 통과). 운영 DB·main·배포는 승인 전까지 변경하지 않는다.

## 승인이 필요한 항목 (먼저 결정)
1. 구장 데이터 출처: 공공데이터(파크골프장 현황) 사용 여부 — API 키 발급과 이용 약관 확인 필요
2. 카카오 로컬 API 사용량: 현재 JS 키 기반 검색을 서버 측 REST 호출로 옮길지 (REST 키 재발급 후)
3. 유튜브 API: 서버 프록시 도입 여부와 쿼터 예산
4. 운영 DB 스키마 적용 시점과 백업 절차

## 단계

**P2-1. 데이터 모델 설계 (SQL 파일만 작성, 적용하지 않음)**
- `supabase/migrations/0010_venues.sql`: venues(id, name, region, address, lat, lng, phone, source, source_url, status[draft|approved], updated_at)
- `0011_tournaments.sql`: tournaments(id, title, region, venue_id, date_start, date_end, apply_url, source_url, status, updated_at)
- `0012_videos.sql`: videos(id, youtube_id, category, title, channel, published_at, status)
- RLS: 공개 읽기는 status='approved' 행과 공개 컬럼만. 쓰기는 서버 역할(관리자 인증 후)만.

**P2-2. 수집·검수 파이프라인 (서버 측 스크립트, 저장소에 키 없음)**
- 공공데이터·카카오 로컬 결과를 정규화 → 이름·좌표 기준 중복 제거 → `status=draft`로만 저장
- 관리자가 검수 후 approved 전환. 출처 URL 필수.

**P2-3. 구장 목록·상세 (클라이언트)**
- 지역 필터, 페이지네이션(20개 단위), 상세 화면(주소·전화·지도 링크·출처)
- 로컬 샘플 데이터로 먼저 테스트 (테스트용 가상 구장만 사용)

**P2-4. 대회 정보**
- 승인된 대회만 표시, 일정·장소·접수 링크·출처 표시
- 기존 외부 검색 링크는 "직접 찾기" 보조 메뉴로 유지

**P2-5. 유튜브**
- 서버 프록시로 키 숨기기, 응답 캐시 TTL 6시간, 쿼터 초과 시 안내 문구
- 현재 클라이언트 키는 P2-5 완료 전에 제한 설정(도메인·API 제한)을 먼저 적용

**P2-6. 맛집**
- 구장 좌표 기준 카카오 카테고리 검색 (현재 JS SDK 방식 유지), 결과는 서버 캐시 24시간

**P2-7. 테스트**
- 각 단계마다 P1 방식 브라우저 테스트 추가 (스텁 사용), 회귀 테스트 유지
- 개인정보 없는 가상 데이터로만 테스트

## 완료 기준
- 모든 기존 테스트 통과, 새 테스트 추가
- main 미변경, 운영 DB 미변경
- 승인 항목 4개에 대한 결정 기록
