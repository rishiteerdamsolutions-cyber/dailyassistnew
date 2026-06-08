-- AHA — server-side daily task limits (tamper-proof; keyed by license)
-- Run in Supabase Dashboard → SQL Editor

-- ─────────────────────────────────────────────────────────────
-- aha_daily_usage
-- One row per user + platform + UTC calendar day
-- ─────────────────────────────────────────────────────────────
create table if not exists aha_daily_usage (
    id                   uuid primary key default gen_random_uuid(),
    user_id              text not null,              -- license_key (primary desktop identity)
    uid                  text references aha_users(uid) on delete set null,
    platform             text not null,              -- facebook | instagram | linkedin | x | whatsapp
    usage_date           date not null,              -- UTC date (server-enforced)
    last_post_timestamp  timestamptz not null default now(),
    task_type            text not null default 'social',
    created_at           timestamptz not null default now(),
    unique (user_id, platform, usage_date)
);

create index if not exists aha_daily_usage_date_idx on aha_daily_usage (usage_date desc);
create index if not exists aha_daily_usage_user_idx on aha_daily_usage (user_id);

-- ─────────────────────────────────────────────────────────────
-- aha_gemini_proxy_log
-- Lightweight audit trail for cloud-proxied Gemini calls
-- ─────────────────────────────────────────────────────────────
create table if not exists aha_gemini_proxy_log (
    id          uuid primary key default gen_random_uuid(),
    user_id     text not null,
    auth_mode   text not null check (auth_mode in ('byok', 'license')),
    model       text,
    created_at  timestamptz not null default now()
);

create index if not exists aha_gemini_proxy_log_created_idx on aha_gemini_proxy_log (created_at desc);

-- Service role only — desktop never reads these tables directly
alter table aha_daily_usage enable row level security;
alter table aha_gemini_proxy_log enable row level security;
