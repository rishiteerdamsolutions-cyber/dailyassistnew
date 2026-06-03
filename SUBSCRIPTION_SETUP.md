# Subscription enforcement — what to run in Supabase

After paying, users get **30 days** (`expires_at`). When that date passes, the **installed app stops working** and **downloads are blocked**.

## 1. Run migration (SQL Editor)

Run in order if not already done:

1. `supabase/migrations/001_initial_schema.sql`
2. `supabase/migrations/002_storage_bucket.sql`
3. `supabase/migrations/003_payments.sql`
4. **`supabase/migrations/004_subscription_enforcement.sql`** ← new

## 2. Deactivate expired licenses (run once now)

In SQL Editor:

```sql
select aha_deactivate_expired_licenses();
```

You should see how many rows were turned off.

## 3. Schedule daily cleanup (recommended)

In Supabase Dashboard → **Database** → enable **pg_cron** (if available on your plan), then:

```sql
select cron.schedule(
  'aha-expire-licenses',
  '0 3 * * *',
  $$ select aha_deactivate_expired_licenses(); $$
);
```

Or run `select aha_deactivate_expired_licenses();` manually once a day until cron is set up.

## 4. Verify a paying user

After a test payment, check:

```sql
select uid, license_key, plan, is_active, expires_at, activated_at
from aha_licenses
order by activated_at desc
limit 5;
```

`expires_at` should be about **30 days** after payment for monthly plan.

## 5. Upload installer zips

Put files in the project (not public URL):

- `downloads/AHA-mac.zip`
- `downloads/AHA-win.zip`

Users download only via **/download** page → signed-in → active subscription → `/api/download/mac` or `/win`.

## 6. Vercel environment variables

Set in Vercel project → Settings → Environment Variables:

- `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET`
- `SUPABASE_URL` / `SUPABASE_SERVICE_KEY`
- `FIREBASE_SERVICE_ACCOUNT_JSON` (full JSON one line) or path equivalent

## How enforcement works

| Step | Behavior |
|------|----------|
| Download | Firebase login + active `expires_at` required |
| Install & open app | Sign in → `/api/license/sync` pulls cloud license |
| Every ~1 hour | App re-checks Supabase; expired → UI blocked + API 403 |
| After 30 days | `expires_at` passed → `is_active` set false → app unusable |

Dev-only fake keys are **disabled** unless `AHA_ALLOW_DEV_LICENSE=1` in `.env` (do not set in production).
