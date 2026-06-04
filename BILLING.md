# Razorpay subscriptions (Mac + Windows)

## Setup

1. Add test keys to `.env` (from Razorpay dashboard or your `rzp-key-2.csv` — **never commit the CSV**):

   ```
   RAZORPAY_KEY_ID=rzp_test_...
   RAZORPAY_KEY_SECRET=...
   AHA_PLAN_CORE_MONTHLY_PAISE=100
   ```

   `100` paise = ₹1 for test checkouts.

2. Run Supabase migrations: `003_payments.sql`, then `005_coupons.sql` (seeds **COUPON100** = 100% off)

3. Set admin email in `.env`: `AHA_ADMIN_EMAILS=you@example.com`

4. Start AHA: `start_companion.command` (Mac) or `start.bat` (Windows)

## Admin & test coupons

- **Admin dashboard:** http://127.0.0.1:8000/admin — customer analytics, coupon list, create codes
- **Test checkout:** on `/subscribe`, sign in, enter `COUPON100`, click **Redeem 100% coupon** (no Razorpay)

## User flow

1. **Subscribe:** http://127.0.0.1:8000/subscribe — sign in → pay with Razorpay  
2. **Download:** http://127.0.0.1:8000/download — Mac zip / Windows zip  
3. **Install** per `INSTALL.md`  
4. **Open companion** — sign in → license syncs via `/api/license/sync`

## Production (dailyassist.xyz)

- Host the same FastAPI app (or proxy `/api/billing/*` to it).
- Place release zips in `downloads/AHA-mac.zip` and `downloads/AHA-win.zip`.
- Swap `rzp_test_*` keys for **live** Razorpay keys in production `.env`.

---

## Before go-live — Razorpay webhook (required reminder)

**Test mode today:** checkout + `/api/billing/verify` after payment is enough. Webhook can wait.

**Before you switch to the live URL**, you must enable the webhook (do not skip):

1. In Razorpay Dashboard → **Webhooks** → Add endpoint:  
   `https://<YOUR-LIVE-DOMAIN>/api/billing/webhook`
2. Subscribe to event: **`payment.captured`**
3. Copy the webhook signing secret into production `.env`:  
   `RAZORPAY_WEBHOOK_SECRET=...`
4. Smoke-test: complete one live ₹1 (or min) payment and confirm `aha_payments.status = paid` in Supabase even if the user closes the browser before verify runs.

The handler is already implemented in `aha/billing.py` (`handle_razorpay_webhook`). Until go-live, client-side verify remains the primary path.

## Razorpay test card

Use Razorpay test mode cards from their docs (e.g. successful payment test card in the Razorpay dashboard).
