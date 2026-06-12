# AHA Agent Architecture — The Hybrid Approach

## THE CORE PHILOSOPHY

1. **Social Media Tasks (The "Gold Standard")**: 
   - Tasks like posting on Facebook, LinkedIn, X, Instagram, WhatsApp.
   - **Rule**: NO LLM CAPABILITIES USED. These must run 100% via hardcoded, deterministic flows (`m9_social`). 
   - **Why?**: Because the LLM was missing intermediate steps (like the Facebook "Next" button). Hardcoding these specific flows ensures perfect reliability.

2. **Other Websites and New Tasks**:
   - For any other website not covered by the gold standard flows.
   - **Rule**: The LLM *is* used to analyze the screen, understand the user's intent, and tell the agent *which button is correct to click*. 
   - **Execution**: The LLM does *not* do the physical clicking itself. It just provides the plan (e.g., "click the Submit button"). The agent (via PyAutoGUI/vision) performs the actual physical OS actions.

---

## How It Works in Practice (`agent.py`)

When the user says something:

1. **Check for Social Media Flow**: 
   `detect_flow(user_text)` checks if this is a known social media task.
   - If YES → Run the hardcoded `SocialFlowExecutor`. The LLM is bypassed entirely. The task completes deterministically.

2. **Fallback to LLM (for "other" websites)**:
   - If NO (e.g., "buy this item on amazon") → The LLM takes over. 
   - The LLM looks at the screenshot, figures out what steps are needed, and outputs a plan.
   - The agent framework then parses the LLM's plan and physically executes the clicks/typing using the vision libraries.

This gives us the best of both worlds: perfect reliability on the complex social media workflows, and flexible AI-driven automation for everything else.
