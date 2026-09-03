"""
Concurrency stress test for the MRPL Agentic Workbench.

Covers the Section 11 checklist item "50 concurrent requests handled".
Fires N concurrent /analyze requests from N distinct engineer IDs (each
user_id is its own rate-limit bucket, so this measures the pipeline rather
than the rate limiter), then reports latency distribution and verifies the
service is still healthy afterwards.

Usage:
    # Terminal 1
    uvicorn api.main:app --port 8000
    # Terminal 2
    python scripts/stress_test.py
    python scripts/stress_test.py --requests 100 --url http://127.0.0.1:8000

Exit code 0 = passed, 1 = failed.
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from typing import Any

import httpx

QUERIES = [
    "Reactor-4 pressure 4.2 bar, last service 6 months, budget Rs.50000. When schedule?",
    "Compressor-B making loud noise, temperature up 15C. What is the risk?",
    "Can we skip separator-D maintenance? Last done 26 months ago.",
    "Pump-A and Compressor-B both need service. Budget Rs.35000. Which first?",
    "What is the current status of Heat Exchanger-C?",
]


async def _one(
    client: httpx.AsyncClient, url: str, index: int
) -> tuple[int, float, str]:
    """Fire one request. Returns (status_code, elapsed_seconds, engine)."""
    payload = {
        "query": QUERIES[index % len(QUERIES)],
        "user_id": f"stress_engineer_{index}",
    }
    start = time.perf_counter()
    try:
        response = await client.post(f"{url}/analyze", json=payload, timeout=60.0)
        elapsed = time.perf_counter() - start
        engine = "-"
        if response.status_code == 200:
            body: dict[str, Any] = response.json()
            engine = str(body.get("metadata", {}).get("engine_used", "-"))
        return response.status_code, elapsed, engine
    except Exception as exc:  # noqa: BLE001 - any transport failure is a failure
        return 0, time.perf_counter() - start, f"ERROR: {type(exc).__name__}: {exc}"


async def run(url: str, count: int, budget_sec: float) -> bool:
    print(f"=== Stress test: {count} concurrent requests -> {url} ===\n")

    async with httpx.AsyncClient() as client:
        try:
            health = await client.get(f"{url}/health", timeout=10.0)
            health.raise_for_status()
            print(f"Pre-flight health: {health.json()}\n")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL: service not reachable at {url} ({exc})")
            return False

        wall_start = time.perf_counter()
        results = await asyncio.gather(*(_one(client, url, i) for i in range(count)))
        wall = time.perf_counter() - wall_start

        # Service must survive the burst.
        try:
            after = await client.get(f"{url}/health", timeout=10.0)
            alive = after.status_code == 200
        except Exception:  # noqa: BLE001
            alive = False

    codes: dict[int, int] = {}
    for code, _, _ in results:
        codes[code] = codes.get(code, 0) + 1

    latencies = sorted(elapsed for code, elapsed, _ in results if code == 200)
    engines: dict[str, int] = {}
    for code, _, engine in results:
        if code == 200:
            engines[engine] = engines.get(engine, 0) + 1

    ok = codes.get(200, 0)
    errors = [e for c, _, e in results if c == 0]

    print(f"Wall time      : {wall:.2f}s for {count} requests")
    print(f"Throughput     : {count / wall:.1f} req/s")
    print(f"Status codes   : {dict(sorted(codes.items()))}")
    print(f"Engines used   : {engines}")

    if latencies:
        p50 = statistics.median(latencies)
        p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]
        print(
            f"Latency (2xx)  : p50={p50:.2f}s  p95={p95:.2f}s  max={max(latencies):.2f}s"
        )

    if errors:
        print(f"\nTransport errors ({len(errors)}):")
        for err in errors[:5]:
            print(f"  {err}")

    print(f"\nService alive after burst: {alive}")

    # ── Verdict ──────────────────────────────────────────────────────────────
    print("\n--- CHECKS ---")
    passed = True

    def check(label: str, condition: bool, detail: str = "") -> None:
        nonlocal passed
        print(f"  [{'PASS' if condition else 'FAIL'}] {label}{detail}")
        if not condition:
            passed = False

    check("all requests answered", ok == count, f" ({ok}/{count} returned 200)")
    check("no transport errors / dropped connections", not errors)
    check("no 5xx responses", not any(c >= 500 for c in codes))
    check("service healthy after burst", alive)
    if latencies:
        check(
            f"p95 latency within {budget_sec:.0f}s budget",
            p95 <= budget_sec,
            f" (p95={p95:.2f}s)",
        )

    print(f"\nRESULT: {'PASSED' if passed else 'FAILED'}")
    return passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument(
        "--budget",
        type=float,
        default=6.0,
        help="p95 latency budget in seconds (spec: <6s per query)",
    )
    args = parser.parse_args()
    return 0 if asyncio.run(run(args.url, args.requests, args.budget)) else 1


if __name__ == "__main__":
    sys.exit(main())
