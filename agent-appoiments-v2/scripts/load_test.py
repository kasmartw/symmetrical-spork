"""
Load Testing Script for Appointment Booking Agent.

Tests concurrent user capacity with realistic conversation patterns.
Validates production readiness under load (10, 50, 100+ concurrent users).
"""
import asyncio
import time
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from langchain_core.messages import HumanMessage
from src.agent import create_graph
import sys


class LoadTestResults:
    """Container for load test results."""

    def __init__(self, num_users: int):
        self.num_users = num_users
        self.latencies: List[float] = []
        self.successes = 0
        self.failures = 0
        self.error_messages: List[str] = []
        self.start_time = None
        self.end_time = None

    @property
    def total_time(self) -> float:
        """Total test duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0

    @property
    def throughput(self) -> float:
        """Requests per second."""
        if self.total_time > 0:
            return self.num_users / self.total_time
        return 0.0

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        total = self.successes + self.failures
        if total > 0:
            return (self.successes / total) * 100
        return 0.0

    @property
    def avg_latency(self) -> float:
        """Average latency in milliseconds."""
        if self.latencies:
            return statistics.mean(self.latencies)
        return 0.0

    @property
    def median_latency(self) -> float:
        """Median latency in milliseconds."""
        if self.latencies:
            return statistics.median(self.latencies)
        return 0.0

    @property
    def p95_latency(self) -> float:
        """P95 latency in milliseconds."""
        if self.latencies:
            sorted_lat = sorted(self.latencies)
            idx = int(len(sorted_lat) * 0.95)
            return sorted_lat[idx] if idx < len(sorted_lat) else sorted_lat[-1]
        return 0.0

    @property
    def p99_latency(self) -> float:
        """P99 latency in milliseconds."""
        if self.latencies:
            sorted_lat = sorted(self.latencies)
            idx = int(len(sorted_lat) * 0.99)
            return sorted_lat[idx] if idx < len(sorted_lat) else sorted_lat[-1]
        return 0.0


def get_future_date(days_ahead: int = 7) -> str:
    """Generate future date for booking."""
    future = datetime.now() + timedelta(days=days_ahead)
    return future.strftime("%Y-%m-%d")


async def simulate_user_booking(
    user_id: int,
    graph,
    quick_mode: bool = False
) -> Tuple[bool, float, str]:
    """
    Simulate a single user completing a booking.

    Args:
        user_id: Unique user identifier
        graph: Agent graph instance
        quick_mode: If True, use minimal conversation flow

    Returns:
        (success, latency_ms, error_message)
    """
    thread_id = f"load-test-user-{user_id}"
    config = {
        "configurable": {
            "thread_id": thread_id,
            "recursion_limit": 10
        }
    }

    # Define conversation flow (quick mode for faster testing)
    if quick_mode:
        # Minimal flow: just greeting + service selection
        messages = [
            "Hello",
            "General Consultation"
        ]
    else:
        # Full booking flow
        messages = [
            "Book appointment",
            "General Consultation",
            "morning",
            get_future_date(4),
            "09:00",
            f"User {user_id}",
            f"user{user_id}@test.com",
            f"+155500{user_id:05d}",
            "yes"
        ]

    start = time.time()

    try:
        for msg in messages:
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=msg)]},
                config=config
            )

            # Check for errors in response
            if result and "messages" in result and result["messages"]:
                last_msg = result["messages"][-1]
                if hasattr(last_msg, 'content'):
                    content = str(last_msg.content).lower()
                    if 'error' in content or 'failed' in content:
                        latency = (time.time() - start) * 1000
                        return False, latency, f"Error in response: {content[:100]}"

        latency = (time.time() - start) * 1000
        return True, latency, ""

    except Exception as e:
        latency = (time.time() - start) * 1000
        return False, latency, str(e)


async def run_load_test(
    num_users: int,
    quick_mode: bool = False,
    show_progress: bool = True
) -> LoadTestResults:
    """
    Run load test with specified number of concurrent users.

    Args:
        num_users: Number of concurrent users to simulate
        quick_mode: Use minimal conversation flow (faster)
        show_progress: Print progress updates

    Returns:
        LoadTestResults with metrics
    """
    print(f"\n{'='*80}")
    print(f"🚀 LOAD TEST: {num_users} Concurrent Users")
    print(f"   Mode: {'Quick (2 messages)' if quick_mode else 'Full booking flow'}")
    print(f"{'='*80}\n")

    results = LoadTestResults(num_users)

    # Create single graph instance (shared across users)
    graph = create_graph()

    # Start timer
    results.start_time = time.time()

    # Create tasks for all users
    tasks = []
    for i in range(num_users):
        task = simulate_user_booking(i, graph, quick_mode)
        tasks.append(task)

        if show_progress and (i + 1) % 10 == 0:
            print(f"   Created tasks for {i + 1}/{num_users} users...")

    if show_progress:
        print(f"\n⏳ Executing {num_users} concurrent requests...")

    # Execute all users concurrently
    user_results = await asyncio.gather(*tasks, return_exceptions=True)

    # End timer
    results.end_time = time.time()

    # Process results
    for i, result in enumerate(user_results):
        if isinstance(result, Exception):
            results.failures += 1
            results.error_messages.append(f"User {i}: {str(result)}")
        else:
            success, latency, error = result
            if success:
                results.successes += 1
                results.latencies.append(latency)
            else:
                results.failures += 1
                if error:
                    results.error_messages.append(f"User {i}: {error}")

    return results


def print_results(results: LoadTestResults):
    """Print formatted load test results."""
    print(f"\n{'='*80}")
    print(f"📊 LOAD TEST RESULTS")
    print(f"{'='*80}")
    print(f"👥 Concurrent Users:    {results.num_users}")
    print(f"⏱️  Total Duration:     {results.total_time:.2f}s")
    print(f"✅ Successes:           {results.successes}")
    print(f"❌ Failures:            {results.failures}")
    print(f"📈 Success Rate:        {results.success_rate:.1f}%")
    print(f"🚀 Throughput:          {results.throughput:.2f} req/s")
    print(f"{'='*80}")
    print(f"⏱️  LATENCY METRICS (milliseconds)")
    print(f"{'='*80}")
    print(f"   Average:             {results.avg_latency:.2f}ms")
    print(f"   Median:              {results.median_latency:.2f}ms")
    print(f"   P95:                 {results.p95_latency:.2f}ms")
    print(f"   P99:                 {results.p99_latency:.2f}ms")

    if results.latencies:
        print(f"   Min:                 {min(results.latencies):.2f}ms")
        print(f"   Max:                 {max(results.latencies):.2f}ms")

    print(f"{'='*80}")

    # Show first 3 errors (if any)
    if results.error_messages:
        print(f"\n⚠️  ERRORS (showing first 3):")
        for error in results.error_messages[:3]:
            print(f"   - {error[:120]}")
        if len(results.error_messages) > 3:
            print(f"   ... and {len(results.error_messages) - 3} more errors")

    print()


def assess_production_readiness(results: LoadTestResults) -> bool:
    """
    Assess if system meets production readiness criteria.

    Criteria:
    - Success rate > 95%
    - P95 latency < 5000ms
    - No catastrophic failures
    """
    print(f"\n{'='*80}")
    print(f"🔍 PRODUCTION READINESS ASSESSMENT")
    print(f"{'='*80}")

    checks = []

    # Check 1: Success rate
    success_rate_ok = results.success_rate > 95.0
    checks.append(("Success Rate > 95%", results.success_rate > 95.0, f"{results.success_rate:.1f}%"))

    # Check 2: P95 latency
    p95_ok = results.p95_latency < 5000
    checks.append(("P95 Latency < 5s", p95_ok, f"{results.p95_latency:.0f}ms"))

    # Check 3: No catastrophic failures (> 50% failure)
    catastrophic_ok = results.success_rate > 50.0
    checks.append(("No Catastrophic Failures", catastrophic_ok, f"{results.failures} failures"))

    # Print checks
    for check_name, passed, value in checks:
        icon = "✅" if passed else "❌"
        print(f"   {icon} {check_name:<30} {value}")

    all_passed = all(check[1] for check in checks)

    print(f"{'='*80}")
    if all_passed:
        print(f"✅ PRODUCTION READY: All checks passed")
    else:
        print(f"⚠️  NEEDS ATTENTION: Some checks failed")
    print(f"{'='*80}\n")

    return all_passed


async def run_progressive_load_test():
    """Run progressive load test: 10 → 50 → 100 users."""
    print(f"\n{'='*80}")
    print(f"🚀 PROGRESSIVE LOAD TEST")
    print(f"{'='*80}")
    print(f"Testing: 10 → 50 → 100 concurrent users")
    print(f"Mode: Quick (2 messages per user for faster testing)")
    print(f"{'='*80}\n")

    test_configs = [
        (10, "10 users (warm-up)"),
        (50, "50 users (moderate load)"),
        (100, "100 users (high load)")
    ]

    all_results = []

    for num_users, description in test_configs:
        print(f"\n🔄 Starting: {description}")
        results = await run_load_test(num_users, quick_mode=True, show_progress=True)
        print_results(results)
        assess_production_readiness(results)
        all_results.append((num_users, results))

        # Brief pause between tests
        if num_users < 100:
            print(f"⏸️  Pausing 3 seconds before next test...\n")
            await asyncio.sleep(3)

    # Summary
    print(f"\n{'='*80}")
    print(f"📊 PROGRESSIVE LOAD TEST SUMMARY")
    print(f"{'='*80}")
    print(f"{'Users':<10} {'Success Rate':<15} {'Avg Latency':<15} {'P95 Latency':<15} {'Throughput'}")
    print(f"{'-'*80}")

    for num_users, results in all_results:
        print(
            f"{num_users:<10} "
            f"{results.success_rate:>6.1f}%        "
            f"{results.avg_latency:>8.0f}ms       "
            f"{results.p95_latency:>8.0f}ms       "
            f"{results.throughput:>6.2f} req/s"
        )

    print(f"{'='*80}\n")


async def main():
    """Main entry point."""
    import sys

    if len(sys.argv) > 1:
        # Single test mode
        num_users = int(sys.argv[1])
        quick_mode = "--quick" in sys.argv

        results = await run_load_test(num_users, quick_mode=quick_mode)
        print_results(results)
        assess_production_readiness(results)
    else:
        # Progressive test mode (default)
        await run_progressive_load_test()


if __name__ == "__main__":
    asyncio.run(main())
