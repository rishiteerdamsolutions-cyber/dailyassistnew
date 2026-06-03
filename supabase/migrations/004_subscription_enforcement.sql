-- AHA — subscription enforcement helpers
-- Run in Supabase SQL Editor after 001–003

-- Index for expiry lookups
create index if not exists idx_aha_licenses_expires
    on aha_licenses (expires_at)
    where is_active = true;

-- Deactivate licenses that are past expires_at (run manually or on a schedule)
create or replace function aha_deactivate_expired_licenses()
returns integer
language plpgsql
security definer
as $$
declare
    n integer;
begin
    update aha_licenses
    set is_active = false
    where is_active = true
      and expires_at is not null
      and expires_at < now();
    get diagnostics n = row_count;
    return n;
end;
$$;

-- Optional: run once now
-- select aha_deactivate_expired_licenses();

-- For automatic daily cleanup, enable pg_cron in Supabase and run:
-- select cron.schedule(
--   'aha-expire-licenses',
--   '0 3 * * *',
--   $$ select aha_deactivate_expired_licenses(); $$
-- );
