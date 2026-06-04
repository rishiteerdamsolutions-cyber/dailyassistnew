# dailyassist.xyz — Website design brief (for designer)

**Product:** AHA — **daily computer assistance** (same category as Claude computer use / Operator / Copilot)  
**Domain:** https://www.dailyassist.xyz  
**Site name:** dailyassist.xyz

---

## 1. Core concept (read this first)

AHA is **daily assistance on your computer** — you **ask**, it **helps** on your screen (Mac or Windows).

**What customers should understand:**

- Install the app, subscribe, sign in, **ask in chat** for help with tasks on the computer.
- It works like a **human using your machine** — seeing the screen, clicking, typing.
- After subscribe, core assistance **just works** on Mac/Windows — no extra setup required for typical daily tasks.
- For some tasks, users **may** add their own AI key in app settings — optional, their cost.

**What customers must NOT see on the website:**

- Vault, storage, slots, calendar folders, CSV import, “content pipeline”
- **Social media, posting, schedules, reels, captions, influencers, platform logos as hero**
- Tier 1 / Tier 2, routes, hardcoded flows, vision templates, modules, agents (m1–m10)
- “Automation,” “auto-post bot,” “we store your media in the cloud”
- Any internal routing (which tasks use AI vs fixed flows) — **never in marketing copy**

**Internal truth (for founders/devs only — never marketing copy):**

- Some tasks = fixed on-screen flows, no LLM at execution time.
- Other asks = optional user AI key for planning which button to click.
- Saving an AI key does **not** change how fixed-flow tasks run.

---

## 2. Brand & voice

| Always | Never |
|--------|--------|
| **Assistant**, **daily assistance**, **helps**, **ask**, **your computer** | Automation, automate, bot, autopilot |
| **Subscribe**, **Download**, **Get started** | Vault, storage, orchestrator, agents, modules |
| **Mac & Windows** | Engineering or architecture diagrams on homepage |

**Names:** **AHA** (product) · **dailyassist.xyz** (site)  
**Support:** support@dailyassist.xyz

**Tagline options:**

- “Daily assistance on your computer.”
- “Ask. Get help on your screen.”
- “Computer use assistance — on your Mac or Windows.”

**Pricing (public):** **₹2,999 / month** (confirm yearly with client before final designs).

**Do not justify price with** post counts or internal math on the site — keep pricing simple: one subscription, full daily computer assistance.

---

## 3. Site map

| Page | URL | Purpose |
|------|-----|---------|
| **Home** | `/` | What it is, who it’s for, how simple it is, CTAs |
| **Subscribe** | `/subscribe` | Sign in → pay (Razorpay) |
| **Download** | `/download` | Sign in → download Mac / Windows app |
| **How it works** | `/how-it-works` | 3–4 simple steps — **no vault/storage language** |
| **FAQ** | `/faq` | Subscriptions, Mac/Win, privacy, “what is this?” |
| **Legal** | `/legal.html` | Terms, Privacy, Refunds, Delivery |
| **Contact** | footer or `/contact` | support@dailyassist.xyz |

**Footer:** Subscribe · Download · Legal · support@

**Not public:** dev dashboards, module UI, `/demo`.

---

## 4. Page content (customer-facing only)

### Home `/`

- **Headline:** Daily computer assistance — ask, get help on your screen.
- **Subhead:** Works on Mac and Windows. Helps with everyday tasks on screen when you ask.
- **Bullets (example):**
  - Chat what you want done
  - Works in the apps and sites you already use
  - Runs on your computer — you stay in control
- **Optional line:** Add your own AI key in settings for some tasks (optional — no detail).
- **CTAs:** Subscribe · Download
- **No:** vault diagrams, tier tables, module names

### How it works `/how-it-works`

1. Subscribe on dailyassist.xyz  
2. Download and install (Mac or Windows)  
3. Sign in and **ask** in the app  
4. It helps on your screen in the apps and sites you already use  

**Do not mention:** social media, posting, platforms by name, folders, storage, BYOK acronym.

### Subscribe `/subscribe`

Sign in (email + Google) → plan → Razorpay → success → go to Download.

### Download `/download`

Sign in → active subscription → Mac zip / Windows zip.

### FAQ `/faq` (examples)

- What is AHA? → Daily assistance on your computer when you ask.  
- Do I need an AI API key? → **No** to get started. Optional key in app settings for some tasks.  
- Is this automation? → **No** — daily assistance on **your** machine when you ask.  
- Mac / Windows? → Yes.  
- Subscription ended? → Renew on the site.

---

## 5. User journey (wireframe)

```text
Home → Subscribe (pay) → Download app → Install → Sign in → Ask in chat → Done
```

Optional later: user adds AI key in app — **not part of homepage story**.

---

## 6. Visual direction

- Trustworthy, simple, “computer assistant” — not scheduler/SMM tool branding
- Show **chat + laptop/desktop**, not file folders or calendars
- India-friendly: ₹, Razorpay
- Dark professional UI acceptable; designer may propose fresh system

---

## 7. Designer deliverables

- Figma: Home, Subscribe, Download, How it works, FAQ, Legal layout  
- Mobile + desktop  
- Logo / OG image  
- Style guide for dev handoff (static site on Vercel)

---

## 8. One paragraph for the designer

**dailyassist.xyz** sells **AHA**, a **daily computer assistance** app for Mac and Windows — like computer-use assistants people already know, priced for India at **₹2,999/month**. Users subscribe, download, sign in, and **ask** for help on their screen. The website must **never** mention social media, posting, or channel names. Tone: **ask → help**, not automation jargon. Optional AI keys are a footnote, not the hero story.

---

*Internal architecture: see `AHA_PHILOSOPHY.md` — marketing always follows this brief when they conflict.*
