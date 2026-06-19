"""
agents/kinematic.py — Bezier + overshoot trajectory engine.

Ported from:
  bol/modules/m2_kinematic/bezier.py
  bol/modules/m2_kinematic/overshoot.py
  bol/modules/m2_kinematic/scroll.py

Fully self-contained — no bol.* imports.

Public API
----------
generate_mouse_path(start_x, start_y, target_x, target_y, target_w, target_h)
    → TrajectoryResult(path: list[tuple[float,float]], total_duration_ms: float)

generate_scroll_profile(distance_px, direction)
    → ScrollResult(steps: list[ScrollStep], total_duration_ms: float)
"""

from __future__ import annotations

import math
import secrets
from dataclasses import dataclass, field


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class TrajectoryResult:
    """Output of generate_mouse_path."""
    path: list[tuple[float, float]]       # List of (x, y) coordinate pairs
    total_duration_ms: float
    includes_overshoot: bool = False


@dataclass
class ScrollStep:
    """A single discrete scroll step."""
    delta_px: int                          # Pixels to scroll in this step
    delay_ms: float                        # Delay before issuing this step
    is_stutter: bool = False               # True if this is a micro-stutter pause


@dataclass
class ScrollResult:
    """Output of generate_scroll_profile."""
    direction: str                         # "up" or "down"
    steps: list[ScrollStep]
    total_duration_ms: float


# ── Internal helpers ─────────────────────────────────────────────────────────

def _rand_offset(distance: float) -> float:
    """Perpendicular offset: ±15–40% of direct distance."""
    pct = 15 + secrets.randbelow(26)       # 15–40
    sign = 1 if secrets.randbelow(2) == 0 else -1
    return sign * distance * (pct / 100.0)


def _rand_float(lo: float, hi: float) -> float:
    """Uniform float in [lo, hi] via secrets int resolution."""
    resolution = 10_000
    return lo + (secrets.randbelow(resolution + 1) / resolution) * (hi - lo)


# ── Bezier Engine ─────────────────────────────────────────────────────────────

def _generate_cubic_bezier(
    sx: float, sy: float,
    ex: float, ey: float,
    num_steps: int = 80,
) -> list[tuple[float, float]]:
    """
    Sample a cubic Bezier curve from (sx, sy) to (ex, ey).

    Control points are randomised perpendicular to the straight-line path
    (15–40% of total distance) so every path looks organically curved.

    Time parameterization: ease-out  t_mapped = 1 - (1-t)²
    This produces a fast start with deceleration near the target.
    """
    dx = ex - sx
    dy = ey - sy
    distance = math.sqrt(dx * dx + dy * dy)

    if distance < 1.0:
        return [(ex, ey)]

    # Perpendicular unit vector
    perp_x = -dy / distance
    perp_y = dx / distance

    offset1 = _rand_offset(distance)
    offset2 = _rand_offset(distance)

    t1 = _rand_float(0.25, 0.35)
    t2 = _rand_float(0.65, 0.75)

    p0 = (sx, sy)
    p1 = (sx + dx * t1 + perp_x * offset1, sy + dy * t1 + perp_y * offset1)
    p2 = (sx + dx * t2 + perp_x * offset2, sy + dy * t2 + perp_y * offset2)
    p3 = (ex, ey)

    points: list[tuple[float, float]] = []
    for i in range(num_steps):
        t_lin = i / (num_steps - 1) if num_steps > 1 else 1.0
        t = 1.0 - (1.0 - t_lin) ** 2          # ease-out mapping

        mt = 1.0 - t
        x = (
            mt ** 3 * p0[0]
            + 3 * mt ** 2 * t * p1[0]
            + 3 * mt * t ** 2 * p2[0]
            + t ** 3 * p3[0]
        )
        y = (
            mt ** 3 * p0[1]
            + 3 * mt ** 2 * t * p1[1]
            + 3 * mt * t ** 2 * p2[1]
            + t ** 3 * p3[1]
        )
        points.append((x, y))

    return points


def _calculate_duration_ms(distance: float) -> float:
    """
    Duration formula: 600ms base + 2.5ms per pixel, ±20% jitter.
    A full screen movement (1000px) will take ~2.5s - 3.8s.
    Minimum: 500ms.
    """
    base = 600.0 + 2.5 * distance
    jitter_pct = (secrets.randbelow(41) - 20) / 100.0   # −0.20 → +0.20
    return max(base * (1.0 + jitter_pct), 500.0)


# ── Overshoot Engine ──────────────────────────────────────────────────────────

def _should_overshoot(distance: float) -> bool:
    """
    Logistic probability: 0.2 + 0.5*(1 − e^(−d/300)), capped at 0.8.
    → ~30% at 100px, ~50% at 300px, ~70% at 500px+
    """
    prob = min(0.2 + 0.5 * (1.0 - math.exp(-distance / 300.0)), 0.8)
    return secrets.randbelow(1000) / 1000.0 < prob


def _apply_human_hesitations(
    trajectory: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """
    Injects realistic 'installments' into the path by forcing the cursor to hover 
    at certain points, creating natural hesitations.
    """
    if len(trajectory) < 10:
        return trajectory
        
    result = []
    # Pick 1-2 random points in the path to hesitate at
    num_hesitations = 1 + secrets.randbelow(2)
    hesitation_indices = set()
    for _ in range(num_hesitations):
        # Hesitate somewhere in the middle 60% of the movement
        idx = int(len(trajectory) * _rand_float(0.2, 0.8))
        hesitation_indices.add(idx)

    for i, pt in enumerate(trajectory):
        result.append(pt)
        if i in hesitation_indices:
            # Repeat the coordinate 20-40 times. At ~10ms per step, this is a 200-400ms pause.
            pause_frames = 20 + secrets.randbelow(21)
            for _ in range(pause_frames):
                result.append(pt)
                
    return result

def _apply_nearby_stop_and_correct(
    trajectory: list[tuple[float, float]],
    target_x: float,
    target_y: float,
) -> list[tuple[float, float]]:
    """
    Simulates a human stopping just short of the target ("nearby"), hesitating, 
    and then carefully closing the final distance.
    """
    if len(trajectory) < 2:
        return trajectory

    result = list(trajectory)
    
    # Pause near the end
    pause_frames = 15 + secrets.randbelow(15)
    last_pt = result[-1]
    for _ in range(pause_frames):
        result.append(last_pt)
        
    # Micro-correction to the exact final target
    # Generate a slow, short straight line or slight curve to the exact target
    dx = target_x - last_pt[0]
    dy = target_y - last_pt[1]
    dist = math.sqrt(dx*dx + dy*dy)
    
    # 5 to 15 frames for the final correction
    correction_steps = 5 + secrets.randbelow(11)
    for i in range(1, correction_steps + 1):
        t = i / float(correction_steps)
        # ease-out
        t = 1.0 - (1.0 - t) * (1.0 - t)
        result.append((
            last_pt[0] + dx * t,
            last_pt[1] + dy * t
        ))

    return result


# ── Public API ────────────────────────────────────────────────────────────────

def generate_mouse_path(
    start_x: float,
    start_y: float,
    target_x: float,
    target_y: float,
    target_w: float,
    target_h: float,
) -> TrajectoryResult:
    """
    Generate a human-like Bezier mouse trajectory from current cursor
    position to a random off-centre point within the target bounding box.

    Parameters
    ----------
    start_x, start_y    Current cursor position (pixels).
    target_x, target_y  Top-left corner of target element (pixels).
    target_w, target_h  Width and height of target element (pixels).

    Returns
    -------
    TrajectoryResult
        .path              — ordered list of (x, y) float tuples
        .total_duration_ms — realistic movement duration
    """
    # Guarantee we NEVER click the mathematical center
    # Split the target into 4 quadrants, pick a random quadrant, and pick a point strictly inside it
    # leaving a dead-zone in the exact middle.
    mid_x = target_x + target_w / 2.0
    mid_y = target_y + target_h / 2.0
    
    quadrant_x = 1 if secrets.randbelow(2) == 0 else -1
    quadrant_y = 1 if secrets.randbelow(2) == 0 else -1
    
    # Minimum offset from center is 10% of width/height, max is 40% (keeping away from extreme edge)
    offset_x = (target_w / 2.0) * _rand_float(0.1, 0.4) * quadrant_x
    offset_y = (target_h / 2.0) * _rand_float(0.1, 0.4) * quadrant_y
    
    click_x = mid_x + offset_x
    click_y = mid_y + offset_y

    distance = math.sqrt((click_x - start_x) ** 2 + (click_y - start_y) ** 2)
    duration_ms = _calculate_duration_ms(distance)

    # 1. We stop "nearby" instead of going all the way to click_x, click_y immediately.
    # We aim for a point 10-30 pixels away from the final target
    approach_angle = math.atan2(click_y - start_y, click_x - start_x)
    stop_short_dist = _rand_float(10.0, 30.0)
    
    # If the total distance is tiny, don't stop short
    if distance > 40.0:
        nearby_x = click_x - math.cos(approach_angle) * stop_short_dist
        nearby_y = click_y - math.sin(approach_angle) * stop_short_dist
    else:
        nearby_x, nearby_y = click_x, click_y

    num_steps = max(int(distance / 8), 30)
    
    # Generate the main fast curve to the "nearby" point
    path = _generate_cubic_bezier(start_x, start_y, nearby_x, nearby_y, num_steps)
    
    # 2. Add "installments" (hesitations mid-flight)
    path = _apply_human_hesitations(path)
    
    # 3. Stop nearby, hesitate, and do the final micro-correction to the real target
    if distance > 40.0:
        path = _apply_nearby_stop_and_correct(path, click_x, click_y)
    else:
        path.append((click_x, click_y))

    return TrajectoryResult(
        path=path,
        total_duration_ms=duration_ms,
        includes_overshoot=True
    )


# ── Scroll Profile ─────────────────────────────────────────────────────────────

def _sinusoidal_delays(num_steps: int, base_delay_ms: float) -> list[float]:
    """
    Velocity profile: v(t) = sin²(πt).
    Delay ∝ 1/velocity — slow at edges, fast in the middle.
    """
    delays: list[float] = []
    for i in range(num_steps):
        t = (i + 0.5) / num_steps
        velocity = max(math.sin(math.pi * t) ** 2, 0.1)
        delay = base_delay_ms / velocity
        jitter = 1.0 + (secrets.randbelow(21) - 10) / 100.0   # ±10%
        delays.append(round(delay * jitter, 2))
    return delays


def generate_scroll_profile(distance_px: int, direction: str = "down") -> ScrollResult:
    """
    Generate a sinusoidal scroll profile with micro-stutter reading pauses.

    Parameters
    ----------
    distance_px   Total pixels to scroll.
    direction     "up" or "down".

    Returns
    -------
    ScrollResult
        .steps            — list of ScrollStep (delta_px + delay_ms)
        .total_duration_ms
    """
    if distance_px <= 0:
        return ScrollResult(direction=direction, steps=[], total_duration_ms=0.0)

    step_size = 15 + secrets.randbelow(11)                    # 15–25 px per step
    num_steps = max(distance_px // step_size, 3)
    base_delay_ms = 30.0 + secrets.randbelow(21)              # 30–50 ms base

    step_delays = _sinusoidal_delays(num_steps, base_delay_ms)
    stutter_prob = 0.15 + secrets.randbelow(11) / 100.0       # 15–25%

    steps: list[ScrollStep] = []
    total_duration = 0.0
    px_per_step = distance_px // num_steps

    for i, delay in enumerate(step_delays):
        steps.append(ScrollStep(delta_px=px_per_step, delay_ms=delay))
        total_duration += delay

        if secrets.randbelow(1000) / 1000.0 < stutter_prob:
            pause_ms = float(50 + secrets.randbelow(251))     # 50–300 ms
            steps.append(ScrollStep(delta_px=0, delay_ms=pause_ms, is_stutter=True))
            total_duration += pause_ms

    return ScrollResult(
        direction=direction,
        steps=steps,
        total_duration_ms=round(total_duration, 2),
    )
