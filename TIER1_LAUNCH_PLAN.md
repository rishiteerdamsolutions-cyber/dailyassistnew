# Tier-1 Launch Plan — AHA (ASAP)

**Product:** AHA @ [dailyassist.xyz](https://www.dailyassist.xyz)  
**Scope:** Ship **Tier-1 only** — social posting, dev workspace, system tasks. **No BYOK / Tier-2 LLM.**  
**Philosophy:** `AHA_PHILOSOPHY.md` — assistant language only  
**Full launch later:** `LAUNCH100_PLAN.md` (Tier-2 + ops) after this ships

---

## What “Tier-1 launch” means

Paying users can **download**, **sign in**, get a **license**, and **ask in chat** for:

| Category | Examples |
|----------|----------|
| **Social** | Post on Instagram, Facebook, LinkedIn, X, WhatsApp status |
| **Dev** | Git push/status/commit, `.env.local`, SSH key, open project |
| **System** | Connect Bluetooth device, open folder |

**No AI key required.** Chat parses intent; execution is deterministic (`m9_social`, `m9_local`, `m9_native`).

General web tasks (“buy on Amazon”) return a **coming soon** message — not a broken Tier-2 path.

---

## Code switch (done in repo)

| Mechanism | Behavior |
|-----------|----------|
| `AHA_TIER1_ONLY=1` | Block Tier-2 LLM; hide BYOK in Settings; reject BYOK API writes |
| Retail PyInstaller build | Sets `AHA_TIER1_ONLY=1` via `packaging/aha_retail_hook.py` |
| Dev checkout | Tier-2 still available unless you export `AHA_TIER1_ONLY=1` |

Verify locally:

```bash
export AHA_TIER1_ONLY=1
python3 -m uvicorn server:app --host 127.0.0.1 --port 8000
# Open companion → Settings should hide API key section
# Chat: "buy shoes on amazon" → Tier-1 help message (not API key error)
```

---

## Launch checklist (ordered)

### A. Blocking — ship gate

- [ ] **Mac E2E** — subscribe (test or live Razorpay) → download retail zip → permissions → sign in → one social flow (e.g. IG status) → one local command (e.g. git status)
- [ ] **Build retail zip** — `./scripts/build_desktop_release.sh mac` → `scripts/verify_retail_zip.sh` passes
- [ ] **Upload zip** — Supabase `aha-releases` + Vercel `AHA_DOWNLOAD_MAC_URL` (Windows when built)
- [ ] **License path works** — Firebase sign-in → `/api/license/sync` → companion unlocks (test Razorpay OK for first cohort)

### B. Tier-1 quality (same week)

- [ ] **Vision preview** — social steps show non-blank preview in companion
- [ ] **Vault path doc** — one paragraph in `INSTALL.md`: which calendar folder beta users use

### C. Marketing / site (Tier-1 safe copy)

- [ ] Homepage + FAQ: **daily computer assistance** — post, dev workspace, system help on Mac/Windows
- [ ] **Do not** mention Tier 1/2, BYOK, vault/slots, or “automation” (`WEBSITE_DESIGN_BRIEF.md`)
- [ ] Pricing: one plan (₹2,999/mo) — “core assistance” without promising general web AI yet

### D. Explicitly deferred (post Tier-1 launch)

- Tier-2 BYOK + Keychain (`REINVENT_PLAN` Phase 1–2)
- Live Razorpay + prod Supabase hardening (`LAUNCH100_PLAN`)
- macOS notarization / Windows Authenticode (optional UX)
- `m9_atlas` / L2 accessibility indexer (`TIER1_LOCAL_PLAN.md`)

---

## Maintainer release steps

```bash
# 1. Build (macOS machine, Python 3.10+)
./scripts/build_desktop_release.sh mac

# 2. Verify no source leak
./scripts/verify_retail_zip.sh downloads/AHA-mac.zip

# 3. Upload to Supabase Storage → update Vercel env → redeploy

# 4. Smoke test paid download + first-run on a clean Mac
```

---

## Success criteria

1. New user completes **subscribe → download → install → sign in → one successful Tier-1 task** without founder help.
2. Non–Tier-1 asks get a clear **“coming soon”** message — never a Gemini/API-key error.
3. Settings show **Local Workspace + License** only (no API key fields in retail build).

---

*After Tier-1 launch is stable → use **Composer or Sonnet** for Tier-2 BYOK (`REINVENT_PLAN` Phase 1) before flipping `AHA_TIER1_ONLY` off in retail.*
