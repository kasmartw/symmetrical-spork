"""Utilities for measuring latency and performance."""
import time
from contextlib import contextmanager
from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class LatencyMeasurement:
    """Single latency measurement."""
    operation: str
    duration_ms: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


class LatencyTracker:
    """Track and analyze latency measurements."""

    def __init__(self):
        self.measurements: List[LatencyMeasurement] = []

    @contextmanager
    def measure(self, operation: str, **metadata):
        """Context manager to measure operation latency."""
        start = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            self.measurements.append(
                LatencyMeasurement(
                    operation=operation,
                    duration_ms=duration_ms,
                    metadata=metadata
                )
            )

    def get_stats(self, operation: str = None) -> Dict:
        """Get statistics for measurements."""
        measurements = self.measurements
        if operation:
            measurements = [m for m in measurements if m.operation == operation]

        if not measurements:
            return {}

        durations = [m.duration_ms for m in measurements]
        return {
            "count": len(durations),
            "min_ms": min(durations),
            "max_ms": max(durations),
            "avg_ms": sum(durations) / len(durations),
            "total_ms": sum(durations)
        }

    def print_summary(self):
        """Print formatted summary of all measurements."""
        operations = set(m.operation for m in self.measurements)
        print("\n" + "="*70)
        print("⏱️  LATENCY SUMMARY")
        print("="*70)
        for op in sorted(operations):
            stats = self.get_stats(op)
            print(f"\n{op}:")
            print(f"  Count:   {stats['count']}")
            print(f"  Average: {stats['avg_ms']:.2f}ms")
            print(f"  Min:     {stats['min_ms']:.2f}ms")
            print(f"  Max:     {stats['max_ms']:.2f}ms")
        print("="*70 + "\n")

    def clear(self):
        """Clear all measurements."""
        self.measurements = []
