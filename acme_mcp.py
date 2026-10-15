"""Acme company tools as an MCP server (stdio, no dependencies, Python 3.9+).

Stands in for the Datadog / GitHub / Kubernetes / CI / warehouse MCP servers
agents call at work. Results are big on purpose: that is what real tools return.

    claude mcp add acme -- python3 /path/to/acme_mcp.py
    codex mcp add acme -- python3 /path/to/acme_mcp.py
"""

import csv
import json
import sys
from pathlib import Path

DATA = Path(__file__).parent / "data"
PAGE = {"logs": 300, "orders": 250, "issues": 100, "metrics": 400}


def _lines(name: str) -> list:
    return (DATA / name).read_text().splitlines()


def _page(items: list, page: int, size: int) -> dict:
    page = max(1, int(page or 1))
    pages = max(1, -(-len(items) // size))
    return {"page": page, "pages": pages, "total": len(items), "items": items[(page - 1) * size : page * size]}


def _log_record(line: str) -> dict:
    date, time, level, service, rest = (line.split(None, 4) + [""] * 5)[:5]
    fields = dict(p.split("=", 1) for p in rest.split() if "=" in p)
    return {"timestamp": f"{date}T{time}Z", "level": level, "service": service, "region": fields.get("region"), "message": rest}


def logs_search(page: int = 1, region: str = "", level: str = "", since: str = "", until: str = "") -> dict:
    """since/until compare as text against ISO timestamps, e.g. 2026-10-13T13:40."""
    records = [_log_record(line) for line in _lines("logs/checkout-2026-10-13.log")]
    records = [
        r for r in records
        if (not region or r["region"] == region)
        and (not level or r["level"] == level.upper())
        and (not since or r["timestamp"] >= since)
        and (not until or r["timestamp"] <= until)
    ]
    return _page(records, page, PAGE["logs"])


def orders_list(page: int = 1) -> dict:
    return _page(json.loads((DATA / "api/orders.json").read_text()), page, PAGE["orders"])


def issues_list(page: int = 1) -> dict:
    return _page(json.loads((DATA / "api/github_issues.json").read_text()), page, PAGE["issues"])


def k8s_get_pods(namespace: str = "prod") -> dict:
    return json.loads((DATA / "k8s/pods.json").read_text())


def metrics_query(page: int = 1, region: str = "", endpoint: str = "") -> dict:
    with (DATA / "metrics/latency.csv").open() as f:
        rows = [r for r in csv.DictReader(f) if (not region or r["region"] == region) and (not endpoint or r["endpoint"] == endpoint)]
    return _page(rows, page, PAGE["metrics"])


def ci_get_log(job_id: str = "build-1234") -> str:
    return "\n".join(_lines("ci/build-1234.log")[-1200:])


def customers_export() -> str:
    return (DATA / "private/customers.csv").read_text()


TOOLS = {
    "logs_search": (logs_search, "Search checkout service logs for 2026-10-13 (like Datadog). 300 records per page. Optional filters: region, level (INFO/WARN/ERROR/FATAL), since/until as ISO time like 2026-10-13T13:40.", {"page": "integer", "region": "string", "level": "string", "since": "string", "until": "string"}),
    "orders_list": (orders_list, "List orders from the order service API. 250 per page.", {"page": "integer"}),
    "issues_list": (issues_list, "List GitHub issues for acme/shop. 100 per page.", {"page": "integer"}),
    "k8s_get_pods": (k8s_get_pods, "kubectl get pods -o json for a namespace.", {"namespace": "string"}),
    "metrics_query": (metrics_query, "Query p50/p99 latency metrics. 400 rows per page; optional region and endpoint filters.", {"page": "integer", "region": "string", "endpoint": "string"}),
    "ci_get_log": (ci_get_log, "Fetch the raw log of a CI job.", {"job_id": "string"}),
    "customers_export": (customers_export, "Export the customer table from the warehouse as CSV.", {}),
}


def _schema(params: dict) -> dict:
    return {"type": "object", "properties": {k: {"type": t} for k, t in params.items()}}


def handle(msg: dict):
    method, mid = msg.get("method"), msg.get("id")
    if method == "initialize":
        result = {"protocolVersion": msg["params"].get("protocolVersion", "2025-06-18"), "capabilities": {"tools": {}}, "serverInfo": {"name": "acme", "version": "1.0"}}
    elif method == "tools/list":
        result = {"tools": [{"name": n, "description": d, "inputSchema": _schema(p)} for n, (_, d, p) in TOOLS.items()]}
    elif method == "tools/call":
        name, args = msg["params"]["name"], msg["params"].get("arguments") or {}
        if name not in TOOLS:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"unknown tool {name!r}; available: {', '.join(TOOLS)}"}}
        out = TOOLS[name][0](**args)
        text = out if isinstance(out, str) else json.dumps(out, indent=2)
        result = {"content": [{"type": "text", "text": text}]}
    elif method == "ping":
        result = {}
    else:
        if mid is None:
            return None
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        reply = handle(json.loads(line))
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
