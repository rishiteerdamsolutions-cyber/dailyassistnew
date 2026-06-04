-- AHA — Promo coupons (admin-managed, test codes like COUPON100)
-- Run after 003_payments.sql

create table if not exists aha_coupons (
    id               uuid primary key default gen_random_uuid(),
    code             text not null unique,
    discount_percent smallint not null check (discount_percent between 1 and 100),
    plan_id          text,                    -- null = any plan in billing PLANS
    max_uses         integer,                  -- null = unlimited
    uses_count       integer not null default 0,
    is_active        boolean not null default true,
    note             text,
    expires_at       timestamptz,
    created_at       timestamptz not null default now(),
    updated_at       timestamptz not null default now()
);

create table if not exists aha_coupon_redemptions (
    id          uuid primary key default gen_random_uuid(),
    coupon_id   uuid not null references aha_coupons(id) on delete cascade,
    uid         text not null references aha_users(uid) on delete cascade,
    plan_id     text not null,
    license_key text,
    redeemed_at timestamptz not null default now(),
    unique (coupon_id, uid)
);

create index if not exists idx_aha_coupon_redemptions_uid on aha_coupon_redemptions (uid);

alter table aha_coupons enable row level security;
alter table aha_coupon_redemptions enable row level security;
-- No client policies: server uses service role only.

create trigger trg_aha_coupons_updated_at
    before update on aha_coupons
    for each row execute function update_updated_at();

-- Default test coupon: 100% off (no Razorpay payment required)
insert into aha_coupons (code, discount_percent, plan_id, max_uses, note)
values (
    'COUPON100',
    100,
    null,
    5,
    'Internal testing — 100% off any plan (max 5 redemptions)'
)
on conflict (code) do nothing;
