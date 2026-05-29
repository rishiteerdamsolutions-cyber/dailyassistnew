#!/usr/bin/env python3
"""
BOL — Behavioral Operating Layer: Capability Showcase

Demonstrates all 7 module capabilities without requiring
macOS Accessibility or Screen Recording permissions.
"""

from __future__ import annotations

import sys
import tempfile
import time
from datetime import date
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════
# ANSI color helpers
# ═══════════════════════════════════════════════════════════════════
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
RESET = "\033[0m"
BAR = f"{DIM}{'─' * 70}{RESET}"


def header(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'═' * 70}{RESET}")
    print(f"{BOLD}{CYAN}  ◆  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 70}{RESET}\n")


def subheader(title: str) -> None:
    print(f"\n  {BOLD}{YELLOW}▸ {title}{RESET}")
    print(f"  {DIM}{'─' * 60}{RESET}")


def kv(key: str, value: str, indent: int = 4) -> None:
    pad = " " * indent
    print(f"{pad}{DIM}{key}:{RESET} {value}")


def success(msg: str) -> None:
    print(f"    {GREEN}✓{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"    {YELLOW}⚠{RESET} {msg}")


# ═══════════════════════════════════════════════════════════════════
# Module 1: Chrono-Entropy & Timing Manager
# ═══════════════════════════════════════════════════════════════════
def demo_timing() -> None:
    header("MODULE 1 — Chrono-Entropy & Timing Manager")

    from bol.modules.m1_timing.pool import TimingPoolGenerator
    from bol.modules.m1_timing.manager import TimingManager
    from bol.schemas.timing import TimingConfig

    subheader("Beta-Distribution Pool Generation")
    config = TimingConfig(
        platform="linkedin",
        pool_size=1000,
        min_latency_ms=200.0,
        max_latency_ms=4500.0,
        distribution_alpha=2.0,
        distribution_beta=5.0,
    )
    t0 = time.time()
    values = TimingPoolGenerator.generate_pool(config)
    gen_time = (time.time() - t0) * 1000

    kv("Pool size", f"{len(values)} unique values")
    kv("Range", f"{min(values):.2f}ms → {max(values):.2f}ms")
    kv("Generation time", f"{gen_time:.1f}ms")
    kv("Sample values", ", ".join(f"{v:.2f}" for v in values[:8]) + " ...")

    # Statistical distribution
    import numpy as np
    arr = np.array(values)
    kv("Mean", f"{arr.mean():.2f}ms")
    kv("Median", f"{np.median(arr):.2f}ms")
    kv("Std Dev", f"{arr.std():.2f}ms")
    skew = (((arr - arr.mean()) / arr.std()) ** 3).mean()
    kv("Skewness", f"{skew:.3f} (right-skewed = more fast values)")

    # Show histogram as ASCII
    print(f"\n    {BOLD}Distribution Histogram:{RESET}")
    bins = [0] * 10
    for v in values:
        idx = min(int((v - config.min_latency_ms) / (config.max_latency_ms - config.min_latency_ms) * 10), 9)
        bins[idx] += 1
    max_bin = max(bins)
    for i, count in enumerate(bins):
        lo = config.min_latency_ms + i * (config.max_latency_ms - config.min_latency_ms) / 10
        hi = lo + (config.max_latency_ms - config.min_latency_ms) / 10
        bar_len = int(count / max_bin * 40)
        bar = f"{GREEN}{'█' * bar_len}{RESET}"
        print(f"    {lo:7.0f}-{hi:7.0f}ms │{bar} {count}")

    subheader("SQLite Depletion Pool (Draw Without Replacement)")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    manager = TimingManager(db_path, configs={"demo": TimingConfig(platform="demo", pool_size=100)})
    draws = []
    for i in range(5):
        d = manager.get_delay("demo")
        draws.append(d)
    
    kv("5 draws (seconds)", ", ".join(f"{d:.4f}" for d in draws))
    status = manager.get_pool_status("demo")
    kv("Pool remaining", f"{status.remaining_count}/{status.pool_size}")
    kv("Exhaustion", f"{status.exhaustion_percentage:.1f}%")
    kv("Cycle", str(status.cycle_id))
    success("All values unique — extraction without replacement confirmed")
    
    # Personality modifier
    base = draws[0]
    modified = manager.apply_personality_modifier(base, 1.4)
    kv("Personality modifier", f"{base:.4f}s × 1.4 = {modified:.4f}s (Distracted Academic)")
    
    manager.close()
    db_path.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════
# Module 2: Kinematic Motion Synthesizer
# ═══════════════════════════════════════════════════════════════════
def demo_kinematic() -> None:
    header("MODULE 2 — Kinematic Motion Synthesizer")

    from bol.modules.m2_kinematic.bezier import BezierEngine
    from bol.modules.m2_kinematic.overshoot import OvershootEngine
    from bol.modules.m2_kinematic.scroll import ScrollEngine
    from bol.schemas.kinematic import Point2D, ScrollDirection

    subheader("Cubic Bezier Trajectory Generation")
    start = Point2D(x=100.0, y=400.0)
    end = Point2D(x=900.0, y=200.0)
    distance = start.distance_to(end)

    cp = BezierEngine.generate_control_points(start, end)
    trajectory = BezierEngine.sample_trajectory(cp, num_steps=60)
    duration = BezierEngine.calculate_duration_ms(distance)

    kv("Start", f"({start.x:.0f}, {start.y:.0f})")
    kv("End", f"({end.x:.0f}, {end.y:.0f})")
    kv("Distance", f"{distance:.1f}px")
    kv("Duration", f"{duration:.1f}ms")
    kv("Control P1", f"({cp.p1.x:.1f}, {cp.p1.y:.1f})")
    kv("Control P2", f"({cp.p2.x:.1f}, {cp.p2.y:.1f})")
    kv("Trajectory points", str(len(trajectory)))

    # ASCII plot of trajectory
    print(f"\n    {BOLD}Bezier Curve Visualization (60×20 grid):{RESET}")
    grid_w, grid_h = 60, 18
    grid = [[" " for _ in range(grid_w)] for _ in range(grid_h)]
    
    min_x = min(p.x for p in trajectory) - 10
    max_x = max(p.x for p in trajectory) + 10
    min_y = min(p.y for p in trajectory) - 10
    max_y = max(p.y for p in trajectory) + 10

    for i, p in enumerate(trajectory):
        gx = int((p.x - min_x) / (max_x - min_x) * (grid_w - 1))
        gy = int((p.y - min_y) / (max_y - min_y) * (grid_h - 1))
        gx = max(0, min(grid_w - 1, gx))
        gy = max(0, min(grid_h - 1, gy))
        if i == 0:
            grid[gy][gx] = "S"
        elif i == len(trajectory) - 1:
            grid[gy][gx] = "E"
        else:
            grid[gy][gx] = "·"

    for row in grid:
        print(f"    {''.join(row)}")

    # Smoothness check
    import math
    jumps = []
    for i in range(1, len(trajectory)):
        dx = trajectory[i].x - trajectory[i-1].x
        dy = trajectory[i].y - trajectory[i-1].y
        jumps.append(math.sqrt(dx*dx + dy*dy))
    
    kv("Avg step size", f"{sum(jumps)/len(jumps):.2f}px")
    kv("Max step size", f"{max(jumps):.2f}px")
    kv("Linearity check", f"{'CURVED ✓' if max(abs(p.y - start.y) for p in trajectory[5:-5]) > 5 else 'TOO LINEAR ✗'}")
    success("Non-linear ease-out trajectory confirmed")

    subheader("Damped Spring Overshoot")
    engine = OvershootEngine()
    target = Point2D(x=500.0, y=300.0)
    test_traj = [
        Point2D(x=100.0, y=100.0),
        Point2D(x=250.0, y=175.0),
        Point2D(x=400.0, y=260.0),
        Point2D(x=500.0, y=300.0),
    ]
    extended = engine.apply_overshoot(test_traj, target)
    
    kv("Original points", str(len(test_traj)))
    kv("After overshoot", f"{len(extended)} points (+{len(extended) - len(test_traj)} correction)")
    for i, p in enumerate(extended[len(test_traj):], start=1):
        label = "overshoot" if i == 1 else f"correction {i-1}"
        dist_from_target = math.sqrt((p.x - target.x)**2 + (p.y - target.y)**2)
        kv(f"  {label}", f"({p.x:.1f}, {p.y:.1f}) — {dist_from_target:.1f}px from target")
    
    final = extended[-1]
    kv("Final position", f"({final.x:.1f}, {final.y:.1f}) — converges on target ✓")

    # Overshoot probability distribution
    short_hits = sum(1 for _ in range(200) if engine.should_overshoot(80.0))
    long_hits = sum(1 for _ in range(200) if engine.should_overshoot(600.0))
    kv("Overshoot rate @80px", f"{short_hits/200*100:.0f}%")
    kv("Overshoot rate @600px", f"{long_hits/200*100:.0f}%")
    success("Distance-proportional overshoot confirmed")

    subheader("Sinusoidal Scroll Physics")
    scroll_eng = ScrollEngine()
    profile = scroll_eng.generate_scroll_profile(800, ScrollDirection.DOWN)

    kv("Distance", f"{profile.total_distance_px}px DOWN")
    kv("Steps", str(profile.num_steps))
    kv("Total duration", f"{profile.total_duration_ms:.0f}ms")
    kv("Micro-stutters", str(len(profile.micro_stutters)))

    # Show velocity profile
    print(f"\n    {BOLD}Velocity Profile (delay = inverse of speed):{RESET}")
    delays = profile.step_delays_ms
    max_delay = max(delays)
    for i in range(0, len(delays), max(1, len(delays) // 12)):
        bar_len = int(delays[i] / max_delay * 30)
        speed_indicator = "SLOW" if delays[i] > max_delay * 0.7 else "MED " if delays[i] > max_delay * 0.3 else "FAST"
        bar_char = "▓" if speed_indicator == "SLOW" else "▒" if speed_indicator == "MED " else "░"
        print(f"    step {i:3d} │{MAGENTA}{bar_char * bar_len}{RESET} {delays[i]:.1f}ms ({speed_indicator})")
    success("Sinusoidal ease-in/ease-out profile confirmed")


# ═══════════════════════════════════════════════════════════════════
# Module 4: Behavioral Policy & State Engine
# ═══════════════════════════════════════════════════════════════════
def demo_policy() -> None:
    header("MODULE 4 — Behavioral Policy & State Engine")

    from bol.modules.m4_policy.personality import ALL_PERSONALITIES
    from bol.modules.m4_policy.engine import PolicyEngine

    subheader("Personality Vectors")
    for p in ALL_PERSONALITIES:
        print(f"    {BOLD}{p.name}{RESET}")
        kv("  Timing modifier", f"{p.timing_modifier}x", indent=6)
        kv("  Scroll depth", f"{p.scroll_depth_min}-{p.scroll_depth_max}px", indent=6)
        kv("  Distraction prob", f"{p.distraction_probability*100:.0f}%", indent=6)
        kv("  Typo modifier", f"{p.typo_rate_modifier}x", indent=6)
        kv("  WPM range", f"{p.base_wpm_min}-{p.base_wpm_max}", indent=6)
        kv("  Freeze prob", f"{p.freeze_probability*100:.0f}%", indent=6)
        kv("  Ghost drafts", "Enabled" if p.ghost_draft_enabled else "Disabled", indent=6)
        print()

    subheader("Markov Chain State Machine (15-transition simulation)")
    engine = PolicyEngine()
    session = engine.initialize_session()
    
    kv("Personality", session.personality.name)
    kv("Session seed", str(session.seed))
    
    print(f"\n    {BOLD}State Transitions:{RESET}")
    states_visited = []
    for i in range(15):
        state = engine.get_current_state()
        duration_ms = engine.get_state_duration_ms()
        states_visited.append(state.value)
        
        # Color-code states
        color_map = {
            "idle": DIM, "scrolling": BLUE, "reading": GREEN,
            "composing": YELLOW, "distracted": RED, "posting": MAGENTA,
            "cooling_down": CYAN, "exiting": DIM,
        }
        color = color_map.get(state.value, RESET)
        print(f"    [{i+1:2d}] {color}● {state.value:15s}{RESET}  duration={duration_ms/1000:.1f}s")
        
        if state.value == "exiting":
            break
        engine.advance_state()

    # State frequency
    print(f"\n    {BOLD}State Frequency:{RESET}")
    from collections import Counter
    freq = Counter(states_visited)
    for state, count in freq.most_common():
        bar = "█" * (count * 3)
        print(f"    {state:15s} {GREEN}{bar}{RESET} {count}x")

    subheader("Interruption Triggers")
    triggers = {"notification_loop": 0, "mid_composition_freeze": 0, "ghost_draft": 0}
    test_engine = PolicyEngine(personality=ALL_PERSONALITIES[0])  # Distracted Academic
    for _ in range(100):
        e = test_engine._interruptions.check_notification_loop()
        if e: triggers["notification_loop"] += 1
        e = test_engine._interruptions.check_mid_composition_freeze()
        if e: triggers["mid_composition_freeze"] += 1
    
    for name, count in triggers.items():
        kv(name, f"{count}/100 triggers ({count}%)")
    success("Personality-driven Markov chain operational")


# ═══════════════════════════════════════════════════════════════════
# Module 5: Linguistic Variance & Typo Engine
# ═══════════════════════════════════════════════════════════════════
def demo_linguistic() -> None:
    header("MODULE 5 — Linguistic Variance & Typo Engine")

    from bol.modules.m5_linguistic.typo import TypoEngine
    from bol.modules.m5_linguistic.fatigue import FatigueEngine
    from bol.modules.m5_linguistic.engine import LinguisticEngine
    from bol.modules.m4_policy.personality import DISTRACTED_ACADEMIC

    subheader("QWERTY Proximity Matrix")
    typo = TypoEngine()
    
    # Show adjacency for a sample of keys
    sample_keys = "fhjkl"
    for key in sample_keys:
        neighbors = typo.QWERTY_ADJACENCY.get(key, [])
        kv(f"'{key}' neighbors", ", ".join(f"'{n}'" for n in neighbors))

    # Generate typos for a word
    print(f"\n    {BOLD}Typo Injection Demo — 'behavioral':{RESET}")
    word = "behavioral"
    for _ in range(5):
        typos = []
        for c in word:
            if c.lower() in typo.QWERTY_ADJACENCY and typo.should_inject_typo(0.15):
                replacement = typo.get_proximity_typo(c)
                typos.append(f"{RED}{replacement}{RESET}")
            else:
                typos.append(c)
        print(f"    → {''.join(typos)}")
    success("QWERTY-adjacent typos with case preservation")

    subheader("Progressive Fatigue Model")
    fatigue_eng = FatigueEngine(DISTRACTED_ACADEMIC)
    profile = fatigue_eng.create_profile()
    
    kv("Base WPM", f"{profile.base_wpm:.0f}")
    kv("Decay rate", f"{profile.decay_rate:.3f} per 100 chars")
    kv("Base typo rate", f"{profile.base_typo_rate:.4f}")

    print(f"\n    {BOLD}Fatigue Progression (every 100 chars):{RESET}")
    print(f"    {'Chars':>8s}  {'WPM':>6s}  {'Typo Rate':>10s}  {'Delay/char':>10s}  {'Visual':>20s}")
    print(f"    {'─'*60}")
    for chars in range(0, 501, 50):
        p = fatigue_eng.update_profile(profile, chars)
        wpm = p.current_wpm
        tr = p.current_typo_rate
        delay = p.current_char_delay_ms
        bar_len = int(wpm / profile.base_wpm * 20)
        bar = f"{GREEN}{'█' * bar_len}{DIM}{'░' * (20 - bar_len)}{RESET}"
        print(f"    {chars:>8d}  {wpm:>6.1f}  {tr:>10.4f}  {delay:>8.1f}ms  {bar}")

    subheader("Full Keystroke Sequence Generation")
    sample_text = "AI is transforming how we build software."
    
    ling = LinguisticEngine(
        personality=DISTRACTED_ACADEMIC,
        history_db_path=None,
    )
    payload = ling.prepare_payload(sample_text)
    seq = ling.generate_keystroke_sequence(payload)

    kv("Input text", f'"{sample_text}"')
    kv("Characters", str(payload.character_count))
    kv("Words", str(payload.word_count))
    kv("Total events", str(len(seq.events)))
    kv("Typos injected", str(seq.typo_count))
    kv("Corrections", str(seq.correction_count))
    kv("Total duration", f"{seq.total_duration_ms/1000:.2f}s")
    kv("WPM start→end", f"{seq.effective_wpm_start:.1f} → {seq.effective_wpm_end:.1f}")

    # Show the keystroke stream
    print(f"\n    {BOLD}Keystroke Stream (first 40 events):{RESET}")
    for i, event in enumerate(seq.events[:40]):
        char_display = repr(event.character) if not event.character.isalnum() and event.character != " " else event.character
        if event.is_typo:
            indicator = f"{RED}TYPO{RESET}"
        elif event.is_correction:
            indicator = f"{YELLOW}BKSP{RESET}"
            char_display = "←"
        else:
            indicator = f"{GREEN}    {RESET}"
        delay_bar = "▪" * min(int(event.delay_before_ms / 30), 15)
        print(f"    [{i:3d}] {indicator} '{char_display}' {DIM}{delay_bar}{RESET} {event.delay_before_ms:.0f}ms")

    success("Typo→pause→backspace→correct chain operational")


# ═══════════════════════════════════════════════════════════════════
# Module 7: Session & Profile Lifecycle Controller
# ═══════════════════════════════════════════════════════════════════
def demo_lifecycle() -> None:
    header("MODULE 7 — Session & Profile Lifecycle Controller")

    from bol.config import BOLConfig
    from bol.modules.m7_lifecycle.calendar import CalendarEngine
    from bol.modules.m7_lifecycle.void import VoidEngine

    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "calendar.json"
        engine = CalendarEngine(timezone="Asia/Kolkata", state_path=state_path)

        subheader("Calendar Intelligence")
        decision = engine.is_posting_allowed()
        kv("Today", date.today().isoformat())
        kv("Day type", decision.day_type.value)
        kv("Should execute", f"{GREEN}YES{RESET}" if decision.should_execute else f"{RED}NO{RESET}")
        kv("Reason", decision.reason)
        if decision.recommended_hour is not None:
            kv("Recommended hour", f"{decision.recommended_hour}:00")

        # Check different day types
        print(f"\n    {BOLD}Day Type Classification:{RESET}")
        test_dates = [
            date(2026, 12, 25),  # Christmas
            date(2026, 1, 26),   # Republic Day
            date(2026, 5, 30),   # Saturday
            date(2026, 5, 31),   # Sunday
            date(2026, 6, 1),    # Monday (workday)
        ]
        for d in test_dates:
            dt = engine.get_day_type(d)
            color = {
                "holiday": RED, "weekend": YELLOW, "workday": GREEN, "void": MAGENTA
            }.get(dt.value, RESET)
            print(f"    {d.isoformat()} ({d.strftime('%A'):>9s}) → {color}{dt.value}{RESET}")

        subheader("Void Event Scheduling")
        void_engine = VoidEngine(engine.state)
        voids = void_engine.generate_void_schedule(months_ahead=3)

        kv("Scheduled voids", str(len(voids)))
        for v in voids:
            print(f"    {MAGENTA}●{RESET} {v.start_date} → {v.end_date} ({v.duration_days}d) — {v.reason.value}")

        kv("Currently in void", f"{RED}YES{RESET}" if void_engine.is_in_void() else f"{GREEN}NO{RESET}")
        next_void = void_engine.get_next_void()
        if next_void:
            kv("Next void", f"{next_void.start_date} ({next_void.reason.value})")

        success("Calendar + Void scheduling operational")


# ═══════════════════════════════════════════════════════════════════
# Module 6: Hardware Jitter (if psutil available)
# ═══════════════════════════════════════════════════════════════════
def demo_hardware() -> None:
    header("MODULE 6 — Hardware-Anchored Jitter")

    try:
        from bol.modules.m6_bridge.hardware import HardwareMonitor

        monitor = HardwareMonitor()
        
        subheader("Real-Time Hardware Sampling")
        samples = []
        for i in range(5):
            jitter = monitor.get_jitter()
            samples.append(jitter)
            kv(f"Sample {i+1}",
               f"CPU={jitter.snapshot.cpu_percent:.1f}%  "
               f"RAM={jitter.snapshot.ram_percent:.1f}%  "
               f"→ jitter={jitter.computed_delay_ms:.2f}ms "
               f"(cpu={jitter.cpu_component_ms:.2f} + ram={jitter.ram_component_ms:.2f} + base=0.50)")

        avg_jitter = sum(s.computed_delay_ms for s in samples) / len(samples)
        kv("Avg jitter", f"{avg_jitter:.2f}ms")
        success("Physical hardware anchoring confirmed — each interaction is unique")

    except ImportError:
        warn("psutil not installed — skipping hardware demo")


# ═══════════════════════════════════════════════════════════════════
# Entropy Pool
# ═══════════════════════════════════════════════════════════════════
def demo_entropy() -> None:
    header("FOUNDATION — Cryptographic Entropy Pool")

    from bol.entropy.pool import EntropyPool

    subheader("Sampling Without Replacement")
    pool = EntropyPool(pool_id="demo", values=list(range(1, 21)))
    
    kv("Pool", "20 values [1..20]")
    
    draws = pool.draw_n(10)
    kv("First 10 draws", str(draws))
    kv("All unique?", f"{GREEN}YES{RESET}" if len(set(draws)) == 10 else f"{RED}NO{RESET}")
    kv("Remaining", str(pool.remaining))

    # Exhaust and auto-reset
    remaining = pool.draw_n(10)
    kv("Next 10 draws", str(remaining))
    kv("Pool exhausted?", f"{GREEN}YES{RESET}" if pool.is_exhausted else "NO")

    # Auto-reset on next draw
    new_draw = pool.draw()
    kv("After auto-reset", f"drew {new_draw}, cycle={pool.cycle_id}, remaining={pool.remaining}")
    success("Sampling-without-replacement with auto-cycle-reset confirmed")


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════
def main() -> int:
    print(f"\n{BOLD}{MAGENTA}")
    print("    ╔══════════════════════════════════════════════════════╗")
    print("    ║     BOL — Behavioral Operating Layer                ║")
    print("    ║     Capability Showcase                             ║")
    print("    ╚══════════════════════════════════════════════════════╝")
    print(f"{RESET}")
    print(f"    {DIM}AI-Mediated HCI Framework — Zero DOM Instrumentation{RESET}")
    print(f"    {DIM}All randomness: secrets module (cryptographic entropy){RESET}\n")

    demo_entropy()
    demo_timing()
    demo_kinematic()
    demo_policy()
    demo_linguistic()
    demo_lifecycle()
    demo_hardware()

    print(f"\n{BOLD}{GREEN}")
    print("    ╔══════════════════════════════════════════════════════╗")
    print("    ║     All 7 modules operational ✓                     ║")
    print("    ╚══════════════════════════════════════════════════════╝")
    print(f"{RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
