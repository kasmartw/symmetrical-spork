"""Baseline measurement script (ASYNC version)."""
import os
import asyncio
from langsmith import Client
from datetime import datetime, timedelta
import statistics

async def measure_recent_runs(hours=24, limit=50):
    """Measure metrics from recent LangSmith runs."""
    client = Client()

    # Get runs from last N hours
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)

    runs = list(client.list_runs(
        project_name=os.getenv("LANGCHAIN_PROJECT", "appointment-agent-v2"),
        start_time=start_time,
        end_time=end_time,
        is_root=True,
        limit=limit
    ))

    latencies = []
    iterations = []

    for run in runs:
        if run.status == "success" and run.latency:
            latencies.append(run.latency)
            # Count child runs as iterations
            child_count = len(list(client.list_runs(parent_run_id=run.id)))
            iterations.append(child_count)

    if not latencies:
        print("❌ No runs found in specified time window")
        return None

    metrics = {
        "count": len(latencies),
        "avg_latency_ms": statistics.mean(latencies),
        "median_latency_ms": statistics.median(latencies),
        "avg_iterations": statistics.mean(iterations) if iterations else 0,
        "max_iterations": max(iterations) if iterations else 0,
        "timestamp": datetime.now().isoformat()
    }

    print(f"📊 Baseline Metrics from {len(latencies)} runs:")
    print(f"   Avg Latency: {metrics['avg_latency_ms']:.0f}ms")
    print(f"   Median Latency: {metrics['median_latency_ms']:.0f}ms")
    print(f"   Avg Iterations: {metrics['avg_iterations']:.1f}")
    print(f"   Max Iterations: {metrics['max_iterations']}")

    return metrics

if __name__ == "__main__":
    asyncio.run(measure_recent_runs(hours=24, limit=100))
