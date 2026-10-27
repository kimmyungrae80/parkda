-- PARKDA P0 점검용 READ-ONLY 쿼리. 데이터 변경 없음. 개인 값은 조회하지 않음(건수·키 접두사만).
-- 실행 위치: Supabase 대시보드 > SQL Editor (프로젝트 szoxnkarkdxirbyxmzgr)

-- 1) RLS 활성 여부
select c.relname, c.relrowsecurity as rls_enabled, c.relforcerowsecurity as rls_forced
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relname = 'parkda_store';

-- 2) 정책 목록 (anon/authenticated 가 쓰기 가능한지 확인)
select policyname, cmd, roles, qual, with_check
from pg_policies
where schemaname = 'public' and tablename = 'parkda_store';

-- 3) 테이블 권한 (anon 에 INSERT/UPDATE/DELETE 가 있으면 위험)
select grantee, privilege_type
from information_schema.role_table_grants
where table_schema = 'public' and table_name = 'parkda_store'
order by grantee, privilege_type;

-- 4) 규모와 키 접두사 분포 (값은 조회하지 않음)
select split_part(key, '_', 1) as key_prefix, count(*) as rows
from parkda_store
group by 1 order by 2 desc;

-- 5) 보안 어드바이저는 대시보드 Advisors > Security 에서 확인
