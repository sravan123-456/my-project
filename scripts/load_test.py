#!/usr/bin/env python3
"""Simple HTTP load test for capacity checks."""

from __future__ import annotations

import argparse
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def fetch(url: str, timeout: float) -> dict:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            elapsed_ms = (time.perf_counter() - started) * 1000
            return {
                "ok": 200 <= response.status < 400,
                "status": response.status,
                "ms": elapsed_ms,
            }
    except Exception as exc:  # noqa: BLE001 - report all request failures
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {"ok": False, "status": None, "ms": elapsed_ms, "error": str(exc)}


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((pct / 100) * (len(ordered) - 1)))
    return ordered[index]


def run_scenario(url: str, concurrency: int, requests: int, timeout: float) -> dict:
    started = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(fetch, url, timeout) for _ in range(requests)]
        for future in as_completed(futures):
            results.append(future.result())
    elapsed_s = time.perf_counter() - started

    ok_results = [r for r in results if r["ok"]]
    fail_results = [r for r in results if not r["ok"]]
    latencies = [r["ms"] for r in ok_results]

    return {
        "url": url,
        "concurrency": concurrency,
        "requests": requests,
        "success": len(ok_results),
        "failed": len(fail_results),
        "success_rate": (len(ok_results) / requests) * 100 if requests else 0,
        "duration_s": elapsed_s,
        "rps": len(ok_results) / elapsed_s if elapsed_s else 0,
        "p50_ms": percentile(latencies, 50),
        "p95_ms": percentile(latencies, 95),
        "p99_ms": percentile(latencies, 99),
        "max_ms": max(latencies) if latencies else 0,
        "sample_error": fail_results[0].get("error") if fail_results else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="HTTP load test")
    parser.add_argument("url")
    parser.add_argument("--concurrency", type=int, action="append", required=True)
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    print(f"target={args.url} total_per_scenario={args.requests}")
    print("concurrency,success,failed,success_rate,rps,p50_ms,p95_ms,p99_ms,max_ms,sample_error")
    for concurrency in args.concurrency:
        result = run_scenario(args.url, concurrency, args.requests, args.timeout)
        print(
            f"{result['concurrency']},"
            f"{result['success']},"
            f"{result['failed']},"
            f"{result['success_rate']:.1f},"
            f"{result['rps']:.1f},"
            f"{result['p50_ms']:.1f},"
            f"{result['p95_ms']:.1f},"
            f"{result['p99_ms']:.1f},"
            f"{result['max_ms']:.1f},"
            f"{result['sample_error'] or ''}"
        )


if __name__ == "__main__":
    main()
