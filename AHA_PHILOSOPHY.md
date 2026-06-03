# AHA Philosophy — Single Source of Truth

**Product:** Artificial Human Assistant (**AHA**)  
**Site:** [www.dailyassist.xyz](https://www.dailyassist.xyz)  
**Tagline concept:** Your agent assists you daily on X, Y, Z — anything on your computer.

---

## Brand & Language (Non-Negotiable)

- Always **assistant**, never **automation**.
- Do not describe the product as “automating social media” or “automation software.”
- Users come to **chat** and **ask** (e.g. “post this”); the agent **assists** and carries out the task.
- Position AHA alongside computer-use products (Claude computer use, OpenAI Operator, Google Copilot) — same category, different architecture and cost.

---

## What AHA Is

AHA is a **desktop assistant** that uses your computer like a human: vision on the screen, physical mouse and keyboard, human-like timing and motion. It has **no DOM/backend access** — only what a person would see and click.

---

## Two Tiers

### Tier 1 — Social posting (no AI for execution)

- **Hardcoded flows** with template images (`VISIONBUTTONS/`) so agents know where to click on Facebook, LinkedIn, Instagram, X, and WhatsApp status.
- **No LLM** for these tasks — only chat that **understands intent** (e.g. user asks to post; agent posts).
- **Content Vault:** slots, folders, and calendar setup for planned content used when posting.
- **Module:** `m9_social` (deterministic state machines), coordinated by `m8_orchestrator`.

### Tier 2 — Everything else (BYOK AI)

- User saves API keys in **Companion app → Settings → Chat**.
- When the user asks for tasks **outside** Tier 1 social flows (e.g. “buy something on Amazon”):
  - **Easy tasks:** agent sends a **string of words** (screen text/context); AI returns which button to click; agents click.
  - **Hard tasks:** agent sends a **screenshot**; AI returns which button to click; agents click.
- Goal: **~10× cheaper** than Claude-style computer use while **comparable quality** for general computer assistance.
- AI **plans**; agents **execute** physically via vision + bridge (never “the model clicks” directly).

---

## Agent Ecosystem (10 Modules + m9 Family)

All modules live under `bol/modules/` and are coordinated by **m8_orchestrator**.

| Module | Name | Role |
|--------|------|------|
| **m8** | Orchestrator | Master controller: routes Tier 1 vs Tier 2, commands all other modules |
| **m3** | Visual Cortex | Screenshots, OCR, template matching — “sees” like a human eye |
| **m6** | Native OS Bridge | Physical mouse/keyboard via OS (PyAutoGUI, etc.) |
| **m2** | Kinematic Motion | Bezier curves, overshoot, micro-corrections — not teleport clicks |
| **m1** | Chrono-Entropy | Human timing pools — not fixed robotic intervals |
| **m5** | Linguistic Variance | Fatigue, variable speed, realistic typos + backspace |
| **m4** | Behavioral Policy | Markov “personality”: pauses, distraction, idle scroll |
| **m7** | Lifecycle Controller | Chrome profiles, session isolation for social accounts |
| **m9_social** | Social Flow Executor | Deterministic posting flows (Tier 1) |
| **m9_generator** | Content formatting | Captions and text formatting logic |
| **m9_parser** | UI state parsing | Parses screen text to understand UI state |
| **m10** | Background Scheduler | Watches Content Vault calendar; wakes orchestrator for **scheduled** posts |

### Request flow (every instruction)

1. **m8** receives the command from chat.
2. **m3** looks at the screen.
3. **m8** decides route: Tier 1 social flow vs Tier 2 LLM plan.
4. **m2** + **m1** shape motion and delays; **m5** for typing; **m4** for behavioral realism.
5. **m6** performs physical OS actions.

---

## Related Docs

- Implementation detail for Tier 1 vs Tier 2 routing: `AGENT_ARCHITECTURE.md` (must stay aligned with this file; this file wins on product language and positioning).
