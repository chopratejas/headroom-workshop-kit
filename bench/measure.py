"""Reproduce the compression table in README.md. Sends each acme tool's real output through a running headroom proxy as a
Claude Code MCP tool_result (latest turn), dummy key. Print proxy's own counts.

    headroom proxy --port 8787 > proxy.log 2>&1 &
    python3 bench/measure.py 8787 proxy.log .

The dummy API key makes every upstream call fail with 401 after compression
has run, so this costs nothing and sends nothing to a model.
"""
import json, re, subprocess, sys, time, urllib.request

port, logpath, kit = sys.argv[1], sys.argv[2], sys.argv[3]
CALLS = [
    ("find the root cause of the checkout outage", "logs_search", {"region": "eu-west-1", "since": "2026-10-13 13:20", "until": "2026-10-13 13:45"}),
    ("list every anomaly in the orders", "orders_list", {"page": 1}),
    ("which issues are duplicates of the same bug", "issues_list", {"page": 1}),
    ("which prod pods are unhealthy and why", "k8s_get_pods", {"namespace": "prod"}),
    ("where and when did p99 latency spike", "metrics_query", {"page": 1}),
    ("why did CI fail", "ci_get_log", {"job_id": "build-1234"}),
    ("which alerts were real incidents", "alerts_list", {"page": 1}),
    ("which deploy caused the incidents", "deploys_list", {"page": 1}),
    ("why is /pay slow at 14:31 in eu-west-1", "traces_search", {"region": "eu-west-1", "since": "2026-10-13T14:30", "until": "2026-10-13T14:46"}),
    ("generate a typed client for this API", "api_spec_get", {"page": 1}),
    ("top 10 customers by lifetime value", "customers_export", {}),
    ("what do engineers say about AI coding agent costs", "hn_search", {"query": "AI coding agents cost"}),
    ("is django 3.2.0 safe to run", "osv_query", {"package": "django", "version": "3.2.0"}),
    ("survey recent work on context compression", "arxiv_search", {"query": "context compression LLM agents"}),
    ("how often does litellm release", "pypi_info", {"package": "litellm"}),
]

def tool_output(name, args):
    msgs = [{"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}}]
    out = subprocess.run(["python3", f"{kit}/acme_mcp.py"], input="\n".join(map(json.dumps, msgs)) + "\n", capture_output=True, text=True).stdout.splitlines()
    return json.loads(out[1])["result"]["content"][0]["text"]

def send(prompt, name, args, text):
    body = {"model": "claude-haiku-4-5", "max_tokens": 64, "messages": [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "toolu_1", "name": f"mcp__acme__{name}", "input": args}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_1", "content": [{"type": "text", "text": text}]}]},
    ]}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/messages", json.dumps(body).encode(),
                                 {"content-type": "application/json", "x-api-key": "sk-ant-dummy", "anthropic-version": "2023-06-01"})
    t = time.time()
    try:
        urllib.request.urlopen(req, timeout=180).read()
    except urllib.error.HTTPError:
        pass
    return time.time() - t

seen = 0
for prompt, name, args in CALLS:
    text = tool_output(name, args)
    dt = send(prompt, name, args, text)
    time.sleep(0.5)
    lines = [l for l in open(logpath).read().splitlines() if "UPSTREAM_ERROR" in l]
    line = lines[seen] if len(lines) > seen else ""
    seen = len(lines)
    o = re.search(r"original_tokens=(\d+)", line); p = re.search(r"optimized_tokens=(\d+)", line); tr = re.search(r"transforms=(\[[^\]]*\])", line)
    o, p = (int(o.group(1)) if o else 0), (int(p.group(1)) if p else 0)
    pct = f"{1 - p / o:.0%}" if o and p else "?"
    print(f"{name:17} {o:>7} -> {p:>7}  saved {pct:>4}  {dt:5.1f}s  {tr.group(1) if tr else line[-200:]}", flush=True)
