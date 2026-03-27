#!/usr/bin/env python3
"""Performance benchmark: solrpy vs pysolr.

Measures add, bulk add, select, delete, and async operations.
Requires a running Solr instance on localhost:8983 with core 'core0'.

Usage:
    poetry run python benchmarks/bench.py
"""

import asyncio
import json
import statistics
import time
from contextlib import contextmanager
from typing import Any

# ── Config ──────────────────────────────────────────────────────────
SOLR_URL = "http://localhost:8983/solr/core0"
WARMUP_ROUNDS = 3
BENCH_ROUNDS = 20
BULK_SIZES = [10, 100, 500]
SELECT_ROWS = [10, 100, 500]

# ── Helpers ─────────────────────────────────────────────────────────

def make_doc(i: int, prefix: str = "bench") -> dict[str, Any]:
    return {
        "id": f"{prefix}_{i}",
        "data": f"benchmark document number {i}",
        "user_id": f"user_{i % 100}",
    }


def make_docs(n: int, prefix: str = "bench") -> list[dict[str, Any]]:
    return [make_doc(i, prefix) for i in range(n)]


@contextmanager
def timer():
    """Context manager that records elapsed time in milliseconds."""
    result = {"ms": 0.0}
    start = time.perf_counter()
    yield result
    result["ms"] = (time.perf_counter() - start) * 1000


def bench(fn, rounds: int = BENCH_ROUNDS, warmup: int = WARMUP_ROUNDS):
    """Run fn() multiple times and return timing stats."""
    # Warmup
    for _ in range(warmup):
        fn()

    times = []
    for _ in range(rounds):
        with timer() as t:
            fn()
        times.append(t["ms"])

    return {
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
        "min_ms": min(times),
        "max_ms": max(times),
        "p95_ms": sorted(times)[int(len(times) * 0.95)],
    }


def bench_async(coro_fn, rounds: int = BENCH_ROUNDS, warmup: int = WARMUP_ROUNDS):
    """Run an async function multiple times and return timing stats."""
    loop = asyncio.new_event_loop()

    for _ in range(warmup):
        loop.run_until_complete(coro_fn())

    times = []
    for _ in range(rounds):
        with timer() as t:
            loop.run_until_complete(coro_fn())
        times.append(t["ms"])

    loop.close()
    return {
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
        "min_ms": min(times),
        "max_ms": max(times),
        "p95_ms": sorted(times)[int(len(times) * 0.95)],
    }


def fmt(stats: dict) -> str:
    return f"{stats['mean_ms']:8.2f}ms (median {stats['median_ms']:.2f}, p95 {stats['p95_ms']:.2f})"


def compare(name: str, solrpy_stats: dict, pysolr_stats: dict):
    ratio = pysolr_stats["mean_ms"] / solrpy_stats["mean_ms"] if solrpy_stats["mean_ms"] > 0 else 0
    faster = "solrpy" if ratio > 1 else "pysolr"
    factor = ratio if ratio > 1 else (1 / ratio if ratio > 0 else 0)
    print(f"  {name}")
    print(f"    solrpy : {fmt(solrpy_stats)}")
    print(f"    pysolr : {fmt(pysolr_stats)}")
    print(f"    → {faster} is {factor:.2f}x faster")
    print()
    return {
        "name": name,
        "solrpy_mean_ms": solrpy_stats["mean_ms"],
        "pysolr_mean_ms": pysolr_stats["mean_ms"],
        "faster": faster,
        "factor": factor,
    }


# ── Benchmarks ──────────────────────────────────────────────────────

def run_benchmarks():
    import solr
    import pysolr

    conn_s = solr.Solr(SOLR_URL)
    conn_p = pysolr.Solr(SOLR_URL, always_commit=False)

    results = []

    print("=" * 65)
    print("  solrpy vs pysolr — Performance Benchmark")
    print(f"  Solr {'.'.join(str(v) for v in conn_s.server_version)}")
    print(f"  Rounds: {BENCH_ROUNDS} (warmup: {WARMUP_ROUNDS})")
    print("=" * 65)
    print()

    # ── 1. Single document add ──────────────────────────────────────
    print("[1] Single document add + commit")
    doc = make_doc(0, "single")

    def solrpy_add_single():
        conn_s.add(doc, commit=True)

    def pysolr_add_single():
        conn_p.add([doc], commit=True)

    r = compare("add 1 doc",
                bench(solrpy_add_single),
                bench(pysolr_add_single))
    results.append(r)

    conn_s.delete(id="single_0", commit=True)

    # ── 2. Bulk add ─────────────────────────────────────────────────
    for n in BULK_SIZES:
        print(f"[2] Bulk add {n} docs + commit")
        docs = make_docs(n, f"bulk{n}")
        ids = [d["id"] for d in docs]

        def solrpy_bulk():
            conn_s.add_many(docs, commit=True)

        def pysolr_bulk():
            conn_p.add(docs, commit=True)

        r = compare(f"add_many {n} docs",
                    bench(solrpy_bulk, rounds=10),
                    bench(pysolr_bulk, rounds=10))
        results.append(r)

        for id_ in ids:
            conn_s.delete(id=id_)
        conn_s.commit()

    # ── 3. Search / Select ──────────────────────────────────────────
    # Seed data
    seed = make_docs(1000, "search")
    conn_s.add_many(seed, commit=True)

    for rows in SELECT_ROWS:
        print(f"[3] Select *:* rows={rows}")

        def solrpy_select():
            conn_s.select("*:*", rows=rows)

        def pysolr_select():
            conn_p.search("*:*", rows=rows)

        r = compare(f"select rows={rows}",
                    bench(solrpy_select),
                    bench(pysolr_select))
        results.append(r)

    # ── 4. Filtered search ──────────────────────────────────────────
    print("[4] Filtered search (fq)")

    def solrpy_filtered():
        conn_s.select("*:*", fq="user_id:user_42", rows=50)

    def pysolr_filtered():
        conn_p.search("*:*", fq="user_id:user_42", rows=50)

    r = compare("filtered search",
                bench(solrpy_filtered),
                bench(pysolr_filtered))
    results.append(r)

    # ── 5. Delete ───────────────────────────────────────────────────
    print("[5] Delete by query")

    def solrpy_delete():
        conn_s.add(make_doc(9999, "del"), commit=True)
        conn_s.delete(id="del_9999", commit=True)

    def pysolr_delete():
        conn_p.add([make_doc(9999, "del")], commit=True)
        conn_p.delete(id="del_9999", commit=True)

    r = compare("add+delete cycle",
                bench(solrpy_delete, rounds=10),
                bench(pysolr_delete, rounds=10))
    results.append(r)

    # ── 6. Connection setup ─────────────────────────────────────────
    print("[6] Connection setup (version detection)")

    def solrpy_connect():
        c = solr.Solr(SOLR_URL)
        c.close()

    def pysolr_connect():
        c = pysolr.Solr(SOLR_URL)
        # pysolr doesn't connect on init, force a ping
        c.ping()

    r = compare("connect + version detect",
                bench(solrpy_connect, rounds=10),
                bench(pysolr_connect, rounds=10))
    results.append(r)

    # ── 7/8. Async (solrpy only) ────────────────────────────────────
    print("[7] Async select (solrpy only — pysolr has no async)")
    print("    (connection reused across rounds)")

    adocs = make_docs(100, "abench")

    async def run_async_benches():
        async with solr.AsyncSolr(SOLR_URL) as aconn:
            # Async select
            times_sel = []
            for _ in range(WARMUP_ROUNDS):
                await aconn.select("*:*", rows=100)
            for _ in range(BENCH_ROUNDS):
                with timer() as t:
                    await aconn.select("*:*", rows=100)
                times_sel.append(t["ms"])

            # Async bulk add
            for _ in range(2):
                await aconn.add_many(adocs, commit=True)
            times_bulk = []
            for _ in range(10):
                with timer() as t:
                    await aconn.add_many(adocs, commit=True)
                times_bulk.append(t["ms"])

            return times_sel, times_bulk

    loop = asyncio.new_event_loop()
    times_sel, times_bulk = loop.run_until_complete(run_async_benches())
    loop.close()

    def stats_from(times):
        return {
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
            "min_ms": min(times),
            "max_ms": max(times),
            "p95_ms": sorted(times)[int(len(times) * 0.95)],
        }

    async_sel = stats_from(times_sel)
    sync_sel = bench(lambda: conn_s.select("*:*", rows=100), rounds=BENCH_ROUNDS)
    print(f"  async select rows=100")
    print(f"    solrpy async: {fmt(async_sel)}")
    print(f"    solrpy sync : {fmt(sync_sel)}")
    ratio = async_sel["mean_ms"] / sync_sel["mean_ms"] if sync_sel["mean_ms"] > 0 else 0
    print(f"    → async/sync ratio: {ratio:.2f}x")
    print()

    print("[8] Async bulk add 100 docs (solrpy only)")
    async_bulk = stats_from(times_bulk)
    sync_bulk = bench(lambda: conn_s.add_many(adocs, commit=True), rounds=10, warmup=2)
    print(f"  async add_many 100")
    print(f"    solrpy async: {fmt(async_bulk)}")
    print(f"    solrpy sync : {fmt(sync_bulk)}")
    ratio = async_bulk["mean_ms"] / sync_bulk["mean_ms"] if sync_bulk["mean_ms"] > 0 else 0
    print(f"    → async/sync ratio: {ratio:.2f}x")
    print()

    # ── Cleanup ─────────────────────────────────────────────────────
    conn_s.delete_query("id:search_*", commit=True)
    conn_s.close()

    # ── Summary ─────────────────────────────────────────────────────
    print("=" * 65)
    print("  SUMMARY")
    print("=" * 65)
    print(f"  {'Test':<30} {'solrpy':>10} {'pysolr':>10} {'Winner':>10}")
    print("  " + "-" * 62)
    for r in results:
        winner = f"{r['faster']} {r['factor']:.1f}x"
        print(f"  {r['name']:<30} {r['solrpy_mean_ms']:>8.1f}ms {r['pysolr_mean_ms']:>8.1f}ms {winner:>10}")
    print()

    # Count wins
    solrpy_wins = sum(1 for r in results if r["faster"] == "solrpy")
    pysolr_wins = sum(1 for r in results if r["faster"] == "pysolr")
    print(f"  solrpy wins: {solrpy_wins}/{len(results)}")
    print(f"  pysolr wins: {pysolr_wins}/{len(results)}")
    print()

    return results


if __name__ == "__main__":
    run_benchmarks()
