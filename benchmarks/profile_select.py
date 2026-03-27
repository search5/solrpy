#!/usr/bin/env python3
"""Detailed profiling: where does select() spend time?

Breaks down HTTP request vs JSON parse vs Response construction.
"""

import json
import time
import statistics
import solr
import pysolr

SOLR_URL = "http://localhost:8983/solr/core0"
ROUNDS = 50
ROWS_LIST = [10, 50, 100, 200, 500, 1000]


def make_docs(n):
    return [{"id": f"prof_{i}", "data": f"profile doc {i}", "user_id": f"u{i%100}"} for i in range(n)]


def profile_solrpy(conn, rows):
    """Profile solrpy select broken into stages."""
    import urllib.parse
    from solr.utils import strify
    from solr.parsers import parse_json_response

    times = {"total": [], "http": [], "json_parse": [], "response_build": []}

    for _ in range(ROUNDS):
        params = {"q": "*:*", "fl": "*,score", "wt": "json", "rows": str(rows)}
        request = urllib.parse.urlencode(
            [(k.replace("_", "."), strify(v)) for k, v in params.items()], doseq=True)

        t0 = time.perf_counter()

        # HTTP
        rsp = conn._post(conn.path + "/select", request, conn.form_headers)
        t1 = time.perf_counter()

        # JSON parse (from bytes, matching actual code path)
        data = json.loads(rsp.content)
        t2 = time.perf_counter()

        # Response build
        resp = parse_json_response(data, params, conn)
        t3 = time.perf_counter()

        times["http"].append((t1 - t0) * 1000)
        times["json_parse"].append((t2 - t1) * 1000)
        times["response_build"].append((t3 - t2) * 1000)
        times["total"].append((t3 - t0) * 1000)

    return {k: statistics.mean(v) for k, v in times.items()}


def profile_pysolr(conn, rows):
    """Profile pysolr search broken into stages."""
    times = {"total": [], "http": [], "json_parse": [], "response_build": []}

    for _ in range(ROUNDS):
        params = {"q": "*:*", "rows": rows}

        t0 = time.perf_counter()

        # HTTP (pysolr _select returns raw text)
        raw = conn._select(params)
        t1 = time.perf_counter()

        # JSON parse
        data = conn.decoder.decode(raw)
        t2 = time.perf_counter()

        # Response build
        result = pysolr.Results(data)
        t3 = time.perf_counter()

        times["http"].append((t1 - t0) * 1000)
        times["json_parse"].append((t2 - t1) * 1000)
        times["response_build"].append((t3 - t2) * 1000)
        times["total"].append((t3 - t0) * 1000)

    return {k: statistics.mean(v) for k, v in times.items()}


def main():
    conn_s = solr.Solr(SOLR_URL)
    conn_p = pysolr.Solr(SOLR_URL, always_commit=False)

    # Seed data
    docs = make_docs(1100)
    conn_s.add_many(docs, commit=True)

    print(f"{'rows':>6} | {'stage':<16} | {'solrpy':>10} | {'pysolr':>10} | {'diff':>8}")
    print("-" * 65)

    for rows in ROWS_LIST:
        sp = profile_solrpy(conn_s, rows)
        pp = profile_pysolr(conn_p, rows)

        for stage in ["http", "json_parse", "response_build", "total"]:
            s = sp[stage]
            p = pp[stage]
            diff = ((s - p) / p * 100) if p > 0 else 0
            marker = "◀" if abs(diff) > 10 else ""
            print(f"{rows:>6} | {stage:<16} | {s:>8.3f}ms | {p:>8.3f}ms | {diff:>+7.1f}% {marker}")
        print("-" * 65)

    conn_s.delete_query("id:prof_*", commit=True)
    conn_s.close()


if __name__ == "__main__":
    main()
