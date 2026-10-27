# 동호회·함께 치기: 서버 측 인증·권한 설계 (초안, 미적용)

현재 상태: 데모만 구현됨 (이 기기 localStorage). 운영자 권한은 **브라우저에서 임의로 바뀔 수 있으므로** 운영 데이터로 쓰면 안 된다.
이 문서는 실제 서비스 전환 전에 필요한 서버 측 구조를 정의한다. 실제 적용은 인증 설계 승인 후에 한다.

## 1. 신원 (인증)
- Supabase Auth (이메일 또는 소셜 로그인). 카카오 로그인은 제공자 설정 후 연결.
- 프로필은 `profiles(user_id uuid pk = auth.uid(), display_name text, created_at)` 만 둔다. 전화번호는 저장하지 않는다.
- 전화번호가 꼭 필요한 기능이 생기면 별도 테이블 + 암호화 + 접근 로그를 먼저 설계한다.

## 2. 권한 모델
- `club_members(club_id, user_id, role in ('owner','manager','member'), status in ('pending','approved','left','removed'))`
- 권한 판단은 **항상 DB에서** 한다. 클라이언트가 보낸 역할 값은 무시한다.
- 운영자 승인·공지·정기모임 등록은 `security definer` 함수로만 수행:
  - `approve_member(club uuid, target uuid)`: 호출자가 해당 클럽의 owner/manager 인지 `club_members` 에서 확인한 뒤 상태 변경.
  - `post_notice(club uuid, title text, body text)`: 같은 확인.
- 테이블 직접 UPDATE 정책은 두지 않는다 (RLS 에서 본인 가입 신청 INSERT 만 허용).

## 3. 함께 치기 (모임)
- `meetings(id, creator uuid, venue_id, date, time, capacity 2~4, status in ('open','closed','confirmed','cancelled'), game_code text unique)`
- `meeting_participants(meeting_id, user_id, status in ('joined','confirmed','cancelled'), primary key(meeting_id,user_id))`
- 참가 신청은 `join_meeting(meeting uuid)` 함수가 정원·마감·중복을 원자적으로 검사 (동시 신청 대비 행 잠금).
- 참가자 전화번호는 공개하지 않는다. 필요 시 모임장과의 메시지 기능으로 대체.
- 게임코드는 DB 유니크 제약으로 중복을 막는다 (현재 로컬 중복 검사만 있음 → P1 보고서 9번 항목).

## 4. RLS 원칙
- 모든 테이블에 RLS 활성화. 기본 거부.
- 읽기: 공개 공지·정기모임은 회원만 (클럽 소속 확인), 모임 목록은 공개 필드만.
- 쓰기: 위의 security definer 함수 또는 본인 행 INSERT 만.

## 5. 감사
- `audit_log(id, actor uuid, action text, target text, at timestamptz)` 에 승인·권한 변경·모임 확정을 기록.

## 6. 현재 데모와의 차이 (숨기지 않음)
| 항목 | 데모 (현재) | 서버 설계 |
|---|---|---|
| 운영자 확인 | 표시 이름 일치 (임시) | 로그인 사용자 ID + 클럽 역할 |
| 데이터 | 이 기기 localStorage | Supabase 테이블 + RLS |
| 전화번호 | 저장 안 함 | 저장 안 함 (기본) |
| 감사 기록 | 없음 | audit_log |

## 7. 적용 전 체크리스트
- [ ] Supabase Auth 설정과 프로필 테이블 승인
- [ ] 마이그레이션 SQL 검토 (`supabase/migrations/20261027_clubs_meetings_draft.sql`, 미적용)
- [ ] RLS 정책 테스트 (다른 사용자의 행 읽기·쓰기 거부 확인)
- [ ] 운영 DB 적용 승인
