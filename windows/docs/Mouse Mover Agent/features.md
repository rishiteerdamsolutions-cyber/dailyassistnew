# Kinematic Agent (Mouse Mover) Features

The Kinematic Agent is responsible for translating logical destination coordinates into physical OS-level mouse movements that are mathematically indistinguishable from a human hand. 

It accomplishes this through the following advanced HCI (Human-Computer Interaction) features:

## 1. Cubic Bezier Arcs
Humans do not move mice in straight, robotic lines. Because human hands pivot from fixed biological joints (the wrist or elbow), the agent uses mathematical Cubic Bezier curves to generate natural, swooping arcs for every movement.

## 2. Velocity Easing (Fitts's Law)
The agent dynamically calculates acceleration and deceleration. It moves extremely fast across the empty center of the screen, but physically slows the cursor down as it approaches the target, mimicking a human carefully aiming at a button.

## 3. Off-Center Clicking (Sloppy Aim)
When given the bounding box (width and height) of a target button, the agent calculates a randomized internal offset. It ensures that it *never* clicks the exact, absolute center of a button, mimicking natural human variance.

## 4. Segmented Journeys (Think-and-Move)
If a destination is far away, the agent will not perform a single continuous movement. It calculates a "waypoint" somewhere in the middle, glides to it, physically stops for 150-450 milliseconds (simulating a human pausing to scan the screen with their eyes), and then generates a new trajectory.

## 5. Pre-Target Wobble (Micro-Correction)
When approaching a small target, the agent intentionally aims its trajectory for a coordinate slightly *outside* the button (e.g., 30 pixels above it). It glides to this offset, pauses briefly as it realizes the error, and snaps a final micro-adjustment directly onto the target.

## 6. Hesitation Looping (Lost Cursor Effect)
Humans frequently lose track of where their cursor is on large monitors, resulting in a rapid, circular wiggle to locate it visually. The agent has a 20% randomized chance to inject a chaotic, circular trajectory right at the start of a journey before moving to the target.

## 7. Spring-Damped Overshoot
When moving very quickly, the agent occasionally overshoots its target by a few pixels, simulating physical momentum, before sharply snapping back in the opposite direction.
