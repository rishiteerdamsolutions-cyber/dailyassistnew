# Tier-1 Local Expansion — Implementation Tracker

**Product:** AHA @ dailyassist.xyz  
**Scope:** Complete local computer use on **macOS + Windows** (deterministic, no LLM execution)

---

## Architecture

| Module | Role |
|--------|------|
| `m9_router` | Routes chat → local vs social Tier-1 |
| `m9_local` | Local flow parser + executor |
| `m9_native` | Allowlisted subprocess (git, env, BT, open folder) |
| `m9_social` | Browser social flows (existing) |
| `aha/local_registry.py` | Projects + SSH keys in `~/.aha/` |

---

## Phase L0 — Foundation ✅

- [x] `aha/local_registry.py` — projects, SSH key generation
- [x] `bol/modules/m9_native/runner.py` — allowlisted commands (Mac + Win)
- [x] `bol/modules/m9_local/` — parser, flows, executor
- [x] `bol/modules/m9_router/` — unified Tier-1 detection
- [x] `agent.py` — local tasks before social; LLM blocked on failure
- [x] API: `/api/local/projects`, `/api/local/ssh`
- [x] Companion Settings → Local Workspace UI
- [x] Tests: `tests/test_tier1_local.py`

### L0 chat commands

| Say | Action |
|-----|--------|
| Push {project} to git | `git push` (registered project) |
| Git status for {project} | `git status` |
| Commit with message "…" | `git commit -am` |
| Create .env.local | Scaffold from `.env.example` |
| Generate ssh key | `ssh-keygen` in `~/.aha/keys/` |
| Connect to Noise Buds | Bluetooth (blueutil Mac / settings fallback) |
| Open project {name} | Finder / Explorer (+ Cursor/VS Code optional) |

---

## Phase L1 — OS essentials (next)

- [ ] `VISIONBUTTONS/os/mac/` — menu bar, System Settings
- [ ] `VISIONBUTTONS/os/win/` — taskbar, Settings
- [ ] Vision fallback in `m9_local` when native BT fails
- [ ] Wi‑Fi, volume, displays flows

## Phase L2 — Accessibility atlas

- [ ] macOS AX indexer → `bol/atlas/mac/`
- [ ] Windows UIA indexer → `bol/atlas/win/`
- [ ] `m9_atlas.resolve_intent()`

---

*After L0 → use **Composer or Codex** for L1 OS templates. After L1 → **Sonnet or Opus (thinking)** for L2 AX/UIA.*
