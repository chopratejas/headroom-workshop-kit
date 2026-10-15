# Headroom hands-on kit

## In the workshop sandbox (recommended)

You get a sandbox with Headroom Enterprise, Claude Code, Codex and three real MCP
servers (GitHub read-only, Context7, Fetch) already installed. Open the link you
were given, then:

```bash
gh auth login -w && exec bash   # your GitHub, used read-only by the github MCP server
headroom login                  # signs this sandbox in to the Headroom control plane
headroom start                  # starts the proxy: compression, tool search, routing, observability
claude                          # log in with your own Claude account
```

Then pick a task from [TASKS.md](TASKS.md). Check your savings with
`headroom status` or `curl -s localhost:8787/stats | jq '.tokens'`, and look for
your sandbox in the Headroom portal fleet view.

Facilitators: `sandbox/workshop.py` builds the snapshot and creates one sandbox
per attendee (see the docstring).

## On your own laptop (open source)

See what your coding agent actually sends to the model, and how much of it
Headroom removes. You point Claude Code or Codex at Headroom, give it real work
from [TASKS.md](TASKS.md), and watch the numbers.

The kit is a small fake company, Acme Shop: a day of production logs with an
outage in it, alerts, deploys, traces, metrics, orders, GitHub issues, Kubernetes
pods, a CI log, an API spec, and a pricing bug in `src/`. An MCP server,
`acme_mcp.py`, serves it to your agent the way your Datadog, PagerDuty, GitHub,
kubectl and CI tools would. Four more tools call live public sources (OSV.dev,
Hacker News, arXiv, PyPI) for research tasks. Plain Python 3.9+, no installs.

## Set up (10 minutes)

You need Claude Code or Codex installed and logged in (subscription or API key).

**1. Install Headroom.** Do this before the session; it downloads about 600 MB.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh          # Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
uv tool install --python 3.12 "headroom-ai[proxy]"
headroom doctor --network                                # checks TLS to each provider (useful behind Zscaler)
```

**2. Get the kit.**

```bash
git clone https://github.com/chopratejas/headroom-workshop-kit
cd headroom-workshop-kit
```

**3. Use the hosted Kompress model.** The facilitator shows the two values on screen.

```bash
export HEADROOM_KOMPRESS_ENDPOINT=<shown on screen>
export HEADROOM_KOMPRESS_ENDPOINT_TOKEN=<shown on screen>
# Windows PowerShell: $env:HEADROOM_KOMPRESS_ENDPOINT="..."; $env:HEADROOM_KOMPRESS_ENDPOINT_TOKEN="..."
```

**4. Give your agent the Acme tools.**

```bash
claude mcp add -s user acme -- python3 "$PWD/acme_mcp.py"   # Claude Code
codex mcp add acme -- python3 "$PWD/acme_mcp.py"            # Codex
```

**5. Start your agent through Headroom**, from this folder, in the same terminal as step 3.

```bash
headroom wrap claude --code-memory none
# or
headroom wrap codex
```

Open the dashboard next to your terminal: http://127.0.0.1:8787/dashboard.
Then pick a task from [TASKS.md](TASKS.md).

## Reading your numbers

| Where | What it shows |
|---|---|
| Proxy log (the wrap terminal, or `~/.headroom/logs`) | One line per request: `Pipeline complete: X -> Y tokens`. This is compression, measured on your request. |
| `headroom perf` | Which compressor ran on what content, and how much it removed |
| `curl -s localhost:8787/stats` | Totals, prompt-cache hits, cost with and without Headroom |
| Dashboard | The same totals, live |
| `headroom savings` | Your running total across sessions |

The dashboard's headline total also counts tool definitions Headroom deferred,
which is an estimate. For compression alone, read the `Pipeline complete` lines.

## What to expect

Measured on this kit with `headroom-ai` 0.41.0 and the hosted Kompress model:
each tool's real output sent through the proxy as a Claude Code tool result
(reproduce with `python3 bench/measure.py`, see the file for how).

| Tool output | Tokens before | After | Saved |
|---|---:|---:|---:|
| Deploy history (JSON) | 13,993 | 5,244 | 63% |
| Latency metrics (rows) | 26,176 | 10,719 | 59% |
| Orders API (JSON) | 23,970 | 10,491 | 56% |
| Alerts (JSON) | 14,216 | 6,280 | 56% |
| GitHub issues (JSON) | 18,661 | 8,413 | 55% |
| OSV vulnerabilities (live JSON) | 16,091 | 7,748 | 52% |
| OpenAPI spec | 8,012 | 3,947 | 51% |
| Traces (nested JSON) | 12,368 | 7,405 | 40% |
| Hacker News (live JSON) | 18,732 | 12,248 | 35% |
| Kubernetes pods (nested JSON) | 15,881 | 11,006 | 31% |
| CI log | 19,212 | 14,530 | 24% |
| PyPI metadata (live JSON) | 23,846 | 18,860 | 21% |
| Raw service logs | 15,682 | 14,218 | 9% |
| arXiv feed (XML) | 13,259 | 13,259 | 0% |
| Customer CSV | 12,108 | 12,108 | 0% |
| **All 15** | **252,207** | **156,476** | **38%** |

Repetitive structured data compresses most; feeds and unique rows barely move.
Over a long task the agent calls tools dozens of times, so the totals add up.

## Things to know

- **Your files stay local.** Compression runs on your laptop. With the hosted
  Kompress model, text that Headroom sends to Kompress goes to that endpoint
  and back; nothing is stored there. Originals stay on your machine for
  `headroom_retrieve`.
- **Telemetry.** An anonymous usage counter is on by default.
  `headroom telemetry --show` prints exactly what it sends (counts and model
  ids, never prompts or code). `export HEADROOM_BEACON=off` turns it off.
- **Claude Code's own Read and Grep tools are never compressed.** Headroom
  works on tool results and command output; that is where agents spend context.
- **Reset the kit:** `git checkout -- . && git clean -fd`.

## Before you leave

```bash
headroom savings                  # your number
headroom unwrap codex             # if you used Codex: restores ~/.codex/config.toml
claude mcp remove -s user acme    # or: codex mcp remove acme
```
