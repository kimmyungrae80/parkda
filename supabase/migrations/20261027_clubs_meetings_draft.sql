-- 초안 (미적용). 동호회·함께 치기 서버 구조. 인증 설계 승인 후 검토하여 적용.
-- 원칙: 모든 테이블 RLS 활성, 권한 판단은 DB 함수에서, 전화번호 미저장.

create table if not exists public.profiles (
  user_id      uuid primary key references auth.users(id) on delete cascade,
  display_name text not null check (char_length(display_name) between 1 and 20),
  created_at   timestamptz not null default now()
);

create table if not exists public.clubs (
  id         uuid primary key default gen_random_uuid(),
  name       text not null check (char_length(name) between 2 and 40),
  region     text not null,
  intro      text,
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now()
);

create table if not exists public.club_members (
  club_id  uuid not null references public.clubs(id) on delete cascade,
  user_id  uuid not null references auth.users(id) on delete cascade,
  role     text not null default 'member' check (role in ('owner','manager','member')),
  status   text not null default 'pending' check (status in ('pending','approved','left','removed')),
  joined_at timestamptz not null default now(),
  primary key (club_id, user_id)
);

create table if not exists public.club_notices (
  id        uuid primary key default gen_random_uuid(),
  club_id   uuid not null references public.clubs(id) on delete cascade,
  title     text not null,
  body      text,
  posted_by uuid not null references auth.users(id),
  created_at timestamptz not null default now()
);

create table if not exists public.meetings (
  id         uuid primary key default gen_random_uuid(),
  creator    uuid not null references auth.users(id),
  venue_id   text not null,
  meet_date  date not null,
  meet_time  text,
  capacity   integer not null check (capacity between 2 and 4),
  status     text not null default 'open' check (status in ('open','closed','confirmed','cancelled')),
  game_code  text unique,
  created_at timestamptz not null default now()
);

create table if not exists public.meeting_participants (
  meeting_id uuid not null references public.meetings(id) on delete cascade,
  user_id    uuid not null references auth.users(id) on delete cascade,
  status     text not null default 'joined' check (status in ('joined','confirmed','cancelled')),
  primary key (meeting_id, user_id)
);

create table if not exists public.audit_log (
  id     bigint generated always as identity primary key,
  actor  uuid,
  action text not null,
  target text,
  at     timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.clubs enable row level security;
alter table public.club_members enable row level security;
alter table public.club_notices enable row level security;
alter table public.meetings enable row level security;
alter table public.meeting_participants enable row level security;
alter table public.audit_log enable row level security;
-- 정책은 승인 후 작성: 본인 행만 읽기, 가입 신청(INSERT) 본인 명의만, 승인·공지는 security definer 함수만.
-- audit_log 는 클라이언트 읽기·쓰기 모두 차단.
