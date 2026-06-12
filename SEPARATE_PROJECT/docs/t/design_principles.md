# Typing (Linguistic) Agent Design Principles

The Linguistic Agent is designed to completely evade bot-detection systems by mimicking human typing behavior at a statistical level, rather than relying on pure randomness.

## Core Mechanisms

### 1. The Beta Distribution (Not Bell Curve)
Human reaction times do not follow a standard bell curve (Normal Distribution) or uniform randomness. We have a physical "floor" (a minimum time it takes to move a finger), but occasionally we pause for a long time to think or scratch our nose. The agent mathematically models this exact long-tailed curve using a Beta distribution to generate initial delays.

### 2. The Depletion Pool
Instead of generating a random number for every keystroke on the fly, the agent generates a massive pool of delays (e.g., 500 delays) based on the Beta distribution. When it types a character, it pulls a delay from the pool *without replacement*. Once drawn, the exact millisecond delay is deleted from the pool. This guarantees that **no two keystrokes will ever have the exact same millisecond delay** during a session.

### 3. Fatigue Drift
As a paragraph gets longer, human typing speed naturally decreases due to physical and mental fatigue. The agent models this by slowly drifting the baseline milliseconds upwards. A session that starts at 60 WPM might naturally drift down to 52 WPM by the end of a long paragraph.

### 4. Context-Aware Delays
The algorithm understands the physical geometry of a QWERTY keyboard. It knows that hitting the `Spacebar` or reaching for the `Shift` key (for capital letters and punctuation) physically takes a human longer. Therefore, it applies mathematical multipliers to the delays for these specific, harder-to-reach keys.

### 5. QWERTY-Adjacent Typo Correction
Humans make mistakes. The agent will purposefully (based on an error rate) inject a typo by selecting a key physically adjacent to the target key on a QWERTY keyboard (e.g., typing 's' instead of 'a'). It then simulates the human realization of the error, pauses, hits the `Backspace` key, and types the correct letter.
