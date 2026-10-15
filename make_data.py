"""Generate the workshop data files. Deterministic: same seed, same bytes.

    python3 make_data.py

Every file has a few "needles" (the real answer) buried in a lot of noise,
which is what agents read all day. Answers are in FACILITATOR.md.
"""

import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 20261014
ROOT = Path(__file__).parent / "data"
REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "ap-south-1"]
ENDPOINTS = ["/cart", "/checkout", "/pay", "/orders", "/inventory", "/login"]
SERVICES = ["checkout", "cart", "payments", "inventory", "auth", "search"]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def checkout_log(rng: random.Random) -> str:
    """25k lines. Root cause: a 14:02 config reload drops the eu-west-1 pool 50 -> 20."""
    t = datetime(2026, 10, 13, 13, 0, 0)
    lines = []
    for i in range(25_000):
        t += timedelta(milliseconds=rng.randint(80, 220))
        ts = t.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        region = rng.choice(REGIONS)
        if i == 9_870:
            lines.append(f"{ts} INFO  config-agent reload applied: db.pool.max_connections 50 -> 20 region=eu-west-1 deploy=rel-8812 by=ci-bot")
            continue
        if 17_300 <= i < 17_340 and region == "eu-west-1":
            lines.append(f"{ts} ERROR payments req={i:06d} region=eu-west-1 payment-gateway timeout after 30000ms waiting for db connection")
            continue
        if i == 17_342:
            lines.append(f"{ts} FATAL checkout region=eu-west-1 connection pool exhausted (active=20 max=20 waiting=311) - shedding traffic")
            continue
        if i % 997 == 0:
            lines.append(f"{ts} WARN  cache region={region} miss ratio 0.{rng.randint(11, 19)} above 0.10 for key prefix cart:")
            continue
        ep = rng.choice(ENDPOINTS)
        ms = rng.randint(12, 180)
        lines.append(f"{ts} INFO  {rng.choice(SERVICES)} req={i:06d} region={region} {ep} 200 {ms}ms user=u{rng.randint(1000, 9999)}")
    return "\n".join(lines) + "\n"


def ci_log(rng: random.Random) -> str:
    """8k lines of install/build noise; one test fails at step 'integration'."""
    lines = []
    for i in range(3_000):
        pkg = f"pkg-{rng.randint(1, 900)}"
        lines.append(f"[install] added {pkg}@{rng.randint(1, 9)}.{rng.randint(0, 30)}.{rng.randint(0, 9)} ({rng.randint(1, 900)}kB)")
    for i in range(3_000):
        lines.append(f"[build] compiling src/module_{i % 400}.ts -> dist/module_{i % 400}.js ok ({rng.randint(3, 90)}ms)")
    for i in range(1_990):
        lines.append(f"[test] PASS tests/unit/case_{i:04d}.test.ts ({rng.randint(2, 40)}ms)")
    lines += [
        "[test] FAIL tests/integration/checkout.test.ts",
        "  ● checkout › applies loyalty discount once",
        "    expect(received).toBe(expected)",
        "    Expected: 90.00",
        "    Received: 81.00",
        "      at Object.<anonymous> (tests/integration/checkout.test.ts:42:31)",
        "[test] Tests: 1 failed, 1990 passed, 1991 total",
        "[ci] step 'integration' failed with exit code 1 (job build-1234)",
    ]
    return "\n".join(lines) + "\n"


def orders(rng: random.Random) -> list:
    """3,000 orders; 4 anomalies hidden inside."""
    out = []
    for i in range(3_000):
        qty = rng.randint(1, 5)
        price = round(rng.uniform(5, 120), 2)
        out.append({
            "order_id": f"ORD-{100000 + i}",
            "customer_id": f"C{rng.randint(1, 800):04d}",
            "region": rng.choice(REGIONS),
            "currency": "USD",
            "items": qty,
            "unit_price": price,
            "total": round(qty * price, 2),
            "status": rng.choice(["paid", "paid", "paid", "shipped", "delivered"]),
            "created_at": f"2026-10-{rng.randint(1, 13):02d}T{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}:00Z",
        })
    out[412]["total"] = -349.99
    out[1203]["currency"] = "EUR"
    out[2210]["order_id"] = out[2209]["order_id"]
    out[2788].update(items=400, total=round(400 * out[2788]["unit_price"], 2))
    return out


def issues(rng: random.Random) -> list:
    """250 GitHub-style issues; 3 are the same double-discount bug in different words."""
    topics = ["flaky test", "dark mode", "slow search", "typo in docs", "login redirect", "CSV export", "timezone", "pagination"]
    dupes = {
        37: "Loyalty members charged 81 instead of 90 on checkout",
        141: "Discount applied twice when coupon and loyalty combine",
        203: "Checkout total too low for returning customers",
    }
    out = []
    for n in range(1, 251):
        title = dupes.get(n) or f"{rng.choice(topics).capitalize()} issue on {rng.choice(ENDPOINTS)}"
        out.append({
            "number": n,
            "title": title,
            "state": rng.choice(["open", "open", "closed"]),
            "labels": [{"name": rng.choice(["bug", "enhancement", "docs", "triage"])}],
            "user": {"login": f"dev{rng.randint(1, 60)}", "type": "User", "site_admin": False},
            "comments": rng.randint(0, 12),
            "created_at": f"2026-0{rng.randint(1, 9)}-{rng.randint(10, 28)}T10:00:00Z",
            "body": f"Seen on {rng.choice(REGIONS)}. Steps: open {rng.choice(ENDPOINTS)}, click submit. Expected success, got an error.",
            "reactions": {"+1": rng.randint(0, 9), "-1": 0, "laugh": 0, "hooray": 0, "confused": 0, "heart": 0},
        })
    return out


def pods(rng: random.Random) -> dict:
    """`kubectl get pods -o json` shape; 2 of 70 are OOMKilled in CrashLoopBackOff."""
    items = []
    for i in range(70):
        svc = SERVICES[i % len(SERVICES)]
        bad = i in (23, 61)
        items.append({
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": f"{svc}-{rng.randint(10000, 99999)}-{i:03d}", "namespace": "prod", "labels": {"app": svc, "tier": "backend"}},
            "spec": {"containers": [{"name": svc, "image": f"acme/{svc}:2026.10.{rng.randint(1, 13)}", "resources": {"limits": {"memory": "256Mi" if bad else "1Gi", "cpu": "500m"}}}]},
            "status": {
                "phase": "Running",
                "containerStatuses": [{
                    "name": svc,
                    "ready": not bad,
                    "restartCount": 37 if bad else rng.randint(0, 1),
                    "state": {"waiting": {"reason": "CrashLoopBackOff"}} if bad else {"running": {"startedAt": "2026-10-13T09:00:00Z"}},
                    "lastState": {"terminated": {"reason": "OOMKilled", "exitCode": 137}} if bad else {},
                }],
            },
        })
    return {"apiVersion": "v1", "kind": "List", "items": items}


def latency_csv(rng: random.Random, path: Path) -> None:
    """10k rows; p99 spike for /pay in eu-west-1 between 14:31 and 14:44."""
    path.parent.mkdir(parents=True, exist_ok=True)
    t = datetime(2026, 10, 13, 12, 0, 0)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "region", "endpoint", "p50_ms", "p99_ms", "rps"])
        for _ in range(10_000):
            t += timedelta(seconds=2)
            region, ep = rng.choice(REGIONS), rng.choice(ENDPOINTS)
            spike = region == "eu-west-1" and ep == "/pay" and t.hour == 14 and 31 <= t.minute <= 44
            p99 = rng.randint(2400, 4100) if spike else rng.randint(90, 260)
            w.writerow([t.isoformat(), region, ep, rng.randint(20, 60), p99, rng.randint(40, 400)])


def customers_csv(rng: random.Random, path: Path) -> None:
    """Synthetic PII (example.com, 555 numbers) for the privacy task."""
    first = ["Ava", "Liam", "Noah", "Mia", "Zoe", "Ravi", "Sara", "Ken", "Ines", "Omar"]
    last = ["Patel", "Nguyen", "Garcia", "Kim", "Okafor", "Rossi", "Silva", "Chen", "Haddad", "Novak"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["customer_id", "name", "email", "phone", "card_last4", "lifetime_value_usd"])
        for i in range(400):
            fn, ln = rng.choice(first), rng.choice(last)
            w.writerow([f"C{i + 1:04d}", f"{fn} {ln}", f"{fn.lower()}.{ln.lower()}{i}@example.com", f"+1-555-01{rng.randint(10, 99)}", f"{rng.randint(1000, 9999)}", round(rng.uniform(20, 9000), 2)])


def alerts(rng: random.Random) -> list:
    """A week of PagerDuty-style alerts: ~500 noisy ones, 3 real pages."""
    out = []
    t = datetime(2026, 10, 7, 0, 0, 0)
    noisy = ["DiskUsageHigh", "CertExpiresIn30d", "CacheMissRatioHigh", "CronJobLate", "NodeCPUThrottling", "HPAAtMaxReplicas"]
    for i in range(520):
        t += timedelta(minutes=rng.randint(5, 25))
        out.append({
            "id": f"ALRT-{70000 + i}", "created_at": t.isoformat() + "Z", "status": rng.choice(["resolved", "resolved", "auto-resolved"]),
            "severity": rng.choice(["info", "warning", "warning"]), "service": rng.choice(SERVICES), "region": rng.choice(REGIONS),
            "title": rng.choice(noisy), "acknowledged_by": None, "duration_min": rng.randint(1, 40),
        })
    out += [
        {"id": "ALRT-79001", "created_at": "2026-10-13T13:43:30Z", "status": "resolved", "severity": "critical", "service": "checkout", "region": "eu-west-1", "title": "CheckoutErrorRateHigh (>5% for 2m)", "acknowledged_by": "oncall-sre", "duration_min": 52},
        {"id": "ALRT-79002", "created_at": "2026-10-13T14:32:10Z", "status": "resolved", "severity": "critical", "service": "payments", "region": "eu-west-1", "title": "PayLatencyP99High (>2s for 5m)", "acknowledged_by": "oncall-payments", "duration_min": 13},
        {"id": "ALRT-79003", "created_at": "2026-10-12T22:05:00Z", "status": "open", "severity": "high", "service": "cart", "region": "us-east-1", "title": "PodRestartLoop (restarts>10/h)", "acknowledged_by": None, "duration_min": 1080},
    ]
    out.sort(key=lambda a: a["created_at"])
    return out


def deploys(rng: random.Random) -> list:
    """Deploy history. Three deploys explain the three incidents."""
    out = []
    t = datetime(2026, 10, 1, 9, 0, 0)
    for i in range(140):
        t += timedelta(minutes=rng.randint(30, 160))
        svc = rng.choice(SERVICES)
        out.append({
            "id": f"rel-{8600 + i}", "service": svc, "at": t.isoformat() + "Z", "author": f"dev{rng.randint(1, 60)}", "status": "succeeded",
            "summary": rng.choice(["bump dependencies", "copy change", "add metrics", "refactor handler", "feature flag cleanup", "retry tuning"]),
            "diff_stat": {"files": rng.randint(1, 12), "insertions": rng.randint(1, 300), "deletions": rng.randint(0, 200)},
        })
    out += [
        {"id": "rel-8790", "service": "platform", "at": "2026-10-12T21:40:00Z", "author": "finops-bot", "status": "succeeded", "summary": "Right-size memory limits to cut cluster cost (cart, search: 1Gi -> 256Mi)", "diff_stat": {"files": 2, "insertions": 2, "deletions": 2}},
        {"id": "rel-8812", "service": "checkout", "at": "2026-10-13T13:24:30Z", "author": "ci-bot", "status": "succeeded", "summary": "Sync config from staging (includes db.pool.max_connections)", "diff_stat": {"files": 1, "insertions": 14, "deletions": 14}},
        {"id": "rel-8820", "service": "payments", "at": "2026-10-13T14:30:05Z", "author": "dev17", "status": "rolled_back", "summary": "Enable synchronous fraud check on /pay (eu-west-1 canary)", "diff_stat": {"files": 6, "insertions": 212, "deletions": 9}},
        {"id": "rel-8821", "service": "payments", "at": "2026-10-13T14:45:12Z", "author": "dev17", "status": "succeeded", "summary": "Rollback rel-8820", "diff_stat": {"files": 6, "insertions": 9, "deletions": 212}},
    ]
    out.sort(key=lambda d: d["at"])
    return out


def traces(rng: random.Random) -> list:
    """1,200 /pay traces on 2026-10-13. Slow fraud.check spans 14:31-14:44 in eu-west-1."""
    out = []
    t = datetime(2026, 10, 13, 13, 0, 0)
    for i in range(1_200):
        t += timedelta(seconds=rng.randint(4, 8))
        region = rng.choice(REGIONS)
        slow = region == "eu-west-1" and t.hour == 14 and 31 <= t.minute <= 44
        db_wait = region == "eu-west-1" and t.hour == 13 and 40 <= t.minute <= 59
        spans = [
            {"name": "http.request /pay", "service": "payments", "duration_ms": 0},
            {"name": "auth.verify_token", "service": "auth", "duration_ms": rng.randint(2, 9)},
            {"name": "db.acquire_connection", "service": "payments", "duration_ms": rng.randint(800, 30000) if db_wait else rng.randint(1, 4)},
            {"name": "db.query orders.insert", "service": "payments", "duration_ms": rng.randint(3, 15)},
            {"name": "fraud.check", "service": "fraud", "duration_ms": rng.randint(2000, 3900) if slow else rng.randint(5, 30)},
            {"name": "psp.charge", "service": "payments", "duration_ms": rng.randint(60, 180)},
        ]
        spans[0]["duration_ms"] = sum(s["duration_ms"] for s in spans[1:]) + rng.randint(1, 5)
        out.append({"trace_id": f"{rng.getrandbits(64):016x}", "start": t.isoformat() + "Z", "region": region, "endpoint": "/pay", "status": "error" if spans[2]["duration_ms"] >= 30000 else "ok", "spans": spans})
    return out


RUNBOOKS = {
    "checkout-errors": "# Runbook: checkout error rate high\n\n1. Check payments and checkout logs for timeouts.\n2. Check db connection pool saturation (db.pool.active vs db.pool.max_connections).\n3. If the pool is saturated, compare db.pool.max_connections with the value in the last known-good config (50 in prod).\n4. Roll back the last config sync if it changed pool settings.\n5. Page the database on-call if saturation persists after rollback.\n",
    "pay-latency": "# Runbook: /pay p99 latency high\n\n1. Open traces for /pay and find the slowest span.\n2. If fraud.check dominates, disable the fraud_sync flag (fraud runs async by default).\n3. If psp.charge dominates, check the PSP status page.\n4. Roll back the latest payments deploy if it started within 15 minutes of the alert.\n",
    "pod-restarts": "# Runbook: pod restart loop\n\n1. kubectl describe the pod and read lastState.terminated.reason.\n2. OOMKilled: compare memory limits with p99 working set (cart and search need ~700Mi).\n3. Check recent platform deploys that changed resources.\n4. Raise the limit, then open a ticket for the owning team.\n",
}


def openapi_spec() -> dict:
    """OpenAPI 3 spec for the Acme order service: 36 endpoints, verbose like real specs."""
    resources = ["orders", "customers", "carts", "payments", "refunds", "inventory", "coupons", "shipments", "webhooks"]
    paths = {}
    for r in resources:
        obj = {"type": "object", "properties": {"id": {"type": "string"}, "created_at": {"type": "string", "format": "date-time"}, "updated_at": {"type": "string", "format": "date-time"}, "region": {"type": "string", "enum": REGIONS}, "metadata": {"type": "object", "additionalProperties": {"type": "string"}}, "status": {"type": "string"}}}
        err = {"description": "Error", "content": {"application/json": {"schema": {"type": "object", "properties": {"code": {"type": "string"}, "message": {"type": "string"}, "request_id": {"type": "string"}}}}}}
        common = {"400": err, "401": err, "403": err, "404": err, "429": err, "500": err}
        paths[f"/v1/{r}"] = {
            "get": {"summary": f"List {r}", "operationId": f"list_{r}", "parameters": [{"name": n, "in": "query", "schema": {"type": "string"}, "description": f"Filter {r} by {n}."} for n in ("page", "page_size", "region", "status", "created_after", "created_before")], "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "array", "items": obj}}}}, **common}},
            "post": {"summary": f"Create {r[:-1]}", "operationId": f"create_{r[:-1]}", "requestBody": {"content": {"application/json": {"schema": obj}}}, "responses": {"201": {"description": "Created", "content": {"application/json": {"schema": obj}}}, **common}},
        }
        paths[f"/v1/{r}/{{id}}"] = {
            "get": {"summary": f"Get {r[:-1]}", "operationId": f"get_{r[:-1]}", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}], "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": obj}}}, **common}},
            "patch": {"summary": f"Update {r[:-1]}", "operationId": f"update_{r[:-1]}", "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}], "requestBody": {"content": {"application/json": {"schema": obj}}}, "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": obj}}}, **common}},
        }
    return {"openapi": "3.0.3", "info": {"title": "Acme Order Service", "version": "2026.10"}, "paths": paths}


def main() -> None:
    rng = random.Random(SEED)
    write(ROOT / "logs" / "checkout-2026-10-13.log", checkout_log(rng))
    write(ROOT / "ci" / "build-1234.log", ci_log(rng))
    write(ROOT / "api" / "orders.json", json.dumps(orders(rng), indent=2))
    write(ROOT / "api" / "github_issues.json", json.dumps(issues(rng), indent=2))
    write(ROOT / "k8s" / "pods.json", json.dumps(pods(rng), indent=2))
    latency_csv(rng, ROOT / "metrics" / "latency.csv")
    customers_csv(rng, ROOT / "private" / "customers.csv")
    write(ROOT / "ops" / "alerts.json", json.dumps(alerts(rng), indent=2))
    write(ROOT / "ops" / "deploys.json", json.dumps(deploys(rng), indent=2))
    write(ROOT / "ops" / "traces.json", json.dumps(traces(rng), indent=2))
    for name, text in RUNBOOKS.items():
        write(ROOT / "runbooks" / f"{name}.md", text)
    write(ROOT / "api" / "openapi.json", json.dumps(openapi_spec(), indent=2))
    print(f"wrote data under {ROOT}")


if __name__ == "__main__":
    main()
