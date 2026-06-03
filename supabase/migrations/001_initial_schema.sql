-- AHA — Supabase initial schema
-- Run this in Supabase Dashboard → SQL Editor

-- ─────────────────────────────────────────────────────────────
-- aha_users
-- Mirrors Firebase Auth user; uid = Firebase UID (string)
-- ─────────────────────────────────────────────────────────────
create table if not exists aha_users (
    uid            text primary key,          -- Firebase UID
    email          text unique not null,
    display_name   text,
    plan           text not null default 'free',  -- free | core | hybrid | ai_budget | ai_pro
    created_at     timestamptz not null default now(),
    updated_at     timestamptz not null default now()
);

-- RLS: users can only read/update their own row
alter table aha_users enable row level security;

create policy "users_select_own" on aha_users
    for select using (uid = current_setting('request.jwt.claims', true)::json->>'sub');

create policy "users_insert_own" on aha_users
    for insert with check (uid = current_setting('request.jwt.claims', true)::json->>'sub');

create policy "users_update_own" on aha_users
    for update using (uid = current_setting('request.jwt.claims', true)::json->>'sub');

-- ─────────────────────────────────────────────────────────────
-- aha_licenses
-- One row per license key activation
-- ─────────────────────────────────────────────────────────────
create table if not exists aha_licenses (
    id             uuid primary key default gen_random_uuid(),
    uid            text not null references aha_users(uid) on delete cascade,
    license_key    text not null unique,
    plan           text not null default 'core',
    activated_at   timestamptz not null default now(),
    expires_at     timestamptz,               -- null = lifetime
    is_active      boolean not null default true
);

alter table aha_licenses enable row level security;

create policy "licenses_select_own" on aha_licenses
    for select using (uid = current_setting('request.jwt.claims', true)::json->>'sub');

create policy "licenses_insert_own" on aha_licenses
    for insert with check (uid = current_setting('request.jwt.claims', true)::json->>'sub');

-- ─────────────────────────────────────────────────────────────
-- aha_vault_meta
-- Lightweight calendar metadata — actual files in Supabase Storage
-- ─────────────────────────────────────────────────────────────
create table if not exists aha_vault_meta (
    id             uuid primary key default gen_random_uuid(),
    uid            text not null references aha_users(uid) on delete cascade,
    slot           text not null,
    year           smallint not null,
    month          smallint not null check (month between 1 and 12),
    day            smallint not null check (day between 1 and 31),
    has_text       boolean not null default false,
    has_image      boolean not null default false,
    has_video      boolean not null default false,
    updated_at     timestamptz not null default now(),
    unique (uid, slot, year, month, day)
);

alter table aha_vault_meta enable row level security;

create policy "vault_meta_select_own" on aha_vault_meta
    for select using (uid = current_setting('request.jwt.claims', true)::json->>'sub');

create policy "vault_meta_insert_own" on aha_vault_meta
    for insert with check (uid = current_setting('request.jwt.claims', true)::json->>'sub');

create policy "vault_meta_update_own" on aha_vault_meta
    for update using (uid = current_setting('request.jwt.claims', true)::json->>'sub');

create policy "vault_meta_delete_own" on aha_vault_meta
    for delete using (uid = current_setting('request.jwt.claims', true)::json->>'sub');

-- Index for fast calendar lookups
create index if not exists idx_vault_meta_uid_slot
    on aha_vault_meta (uid, slot, year, month);

-- ─────────────────────────────────────────────────────────────
-- aha_slots
-- User-created content slot names
-- ─────────────────────────────────────────────────────────────
create table if not exists aha_slots (
    id             uuid primary key default gen_random_uuid(),
    uid            text not null references aha_users(uid) on delete cascade,
    slot_name      text not null,
    created_at     timestamptz not null default now(),
    unique (uid, slot_name)
);

alter table aha_slots enable row level security;

create policy "slots_select_own" on aha_slots
    for select using (uid = current_setting('request.jwt.claims', true)::json->>'sub');

create policy "slots_insert_own" on aha_slots
    for insert with check (uid = current_setting('request.jwt.claims', true)::json->>'sub');

create policy "slots_delete_own" on aha_slots
    for delete using (uid = current_setting('request.jwt.claims', true)::json->>'sub');

-- ─────────────────────────────────────────────────────────────
-- updated_at auto-trigger
-- ─────────────────────────────────────────────────────────────
create or replace function update_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger trg_aha_users_updated_at
    before update on aha_users
    for each row execute function update_updated_at();

create trigger trg_vault_meta_updated_at
    before update on aha_vault_meta
    for each row execute function update_updated_at();
