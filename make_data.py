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


def main() -> None:
    rng = random.Random(SEED)
    write(ROOT / "logs" / "checkout-2026-10-13.log", checkout_log(rng))
    write(ROOT / "ci" / "build-1234.log", ci_log(rng))
    write(ROOT / "api" / "orders.json", json.dumps(orders(rng), indent=2))
    write(ROOT / "api" / "github_issues.json", json.dumps(issues(rng), indent=2))
    write(ROOT / "k8s" / "pods.json", json.dumps(pods(rng), indent=2))
    latency_csv(rng, ROOT / "metrics" / "latency.csv")
    customers_csv(rng, ROOT / "private" / "customers.csv")
    print(f"wrote data under {ROOT}")


if __name__ == "__main__":
    main()
