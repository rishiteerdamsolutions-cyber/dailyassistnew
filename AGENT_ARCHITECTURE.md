# AHA Agent Architecture — The Hybrid Approach

> **Product philosophy & branding:** see `AHA_PHILOSOPHY.md` (single source of truth). This file covers technical routing only.

## THE CORE PHILOSOPHY

1. **Tier-1 Local Precision (Mac + Windows)**:
   - **Social posting** (Facebook, LinkedIn, X, Instagram, WhatsApp) via `m9_social` + `VISIONBUTTONS/`.
   - **Dev & OS** (git push, `.env.local`, SSH, Bluetooth, open project) via `m9_local` + `m9_native`.
   - **Rule**: NO LLM for execution. Hardcoded deterministic flows only.
   - **Why?**: LLMs miss intermediate steps; native + vision flows ensure reliability.

2. **Tier-2 — Other websites and novel tasks**:
   - For any other website not covered by the gold standard flows.
   - **Rule**: The LLM *is* used to analyze the screen, understand the user's intent, and tell the agent *which button is correct to click*. 
   - **Execution**: The LLM does *not* do the physical clicking itself. It just provides the plan (e.g., "click the Submit button"). The agent (via PyAutoGUI/vision) performs the actual physical OS actions.

---

## How It Works in Practice (`agent.py`)

When the user says something:

1. **Check for Tier-1 local task** (`m9_local` — git, env, Bluetooth, projects):
   - If YES → Run `run_local_task`. LLM bypassed.

2. **Check for Tier-1 social flow** (`m9_social`):
   - If YES → Run `SocialFlowExecutor`. LLM bypassed.

3. **Fallback to Tier-2 LLM** (for "other" websites):
   - If NO (e.g., "buy this item on amazon") → The LLM takes over. 
   - The LLM looks at the screenshot, figures out what steps are needed, and outputs a plan.
   - The agent framework then parses the LLM's plan and physically executes the clicks/typing using the vision libraries.

This gives us the best of both worlds: perfect reliability on the complex social media workflows, and flexible AI-assisted computer use for everything else (Tier 2).
