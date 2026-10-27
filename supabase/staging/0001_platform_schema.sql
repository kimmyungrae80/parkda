-- PARKDA 2.0 staging 스키마 (parkda-staging 전용). 운영 프로젝트에 적용 금지.
-- 원칙: 모든 테이블 RLS 활성 + 기본 거부. 권한은 DB 함수(is_club_member 등)에서 판단. 전화번호 미저장.

create table if not exists public.profiles (
  user_id      uuid primary key references auth.users(id) on delete cascade,
  display_name text not null check (char_length(display_name) between 1 and 20),
  kakao_linked boolean not null default false,
  created_at   timestamptz not null default now()
);

create table if not exists public.clubs (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(name) between 2 and 40),
  region text not null,
  intro text,
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now()
);

create table if not exists public.club_members (
  club_id uuid not null references public.clubs(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'member' check (role in ('owner','manager','treasurer','member')),
  status text not null default 'pending' check (status in ('pending','approved','rejected','left','removed')),
  joined_at timestamptz not null default now(),
  primary key (club_id, user_id)
);

create table if not exists public.club_notices (
  id uuid primary key default gen_random_uuid(),
  club_id uuid not null references public.clubs(id) on delete cascade,
  title text not null, body text,
  posted_by uuid not null references auth.users(id),
  created_at timestamptz not null default now()
);

create table if not exists public.meetups (
  id uuid primary key default gen_random_uuid(),
  club_id uuid references public.clubs(id) on delete cascade,      -- null 이면 일반 함께 치기
  creator uuid not null references auth.users(id),
  venue_id text not null,
  meet_date date not null,
  meet_time text,
  capacity integer not null check (capacity between 2 and 4),
  status text not null default 'open' check (status in ('open','closed','confirmed','cancelled')),
  game_code text unique,
  created_at timestamptz not null default now()
);

create table if not exists public.meetup_participants (
  meetup_id uuid not null references public.meetups(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  status text not null default 'joined' check (status in ('joined','waitlisted','confirmed','cancelled')),
  attended boolean,
  primary key (meetup_id, user_id)
);

create table if not exists public.games (
  id uuid primary key default gen_random_uuid(),
  meetup_id uuid references public.meetups(id) on delete set null,
  club_id uuid references public.clubs(id) on delete cascade,
  game_code text unique,
  status text not null default 'in_progress' check (status in ('in_progress','paused','final')),
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now()
);

create table if not exists public.game_scores (
  game_id uuid not null references public.games(id) on delete cascade,
  player_id uuid not null references auth.users(id),
  hole smallint not null check (hole between 1 and 36),
  strokes smallint not null check (strokes between 1 and 15),
  primary key (game_id, player_id, hole)
);

create table if not exists public.score_audit_logs (
  id bigint generated always as identity primary key,
  game_id uuid not null references public.games(id) on delete cascade,
  actor uuid not null references auth.users(id),
  action text not null, detail jsonb, at timestamptz not null default now()
);

create table if not exists public.club_dues (
  id uuid primary key default gen_random_uuid(),
  club_id uuid not null references public.clubs(id) on delete cascade,
  item text not null, amount integer not null check (amount >= 0), period text not null
);

create table if not exists public.club_transactions (
  id uuid primary key default gen_random_uuid(),
  club_id uuid not null references public.clubs(id) on delete cascade,
  kind text not null check (kind in ('income','expense')),
  amount integer not null check (amount >= 0), memo text, recorded_by uuid not null references auth.users(id),
  occurred_on date not null default current_date
);

create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  club_id uuid not null references public.clubs(id) on delete cascade,
  plan text not null check (plan in ('free','club_pro')),
  status text not null check (status in ('active','canceled','past_due','test')),
  current_period_end date, created_at timestamptz not null default now()
);

create table if not exists public.payments (
  order_id text primary key,                 -- 중복 결제 방지: 주문번호 유일
  club_id uuid not null references public.clubs(id) on delete cascade,
  amount integer not null check (amount > 0),
  status text not null check (status in ('requested','done','failed','canceled','refund_pending','refunded')),
  provider_payment_key text unique,
  mode text not null default 'test' check (mode in ('test')),   -- 실결제 모드는 스키마에서 허용하지 않음
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);

create table if not exists public.reports (
  id uuid primary key default gen_random_uuid(),
  reporter uuid not null references auth.users(id),
  target_type text not null check (target_type in ('meetup','club','user','notice')),
  target_id text not null, reason text not null, status text not null default 'open' check (status in ('open','resolved','dismissed')),
  created_at timestamptz not null default now()
);

create table if not exists public.admin_audit_logs (
  id bigint generated always as identity primary key,
  actor uuid not null references auth.users(id), action text not null, target text, at timestamptz not null default now()
);

-- ── 권한 판단 함수 (security definer: 호출자 본인 기준으로만 확인) ──
create or replace function public.club_role(p_club uuid) returns text
language sql stable security definer set search_path = public as $$
  select role from public.club_members
  where club_id = p_club and user_id = auth.uid() and status = 'approved';
$$;

create or replace function public.is_club_staff(p_club uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((select role in ('owner','manager','treasurer') from public.club_members
    where club_id = p_club and user_id = auth.uid() and status = 'approved'), false);
$$;

create or replace function public.is_club_member(p_club uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists(select 1 from public.club_members where club_id = p_club and user_id = auth.uid() and status = 'approved');
$$;

-- ── RLS ──
alter table public.profiles enable row level security;
alter table public.clubs enable row level security;
alter table public.club_members enable row level security;
alter table public.club_notices enable row level security;
alter table public.meetups enable row level security;
alter table public.meetup_participants enable row level security;
alter table public.games enable row level security;
alter table public.game_scores enable row level security;
alter table public.score_audit_logs enable row level security;
alter table public.club_dues enable row level security;
alter table public.club_transactions enable row level security;
alter table public.subscriptions enable row level security;
alter table public.payments enable row level security;
alter table public.reports enable row level security;
alter table public.admin_audit_logs enable row level security;

-- profiles: 본인만 읽기·수정
create policy profiles_self_read on public.profiles for select to authenticated using (user_id = auth.uid());
create policy profiles_self_write on public.profiles for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

-- clubs: 로그인 사용자는 공개 정보 읽기, 생성은 본인 명의, 수정은 운영자
create policy clubs_read on public.clubs for select to authenticated using (true);
create policy clubs_insert_self on public.clubs for insert to authenticated with check (created_by = auth.uid());
create policy clubs_update_staff on public.clubs for update to authenticated using (public.is_club_staff(id)) with check (public.is_club_staff(id));

-- club_members: 본인 신청 행만 생성, 읽기는 본인 행 또는 같은 동호회 회원, 승인·역할 변경은 DB 함수로만(직접 UPDATE 불가)
create policy club_members_read on public.club_members for select to authenticated
  using (user_id = auth.uid() or public.is_club_member(club_id));
create policy club_members_request on public.club_members for insert to authenticated
  with check (user_id = auth.uid() and status = 'pending' and role = 'member');
create policy club_members_leave on public.club_members for update to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid() and status = 'left');

-- notices: 회원만 읽기, 운영자만 작성
create policy notices_read on public.club_notices for select to authenticated using (public.is_club_member(club_id));
create policy notices_write_staff on public.club_notices for insert to authenticated
  with check (posted_by = auth.uid() and public.is_club_staff(club_id));

-- meetups: 공개 모임은 로그인 사용자 읽기(개인정보 없음), 동호회 모임은 회원만. 생성은 본인 명의 + (동호회면 운영자)
create policy meetups_read on public.meetups for select to authenticated
  using (club_id is null or public.is_club_member(club_id));
create policy meetups_create on public.meetups for insert to authenticated
  with check (creator = auth.uid() and (club_id is null or public.is_club_staff(club_id)));

-- participants: 본인 신청만. 정원·중복은 join_meetup 함수에서 원자적으로 검사 (직접 INSERT 는 막음)
create policy participants_read on public.meetup_participants for select to authenticated
  using (user_id = auth.uid() or exists (select 1 from public.meetups m where m.id = meetup_id and m.creator = auth.uid()));
create policy participants_cancel on public.meetup_participants for update to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid() and status = 'cancelled');

-- games / scores: 동호회 경기는 회원 읽기, 점수 입력은 경기 생성자(운영자) 또는 기록 담당. 수정 이력은 감사 테이블에만.
create policy games_read on public.games for select to authenticated
  using (club_id is null or public.is_club_member(club_id));
create policy games_create on public.games for insert to authenticated
  with check (created_by = auth.uid() and (club_id is null or public.is_club_staff(club_id)));
create policy scores_read on public.game_scores for select to authenticated
  using (exists (select 1 from public.games g where g.id = game_id and (g.club_id is null or public.is_club_member(g.club_id))));
-- score_audit_logs: 읽기만 (쓰기는 함수 전용)
create policy score_audit_read on public.score_audit_logs for select to authenticated
  using (exists (select 1 from public.games g where g.id = game_id and (g.club_id is null or public.is_club_staff(g.club_id))));

-- 회비·장부: 운영자(회계 담당 포함)만
create policy dues_staff on public.club_dues for all to authenticated
  using (public.is_club_staff(club_id)) with check (public.is_club_staff(club_id));
create policy tx_staff on public.club_transactions for all to authenticated
  using (public.is_club_staff(club_id)) with check (public.is_club_staff(club_id) and recorded_by = auth.uid());

-- 구독·결제: 동호회 운영자만 읽기. 쓰기는 서버 함수(service role)만 → 클라이언트 쓰기 정책 없음
create policy subs_staff_read on public.subscriptions for select to authenticated using (public.is_club_staff(club_id));
create policy payments_staff_read on public.payments for select to authenticated using (public.is_club_staff(club_id));

-- 신고: 본인 신고 생성·본인 것 조회. 처리는 관리자 함수
create policy reports_insert on public.reports for insert to authenticated with check (reporter = auth.uid());
create policy reports_read_own on public.reports for select to authenticated using (reporter = auth.uid());

-- 관리자 감사 로그: 클라이언트 접근 전면 차단 (정책 없음 = 거부)
-- 신고 처리·구독 상태 변경·승인 등 권한 행위는 security definer 함수에서만 수행하고 admin_audit_logs 에 기록한다.
