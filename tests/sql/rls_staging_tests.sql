-- staging 전용 RLS 검증 (parkda-staging 에서만 실행). 운영 프로젝트에서 실행 금지.
-- 실행 후 각 행이 'PASS' 인지 확인한다. 실패 시 해당 정책을 수정하고 다시 실행.
-- 전제: 테스트 사용자 3명 (owner, member, outsider) 과 동호회 1개가 미리 만들어져 있어야 한다.
begin;
select set_config('request.jwt.claims', json_build_object('sub', :'owner_id', 'role', 'authenticated')::text, true);
select 'owner can read own club' as case_name,
       case when exists (select 1 from public.clubs) then 'PASS' else 'FAIL' end as result;
-- 같은 방식으로 다음 케이스를 추가한다 (승인 전 회원은 공지 열람 불가, 일반 회원은 승인 불가,
-- 외부인은 회원 목록 열람 불가, 참가 신청은 정원 초과 시 실패, 결제 상태는 클라이언트가 바꿀 수 없음,
-- admin_audit_logs 는 클라이언트 읽기 불가).
rollback;
