# Website build prompt — dailyassist.xyz (AHA)

Copy everything below the line and give it to your designer/developer.

---

## Build the marketing and checkout website for **dailyassist.xyz**

### Product

**AHA** is **daily computer assistance** for **Mac and Windows**.

- Users **subscribe** on the website, **download** the desktop app, sign in, and **ask in chat** for help.
- The assistant works **on the user’s own computer** — seeing the screen and helping with actions when asked (same category as “computer use” / daily assistance products).
- Position as an **assistant**, not “automation software.”

**Do not mention on the website:**

- Social media, posting, scheduling, reels, captions, or named platforms (Facebook, Instagram, etc.)
- Vault, storage, slots, calendars, CSV, content pipelines
- Internal engineering terms (agents, modules, tiers, orchestrator, BYOK as an acronym in headlines)
- “We automate your accounts”

**Optional footnote only (small text, not hero):** Users may add their own AI provider key in the app settings for some kinds of help. Do not explain internal routing.

---

### Pricing (display clearly on Pricing / Subscribe page)

Two plans, **USD**, monthly subscription:

#### **Starter — $20 / month**

- **150 high-value tasks per month** (shown as **5 high-value tasks per day**).
- **Execution only** — the assistant carries out tasks the user directs; **no content creation** included in this plan.
- Short explanation for buyers: *You ask → AHA helps on your screen. Starter covers running tasks, not creating copy, images, or media for you.*

#### **Pro — $20 / month** *(confirm final Pro price with client if it should be higher than Starter)*

- **Everything in Starter**, plus:
- User connects **their own AI API key** in the app.
- **Unlimited high-value tasks** (fair-use policy link in Terms — no hard cap in marketing).
- **Content creation and execution** — user can ask for help that includes creating text/media as part of tasks, plus carrying them out on screen, using **their** AI key for creation-related work.

**Comparison table (simple):**

| | Starter $20/mo | Pro $20/mo |
|---|----------------|------------|
| High-value tasks | 150/month (5/day) | Unlimited |
| Execution on screen | Yes | Yes |
| Content creation | No | Yes (via user’s AI key) |
| Bring your own AI key | No | Yes |

**Checkout:** Monthly billing. Show plan name, price, what’s included, and link to legal policies before payment.

**Support email (visible in footer and legal):** support@dailyassist.xyz

**Domain:** dailyassist.xyz

---

### Pages to build (complete site map)

#### Marketing

1. **Home** (`/`)  
   - Hero: daily computer assistance, Mac & Windows.  
   - What it is: ask → help on your screen.  
   - Two plan teasers with price and one-line difference.  
   - CTAs: **View pricing** / **Subscribe** and **Download** (download explained: after subscribe).

2. **Pricing** (`/pricing` or combined with Subscribe)  
   - Starter vs Pro table (above).  
   - FAQ snippet: what counts as a “high-value task” (plain language: a substantial assist session on the computer when you ask — not email/password resets).  
   - CTA per plan → checkout.

3. **Subscribe / Checkout** (`/subscribe`)  
   - Sign in or create account (email + password; Google sign-in if available).  
   - Select Starter or Pro.  
   - Pay (payment gateway checkout).  
   - Success state: “Payment successful” → button **Go to Download**.  
   - Failure and “already subscribed” states.

4. **Download** (`/download`)  
   - Sign in.  
   - If no active subscription: message + link to Pricing.  
   - If active: show plan name, renewal/expiry if known, **Download for Mac** and **Download for Windows**.  
   - One line: sign in inside the app with the same account.

5. **How it works** (`/how-it-works`)  
   - 4 steps: Subscribe → Download → Install → Ask in the app.  
   - No social or storage language.

6. **FAQ** (`/faq`)  
   - What is AHA?  
   - Starter vs Pro?  
   - What is a high-value task?  
   - Do I need my own AI key? (Starter: no. Pro: for unlimited + content creation.)  
   - Mac and Windows?  
   - Refunds? (link to policy)  
   - Is this automation? (No — assistance on your machine when you ask.)

7. **About** (`/about`) — recommended for payment gateway review  
   - Who operates dailyassist.xyz.  
   - What product is sold (desktop software subscription).  
   - Country of operation: India.  
   - Contact email.

8. **Contact** (`/contact` or footer-only)  
   - support@dailyassist.xyz  
   - Simple form optional (name, email, message).

#### Legal — **required for Razorpay / payment gateway approval**

These must be **linked in the footer on every page** and reachable without login. Use clear headings and “Last updated” date.

9. **Terms of Service** (`/terms` or `/legal#terms`)  
   - Service description: desktop assistance software, subscription plans.  
   - User responsibilities, acceptable use, account/license.  
   - Limitation of liability, governing law (India).  
   - Plan limits: Starter task limits; Pro requires user-supplied API key for unlimited/content features.  
   - No illegal use, spam, malware.

10. **Privacy Policy** (`/privacy` or `/legal#privacy`)  
    - Account data (email, sign-in).  
    - Payment processed by payment partner — you do not store card/UPI secrets.  
    - Local app data on user’s device; screen capture only when user requests help; Pro may send data to **user’s** AI provider with **user’s** key.  
    - Data retention, user rights, contact for privacy requests.

11. **Refund & Cancellation Policy** (`/refund` or `/legal#refund`)  
    - Subscription is monthly.  
    - Cancellation: how to cancel (email or account flow).  
    - Refund rules: e.g. refund within 7 days if no substantial use, or no refunds after download/license activated — **client to confirm final rule**; policy must be explicit for gateway approval.  
    - Chargebacks and support contact.

12. **Delivery / Shipping Policy** (`/delivery` or `/legal#delivery`)  
    - **Digital product only** — no physical shipping.  
    - Delivery method: download link after payment + license activation.  
    - Expected delivery: immediate after successful payment (within minutes).  
    - Support if download fails.

13. **Pricing & Billing disclosure** (can be section on Terms or standalone `/billing`)  
    - Prices in USD (or INR if merchant settles in INR — match actual Razorpay currency).  
    - Recurring monthly charge until cancelled.  
    - Taxes/GST if applicable.  
    - Receipt/invoice via payment provider.

#### Post-payment

14. **Payment success** (`/subscribe/success` or query state)  
    - Thank you, plan name, link to Download.

15. **Payment failed** (`/subscribe/failed`)  
    - Retry, contact support.

#### Error

16. **404** — friendly page with links Home, Pricing, Support.

---

### Footer (every page)

Subscribe · Pricing · Download · How it works · FAQ · About  
Terms · Privacy · Refunds · Delivery · Contact  
support@dailyassist.xyz  
© dailyassist.xyz

---

### Razorpay merchant checklist (content must exist on live site)

Before applying or going live, the live domain should show:

- [ ] Business name and what you sell (software subscription)  
- [ ] **Pricing** visible without login (Starter $20, Pro $20)  
- [ ] **Terms of Service**  
- [ ] **Privacy Policy**  
- [ ] **Refund / Cancellation Policy**  
- [ ] **Delivery Policy** (digital delivery)  
- [ ] **Contact email** (support@dailyassist.xyz)  
- [ ] **About** page with real business context  
- [ ] HTTPS on dailyassist.xyz  
- [ ] Checkout shows amount, plan description, and links to policies  

---

### Visual / UX direction (no tech specified)

- Professional, calm, trustworthy; readable on mobile.  
- Show **laptop + chat** — not robots, not social media dashboards.  
- Primary CTAs: Subscribe, Download.  
- Indian audience OK; prices shown in **USD** as listed above unless client switches to INR for Razorpay.

---

### One-sentence brief for the header of the creative deck

**dailyassist.xyz sells AHA — daily computer assistance for Mac and Windows: Starter ($20/mo, 150 high-value execution-only tasks) and Pro ($20/mo, unlimited tasks with user’s AI key for content creation + execution).**

---

*End of prompt.*
