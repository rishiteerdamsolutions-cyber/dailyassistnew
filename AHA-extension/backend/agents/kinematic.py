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
    Duration formula: 200ms base + 2ms per pixel, ±15% jitter.
    Minimum: 100ms.
    """
    base = 200.0 + 2.0 * distance
    jitter_pct = (secrets.randbelow(31) - 15) / 100.0   # −0.15 → +0.15
    return max(base * (1.0 + jitter_pct), 100.0)


# ── Overshoot Engine ──────────────────────────────────────────────────────────

def _should_overshoot(distance: float) -> bool:
    """
    Logistic probability: 0.2 + 0.5*(1 − e^(−d/300)), capped at 0.8.
    → ~30% at 100px, ~50% at 300px, ~70% at 500px+
    """
    prob = min(0.2 + 0.5 * (1.0 - math.exp(-distance / 300.0)), 0.8)
    return secrets.randbelow(1000) / 1000.0 < prob


def _apply_overshoot(
    trajectory: list[tuple[float, float]],
    target_x: float,
    target_y: float,
) -> list[tuple[float, float]]:
    """
    Extend trajectory with damped spring correction after overshoot.

    1. Cursor overshoots target by 3–12px in approach direction.
    2. 1–3 damped oscillation corrections settle on exact target.
    """
    if len(trajectory) < 2:
        return trajectory

    result = list(trajectory)

    last = trajectory[-1]
    prev = trajectory[-2]
    dx = last[0] - prev[0]
    dy = last[1] - prev[1]
    speed = math.sqrt(dx * dx + dy * dy)

    if speed < 0.5:
        return result

    dir_x = dx / speed
    dir_y = dy / speed

    overshoot_base = 3 + secrets.randbelow(10)             # 3–12 px
    overshoot_scale = min(speed / 5.0, 2.0)
    overshoot_dist = overshoot_base * max(overshoot_scale, 0.5)

    overshoot_pt = (
        target_x + dir_x * overshoot_dist,
        target_y + dir_y * overshoot_dist,
    )
    result.append(overshoot_pt)

    num_corrections = 1 + secrets.randbelow(3)
    zeta = 0.5 + secrets.randbelow(31) / 100.0             # 0.5–0.8 damping
    omega = 2.0 * math.pi / 4.0

    current = overshoot_pt
    for i in range(1, num_corrections + 1):
        t = float(i) / (num_corrections + 1)
        decay = math.exp(-zeta * omega * t)
        oscillation = math.cos(omega * t)

        cx = target_x + (current[0] - target_x) * decay * oscillation * 0.3
        cy = target_y + (current[1] - target_y) * decay * oscillation * 0.3
        result.append((cx, cy))
        current = (cx, cy)

    result.append((target_x, target_y))
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
        .includes_overshoot
    """
    # Off-centre click randomisation within 80% of the bounding box interior
    margin_x = target_w * 0.10
    margin_y = target_h * 0.10
    inner_w = max(target_w - 2 * margin_x, 1.0)
    inner_h = max(target_h - 2 * margin_y, 1.0)

    click_x = target_x + margin_x + _rand_float(0.0, inner_w)
    click_y = target_y + margin_y + _rand_float(0.0, inner_h)

    distance = math.sqrt((click_x - start_x) ** 2 + (click_y - start_y) ** 2)
    duration_ms = _calculate_duration_ms(distance)

    # More steps for longer distances; minimum 30
    num_steps = max(int(distance / 8), 30)
    path = _generate_cubic_bezier(start_x, start_y, click_x, click_y, num_steps)

    includes_overshoot = False
    if _should_overshoot(distance):
        path = _apply_overshoot(path, click_x, click_y)
        includes_overshoot = True

    return TrajectoryResult(
        path=path,
        total_duration_ms=duration_ms,
        includes_overshoot=includes_overshoot,
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
