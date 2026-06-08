"""
Hardware load sampling for micro-delay injection.

Samples CPU and RAM utilization to compute hardware-anchored
jitter delays that tie digital interactions to physical performance.
"""

from __future__ import annotations

import psutil

from bol.schemas.bridge import HardwareJitter, HardwareSnapshot


class HardwareMonitor:
    """
    Samples host machine hardware performance and computes
    micro-delays anchored to physical system load.
    """

    _BASE_JITTER_MS = 0.5
    _CPU_WEIGHT_MS = 3.0   # Max 3ms from CPU load
    _RAM_WEIGHT_MS = 2.0   # Max 2ms from RAM load

    def sample(self) -> HardwareSnapshot:
        """Take a snapshot of current CPU and RAM utilization."""
        cpu = psutil.cpu_percent(interval=0.05)
        ram = psutil.virtual_memory().percent
        return HardwareSnapshot(cpu_percent=cpu, ram_percent=ram)

    def compute_jitter(self, snapshot: HardwareSnapshot) -> HardwareJitter:
        """
        Compute a micro-delay based on hardware load.

        Higher CPU/RAM load → slightly longer delays, anchoring
        the digital signature to physical hardware constraints.
        """
        cpu_ms = (snapshot.cpu_percent / 100.0) * self._CPU_WEIGHT_MS
        ram_ms = (snapshot.ram_percent / 100.0) * self._RAM_WEIGHT_MS
        total = cpu_ms + ram_ms + self._BASE_JITTER_MS

        return HardwareJitter(
            snapshot=snapshot,
            computed_delay_ms=total,
            cpu_component_ms=cpu_ms,
            ram_component_ms=ram_ms,
        )

    def get_jitter(self) -> HardwareJitter:
        """Convenience: sample hardware and compute jitter in one call."""
        return self.compute_jitter(self.sample())
