-- AHA — Razorpay payments & subscription records
-- Run after 001_initial_schema.sql

create table if not exists aha_payments (
    id                  uuid primary key default gen_random_uuid(),
    uid                 text not null references aha_users(uid) on delete cascade,
    razorpay_order_id   text not null unique,
    razorpay_payment_id text unique,
    amount_paise        integer not null,
    currency            text not null default 'INR',
    plan                text not null default 'core',
    status              text not null default 'created',  -- created | paid | failed
    license_key         text,
    created_at          timestamptz not null default now(),
    paid_at             timestamptz
);

create index if not exists idx_aha_payments_uid on aha_payments (uid);

alter table aha_payments enable row level security;

create policy "payments_select_own" on aha_payments
    for select using (uid = current_setting('request.jwt.claims', true)::json->>'sub');
