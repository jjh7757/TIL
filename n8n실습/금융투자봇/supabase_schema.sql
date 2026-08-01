-- KIS 모의투자 연동 텔레그램 에이전트 봇 - Supabase 스키마
-- Supabase SQL Editor에서 실행. RLS를 켜두면 anon/authenticated 키로는 접근 불가하고,
-- n8n에서 쓰는 service_role 키만 RLS를 무시하고 접근 가능하다.

create table if not exists kis_token (
  id int primary key default 1,
  access_token text,
  expires_at timestamptz,
  constraint single_row check (id = 1)
);

create table if not exists alerts (
  id bigserial primary key,
  chat_id text not null,
  stock_code text not null,
  stock_name text,
  target_price numeric not null,
  direction text check (direction in ('above', 'below')),
  active boolean default true,
  created_at timestamptz default now()
);

create table if not exists trade_log (
  id bigserial primary key,
  chat_id text not null,
  stock_code text not null,
  side text check (side in ('buy', 'sell')),
  qty int not null,
  price numeric,
  order_no text,
  created_at timestamptz default now()
);

alter table kis_token enable row level security;
alter table alerts enable row level security;
alter table trade_log enable row level security;
