# Beta 100 Plan — AHA

**Product:** Beta (early users on their own Mac/Windows)  
**Philosophy:** `AHA_PHILOSOPHY.md` — assistant language only  
**Status baseline:** ~75–80% complete → target **100%**  
**Related:** `LAUNCH100_PLAN.md` (Launch requires Beta 100% first)

---

## What “Beta 100” means

A small group can **install**, grant **Accessibility + Screen Recording**, use **test Razorpay** (or approved dev license), **sign in**, run **Tier‑1 social** flows without an AI key, and use **Tier‑2** with BYOK — without hand-holding every session.

**Not required for Beta 100:** live dailyassist.xyz billing, prod Supabase, marketing site, macOS Keychain for BYOK, notarization.

---

## Readiness checklist

### 1. Real-device proof (highest priority)

- [ ] **Mac E2E** — fresh install → permissions → companion → sign in → license sync (test) → one Tier‑1 flow (e.g. FB/IG status) → save BYOK → one Tier‑2 ask
- [ ] **Windows E2E** — same path via `start.bat` / Windows Chrome launcher
- [ ] **Beta tester guide** — one doc: permissions, test card, Tier‑1 vs Tier‑2, BYOK optional, known limits (`INSTALL.md` + short `BETA_TESTERS.md` or section in `INSTALL.md`)

### 2. Tier‑1 reliability

- [ ] **WhatsApp DM `contact_name`** — extract from user message in `agent.py` and pass into `run_social_task` params (flow uses `text_fallback="contact_name"` today without substitution)
- [ ] **Vision preview** — social steps do not return stale/blank preview images (REINVENT M9)
- [ ] **Vault clarity** — document which calendar/vault path beta users should use (`aha/storage_vault.py` vs companion `Slots/`), or unify paths so testers are not confused (REINVENT H1)

### 3. Companion polish

- [ ] **License fail-closed** — if `/api/license/status` errors, do not treat user as licensed (REINVENT M1)
- [ ] **Auto-continue guard** — cancel/overlap protection on 10s auto-continue loop (REINVENT M3)
- [ ] **Fetch errors** — critical companion fetches check `res.ok` and show errors (REINVENT M4)
- [ ] **HTML/JS fixes** — unclosed `vault-controls` div; scope `currentUploadDay` (REINVENT M12–M13)
- [ ] **Settings** — remove Anthropic from UI or implement it (REINVENT M11)

### 4. Security (beta bar)

- [ ] **Phase 0 hygiene** — confirm no secrets in git history; rotate keys if `.env` was ever committed (REINVENT Phase 0)
- [ ] **`POST /api/content/generate`** — do not accept raw `api_key` in body; use BYOK only (REINVENT C6)
- [ ] **BYOK disclosure** — companion/settings copy: keys stored locally in `~/.aha/config.json` (plaintext) — acceptable for private beta with warning; Launch moves to Keychain

### 5. Tests

- [ ] **`aha/license.py`** — set/get/delete, `get_raw_api_key`, status shape
- [ ] **License middleware** — protected agent routes reject without valid license/session
- [ ] **Mocked E2E** — save BYOK → Tier‑2 uses user key (extend `tests/test_byok.py`)
- [ ] **`/api/browser/click`** — contract test if missing

### 6. Beta distribution

- [ ] **Unsigned zip** — build/test per `DISTRIBUTION.md`; artifacts in `downloads/` for testers
- [ ] **Test Razorpay path** — `http://127.0.0.1:8000/subscribe` → pay → verify → `/download` → install → license sync (`BILLING.md`, `SUBSCRIPTION_SETUP.md`)

---

## Already done (do not re-do)

Phases 1–2 and much of 4–5 from `REINVENT_PLAN.md`, including:

- BYOK wired to agent (`aha/byok.py`, `get_raw_api_key`)
- Session token + server-side license on protected routes (`aha/security.py`)
- CORS locked to `127.0.0.1`
- Vault slot sanitization, upload allowlists
- Vision click → `/api/browser/click`
- `confirm_template` / `confirm_text` in m9 executor
- CI pytest (~93 tests), agent step lock

---

## Definition of done

**Beta = 100%** when every unchecked item above is done and one Mac + one Windows run completed the full E2E script without manual fixes.

**Next product:** `LAUNCH100_PLAN.md`

---

## Suggested order

1. Mac + Windows E2E + beta tester doc  
2. WhatsApp `contact_name` + license fail-closed + content/generate BYOK  
3. Companion polish + critical tests  
4. Test Razorpay full path + zip distribution smoke  

**Cursor model hint:** Composer + terminal pytest for tests/E2E notes; Sonnet/Opus (thinking) for vault unify or `contact_name` extraction if ambiguous.

---

*Update checkboxes as work completes. Canonical audit history: `REINVENT_PLAN.md`.*
