-- Run this in Supabase → SQL Editor

-- Users
create table if not exists users (
  id           uuid primary key default gen_random_uuid(),
  email        text unique not null,
  password_hash text not null,
  is_verified  boolean default false,
  created_at   timestamptz default now()
);

-- Preferences (one row per user)
create table if not exists preferences (
  user_id      uuid primary key references users(id) on delete cascade,
  diet         text default 'veg',
  health       text default 'normal',
  cuisine      text default 'north_indian',
  mood         text default 'tired',
  time_minutes int  default 30,
  updated_at   timestamptz default now()
);

-- Recipe history
create table if not exists recipe_history (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references users(id) on delete cascade,
  ingredients text[],
  recipes     jsonb,
  created_at  timestamptz default now()
);

-- Favourites
create table if not exists favourites (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references users(id) on delete cascade,
  recipe_name text not null,
  recipe      jsonb,
  saved_at    timestamptz default now()
);

-- OTP tokens
create table if not exists otp_tokens (
  id          uuid primary key default gen_random_uuid(),
  email       text not null,
  otp         text not null,
  expires_at  timestamptz not null,
  used        boolean default false,
  created_at  timestamptz default now()
);
create index if not exists otp_tokens_email_idx on otp_tokens (email, expires_at);

-- Auto-cleanup expired OTPs (optional, run as cron or on-demand)
-- delete from otp_tokens where expires_at < now();
