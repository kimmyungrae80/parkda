-- =====================================================================
-- DRAFT — 실행 금지 (DO NOT RUN)
-- 대상: 운영 Supabase 프로젝트 szoxnkarkdxirbyxmzgr (현재 접근 불가)
-- 승인 조건: (1) 1단계 분류 결과 확정 (2) 백업 파일 생성·검증 (3) 복구 리허설 통과 (4) 소유자 서면 승인
-- 이 파일은 docs/TEST_DATA_CLEANUP_PLAN.md 의 절차를 SQL로 옮긴 초안이다.
-- =====================================================================

-- [1단계] 읽기 전용 분류 (실행 가능하지만 소유자가 직접 실행하고 결과의 건수·키 접두사만 공유)
select split_part(key, '_', 1) as key_prefix, count(*) as rows
from public.parkda_store
group by 1
order by 2 desc;

-- 테스트 데이터 후보: 표시 이름·메모에 테스트 표식이 있는 경기 (표식 규칙은 소유자 확정 후 채울 것)
-- select key, length(value::text) from public.parkda_store where key like 'match_%' and value::text ilike '%테스트%';

-- [2단계] 백업 (삭제 전 필수). 행 전체를 JSON으로 저장해 두고 복구 가능성을 확인한다.
-- create table public.parkda_store_backup_20261028 as select * from public.parkda_store;
-- 위 백업 테이블은 같은 프로젝트 안에 두지 않는 것을 권장한다 (스냅샷 또는 CSV 내보내기 사용).

-- [3단계] 삭제 대상 확정 후에만 사용. 키 목록은 1단계 결과로 명시적으로 나열한다 (패턴 삭제 금지).
-- begin;
--   delete from public.parkda_store where key in ('<확정된 키 1>', '<확정된 키 2>');
--   -- 삭제 건수가 목록 길이와 같은지 확인한 뒤에만 commit
-- commit;  -- 건수 불일치 시 rollback;

-- [4단계] 복구 (백업 테이블에서 되돌리기)
-- insert into public.parkda_store select * from public.parkda_store_backup_20261028
--   where key in ('<복구할 키>') on conflict (key) do update set value = excluded.value;
