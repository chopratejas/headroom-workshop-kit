"""Acme company tools as an MCP server (stdio, no dependencies, Python 3.9+).

Stands in for the Datadog / GitHub / Kubernetes / CI / warehouse MCP servers
agents call at work. Results are big on purpose: that is what real tools return.

    claude mcp add acme -- python3 /path/to/acme_mcp.py
    codex mcp add acme -- python3 /path/to/acme_mcp.py
"""

import csv
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

DATA = Path(__file__).parent / "data"
PAGE = {"logs": 400, "orders": 250, "issues": 100, "metrics": 400, "alerts": 150, "deploys": 150, "traces": 50, "spec": 4}


def _lines(name: str) -> list:
    return (DATA / name).read_text().splitlines()


def _page(items: list, page: int, size: int) -> dict:
    page = max(1, int(page or 1))
    pages = max(1, -(-len(items) // size))
    return {"page": page, "pages": pages, "total": len(items), "items": items[(page - 1) * size : page * size]}


def logs_search(page: int = 1, region: str = "", level: str = "", since: str = "", until: str = "") -> str:
    """Raw log lines, newest last, like `kubectl logs` or a log MCP server.

    since/until compare as text against the line's timestamp, e.g. 2026-10-13 13:40.
    """
    lines = _lines("logs/checkout-2026-10-13.log")
    since, until = since.replace("T", " "), until.replace("T", " ")
    keep = [
        line for line in lines
        if (not region or f"region={region}" in line)
        and (not level or line.split()[2] == level.upper())
        and (not since or line[:len(since)] >= since)
        and (not until or line[:len(until)] <= until)
    ]
    chunk = _page(keep, page, PAGE["logs"])
    header = f"# page {chunk['page']} of {chunk['pages']} ({chunk['total']} matching lines)"
    return "\n".join([header] + chunk["items"])


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


def alerts_list(page: int = 1, severity: str = "") -> dict:
    items = json.loads((DATA / "ops/alerts.json").read_text())
    if severity:
        items = [a for a in items if a["severity"] == severity]
    return _page(items, page, PAGE["alerts"])


def deploys_list(page: int = 1, service: str = "") -> dict:
    items = json.loads((DATA / "ops/deploys.json").read_text())
    if service:
        items = [d for d in items if d["service"] == service]
    return _page(items, page, PAGE["deploys"])


def traces_search(page: int = 1, region: str = "", since: str = "", until: str = "") -> dict:
    """since/until compare as text against ISO timestamps, e.g. 2026-10-13T14:30."""
    items = [
        tr for tr in json.loads((DATA / "ops/traces.json").read_text())
        if (not region or tr["region"] == region) and (not since or tr["start"] >= since) and (not until or tr["start"] <= until)
    ]
    return _page(items, page, PAGE["traces"])


def runbook_get(name: str = "") -> str:
    names = sorted(p.stem for p in (DATA / "runbooks").glob("*.md"))
    if name not in names:
        return f"Unknown runbook {name!r}. Available: {', '.join(names)}"
    return (DATA / "runbooks" / f"{name}.md").read_text()


def api_spec_get(page: int = 1) -> dict:
    spec = json.loads((DATA / "api/openapi.json").read_text())
    paths = sorted(spec["paths"].items())
    chunk = _page(paths, page, PAGE["spec"])
    return {"openapi": spec["openapi"], "info": spec["info"], "page": chunk["page"], "pages": chunk["pages"], "paths": dict(chunk["items"])}


def _fetch(url: str, body: dict = None) -> bytes:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data, {"Content-Type": "application/json", "User-Agent": "headroom-workshop-kit"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def hn_search(query: str, page: int = 0) -> dict:
    """Hacker News stories via the public Algolia API, raw JSON, 20 per page."""
    q = urllib.parse.urlencode({"query": query, "tags": "story", "hitsPerPage": 20, "page": page})
    return json.loads(_fetch(f"https://hn.algolia.com/api/v1/search?{q}"))


def osv_query(package: str, version: str, page: int = 1) -> dict:
    """Known vulnerabilities for one PyPI package version (OSV.dev), 6 advisories per page."""
    vulns = json.loads(_fetch("https://api.osv.dev/v1/query", {"package": {"name": package, "ecosystem": "PyPI"}, "version": version})).get("vulns", [])
    return {"package": package, "version": version, **_page(vulns, page, 6)}


def arxiv_search(query: str, start: int = 0) -> str:
    """arXiv papers as the raw Atom feed, 20 per call."""
    q = urllib.parse.urlencode({"search_query": f"all:{query}", "start": start, "max_results": 20, "sortBy": "submittedDate"})
    return _fetch(f"https://export.arxiv.org/api/query?{q}").decode()


def pypi_info(package: str) -> dict:
    """PyPI metadata for a package: info block plus every release with its upload time."""
    d = json.loads(_fetch(f"https://pypi.org/pypi/{urllib.parse.quote(package)}/json"))
    releases = {v: (files[0]["upload_time"] if files else None) for v, files in d.get("releases", {}).items()}
    info = {k: v for k, v in d["info"].items() if k != "description"}
    return {"info": info, "releases": releases, "vulnerabilities": d.get("vulnerabilities", [])}


TOOLS = {
    "logs_search": (logs_search, "Search raw checkout service logs for 2026-10-13. 400 lines per page. Optional filters: region, level (INFO/WARN/ERROR/FATAL), since/until like 2026-10-13 13:40.", {"page": "integer", "region": "string", "level": "string", "since": "string", "until": "string"}),
    "orders_list": (orders_list, "List orders from the order service API. 250 per page.", {"page": "integer"}),
    "issues_list": (issues_list, "List GitHub issues for acme/shop. 100 per page.", {"page": "integer"}),
    "k8s_get_pods": (k8s_get_pods, "kubectl get pods -o json for a namespace.", {"namespace": "string"}),
    "metrics_query": (metrics_query, "Query p50/p99 latency metrics. 400 rows per page; optional region and endpoint filters.", {"page": "integer", "region": "string", "endpoint": "string"}),
    "ci_get_log": (ci_get_log, "Fetch the raw log of a CI job.", {"job_id": "string"}),
    "customers_export": (customers_export, "Export the customer table from the warehouse as CSV.", {}),
    "alerts_list": (alerts_list, "List PagerDuty alerts for the last week. 150 per page; optional severity filter (info/warning/high/critical).", {"page": "integer", "severity": "string"}),
    "deploys_list": (deploys_list, "List deploys since 2026-10-01. 150 per page; optional service filter.", {"page": "integer", "service": "string"}),
    "traces_search": (traces_search, "Search distributed traces for /pay on 2026-10-13. 50 traces per page. Optional filters: region, since/until as ISO time.", {"page": "integer", "region": "string", "since": "string", "until": "string"}),
    "runbook_get": (runbook_get, "Fetch an on-call runbook by name (call with no name to list them).", {"name": "string"}),
    "api_spec_get": (api_spec_get, "Fetch the OpenAPI spec of the Acme order service, 4 paths per page.", {"page": "integer"}),
    "hn_search": (hn_search, "Search Hacker News stories (live, public Algolia API). 20 per page, page starts at 0.", {"query": "string", "page": "integer"}),
    "osv_query": (osv_query, "Known vulnerabilities for a PyPI package version (live, OSV.dev). 6 advisories per page.", {"package": "string", "version": "string", "page": "integer"}),
    "arxiv_search": (arxiv_search, "Search arXiv papers, newest first (live). Returns the raw Atom feed, 20 per call; use start to page.", {"query": "string", "start": "integer"}),
    "pypi_info": (pypi_info, "PyPI metadata and full release history for a package (live).", {"package": "string"}),
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
        try:
            out = TOOLS[name][0](**args)
        except OSError as exc:
            return {"jsonrpc": "2.0", "id": mid, "result": {"isError": True, "content": [{"type": "text", "text": f"{name} could not reach its data source ({exc}). Check your network and retry."}]}}
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
