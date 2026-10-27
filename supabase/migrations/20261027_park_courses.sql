-- PARKDA 2.0: 전국 파크골프장 공개 데이터 (기존 parkda_store 와 분리된 새 테이블)
-- 상태: 작성만 됨. 운영 DB 에는 적용하지 않음 (별도 승인 필요).
-- 원칙: 공개 읽기는 공식 출처로 확인된 행만. 쓰기는 서버(service role)만 가능 → 클라이언트 키로 쓰기 불가.

create table if not exists public.park_courses (
  id                  text primary key,              -- 지역+이름+주소 해시 기반, 재실행해도 같음
  name                text not null,
  region              text,                           -- 시도 (서울, 부산, … 전남, 광주)
  city                text,
  district            text,
  address             text,
  road_address        text,
  latitude            double precision,
  longitude           double precision,
  coordinate_source   text,                           -- official_dataset | osm_nominatim | null
  coordinate_note     text,
  holes               integer,
  course_count        integer,
  fee                 text,
  opening_hours       text,
  closed_days         text,
  reservation_method  text,
  reservation_url     text,
  phone               text,
  operator            text,
  parking             text,
  restroom            text,
  website             text,
  source_name         text not null,
  source_url          text not null,
  source_license      text,
  verified_at         date,
  verification_status text not null check (verification_status in
                        ('official_dataset', 'official_page_checked', 'unverified_candidate', 'needs_review')),
  flags               text[] not null default '{}',
  updated_at          timestamptz not null default now()
);

create index if not exists park_courses_region_idx on public.park_courses (region);
create index if not exists park_courses_name_idx on public.park_courses (name);

create table if not exists public.park_tournaments (
  id              text primary key,
  title           text not null,
  venue           text,
  date_start      date,
  date_end        date,
  period          text,                                -- 예정 대회 | 지난 대회 | 일정 확인 중
  organizer       text,
  co_organizer    text,
  contact         text,
  apply_url       text,
  result_url      text,
  source_name     text not null,
  source_url      text not null,
  publisher       text,
  source_license  text,
  checked_at      date,
  verification_status text not null default 'official_dataset',
  updated_at      timestamptz not null default now()
);

-- 행 수준 보안: 공개 읽기는 공식 확인 행만
alter table public.park_courses enable row level security;
alter table public.park_tournaments enable row level security;

drop policy if exists "park_courses_public_read_verified" on public.park_courses;
create policy "park_courses_public_read_verified" on public.park_courses
  for select to anon, authenticated
  using (verification_status in ('official_dataset', 'official_page_checked'));

drop policy if exists "park_tournaments_public_read" on public.park_tournaments;
create policy "park_tournaments_public_read" on public.park_tournaments
  for select to anon, authenticated
  using (verification_status = 'official_dataset');

-- 쓰기 정책은 만들지 않는다 (anon/authenticated 쓰기 차단). 적재는 service role 로만 수행.
