# Tasks

Pick any task. Paste the prompt into Claude Code or Codex (started with
`headroom wrap`, see [README](README.md)), let the agent work, then look at the
Headroom dashboard: http://127.0.0.1:8787/dashboard

Every task is real work an engineer would hand an agent: it calls several tools,
reads a lot of output, and has a right answer. The `acme` tools stand in for
your own Datadog, PagerDuty, GitHub, Kubernetes, CI and warehouse. The research
tools call live public sources.

| Track | Tasks | Good for |
|---|---|---|
| [SRE and on-call](#sre-and-on-call) | 1–10 | logs, alerts, deploys, traces, metrics |
| [Research](#research) | 11–17 | live public data: vulnerabilities, Hacker News, arXiv, PyPI |
| [Build something new](#build-something-new) | 18–24 | bootstrapping code from specs and data |
| [Data and product](#data-and-product) | 25–28 | big API responses, analytics |
| [Code and CI](#code-and-ci) | 29–32 | a real bug, tests, CI output |
| [Your own repo](#your-own-repo) | 33–35 | the same thing on your code |

Reset the kit at any time with `git checkout -- . && git clean -fd`.

---

## SRE and on-call

### 1. Find what broke checkout
**What it does:** the agent reads a day of logs, alerts and deploys and finds the change that took checkout down.
```
Checkout had an outage on 2026-10-13. Using the acme tools (logs_search, alerts_list, deploys_list), find the root cause. The errors only show the symptom; find the change that caused it. Give me a timeline with exact timestamps and the evidence for each step.
```

### 2. Explain the payment latency spike
**What it does:** follows a p99 spike from metrics to traces to the deploy behind it.
```
p99 latency on /pay spiked on 2026-10-13. Use metrics_query to find where and when, traces_search to find which span got slow, and deploys_list to find what changed. Explain the cause and how it was resolved.
```

### 3. Stop the crash-looping pods
**What it does:** finds the restarting pods, the reason, and the deploy that caused it, then proposes the fix.
```
Some prod pods keep restarting. Use k8s_get_pods to find which ones and why, then deploys_list to find the change that caused it. Propose the exact Kubernetes resource change to fix it and who should review it.
```

### 4. Audit a week of alert noise
**What it does:** reads 523 alerts and separates the 3 real incidents from the noise.
```
Go through every page of alerts_list for the last week. Which alerts were real incidents and which were noise? Group the noise by title, estimate how many pages per week it costs on-call, and propose which alerts to silence or retune.
```

### 5. Write the postmortem
**What it does:** a full blameless postmortem built from logs, alerts and deploys.
```
Write a blameless postmortem for the 2026-10-13 checkout outage. Include summary, impact (count ERROR lines by region with logs_search), timeline from alerts_list and deploys_list, root cause, what went well, and five action items with owners by team.
```

### 6. Be the on-call engineer
**What it does:** takes a critical alert, follows the runbook, and checks every step against real data.
```
You are on call. Take alert ALRT-79002 from alerts_list. Fetch the matching runbook with runbook_get and follow it step by step, checking each step against traces_search and deploys_list. Tell me what you found at each step and what you would do.
```

### 7. Measure the blast radius
**What it does:** quantifies the outage: duration, failed requests, regions affected.
```
For the 2026-10-13 checkout outage, measure the blast radius with logs_search: when did errors start and stop, how many ERROR and FATAL lines per region, and which endpoints were hit. Show a small table.
```

### 8. Review deploy risk
**What it does:** reads two weeks of deploys and writes a change policy from what went wrong.
```
Review every deploy in deploys_list. Which ones changed config or resources rather than code? Which caused incidents (check alerts_list)? Propose a deploy policy for the riskiest kinds of change.
```

### 9. Write the SLO report
**What it does:** computes p99 per endpoint and region and flags SLO breaches.
```
Our SLO is p99 under 300 ms for every endpoint. Page through metrics_query and report, per region and endpoint, the worst p99 and how many minutes we were in breach. Rank the breaches.
```

### 10. Turn the incident into alerts
**What it does:** writes the monitoring that would have caught this outage earlier.
```
Using the evidence from logs_search, metrics_query and the checkout-errors runbook (runbook_get), write Prometheus alerting rules that would have caught the 2026-10-13 outage before customers did, plus an updated runbook. Save them to alerts/checkout.rules.yml and runbooks/checkout-errors.md.
```

---

## Research

### 11. Is this old service safe to run?
**What it does:** checks 20 pinned dependencies against the live OSV vulnerability database.
```
research/requirements-legacy.txt lists the dependencies of a service nobody has updated since 2021. Check every package with osv_query (all pages). Rank the packages by their worst vulnerability, and write an upgrade plan in the order I should do it.
```

### 12. What are engineers saying?
**What it does:** researches live Hacker News discussion and summarizes the themes.
```
Use hn_search (several queries and pages) to research what engineers say about the cost of AI coding agents. Summarize the five strongest themes, with two story links each, and say which themes matter to a CTO.
```

### 13. Literature scan
**What it does:** builds a reading list from live arXiv results.
```
Use arxiv_search (several queries) to find recent papers on context compression and memory for LLM agents. Give me a reading list of the ten most useful, one line each on what it contributes, grouped by approach.
```

### 14. Choose an LLM gateway
**What it does:** compares open-source gateways on release health and community signal.
```
Compare litellm, portkey-ai and aisuite using pypi_info (release cadence, latest version, license, Python support) and hn_search (what people say). Recommend one for a 300-engineer company and say what would change your mind.
```

### 15. Plan a framework upgrade
**What it does:** works out what upgrading Django 3.2.0 fixes and what it risks.
```
We run django 3.2.0. Use osv_query to list the vulnerabilities we carry, and pypi_info to find the release history. Propose an upgrade path (which versions to stop at), what each step fixes, and the risks.
```

### 16. Map the landscape
**What it does:** maps vendors and projects in a market from live discussion.
```
Use hn_search to map the landscape of LLM gateways and AI cost-control tools: which products come up, what people praise and complain about, and where the gaps are. Present it as a table.
```

### 17. Tech radar for your stack
**What it does:** release health and known vulnerabilities for libraries your teams use.
```
Pick the five Python libraries my team depends on most: requests, sqlalchemy, celery, pydantic and fastapi. For each, use pypi_info and osv_query on its latest version and on a version from two years ago. Write a one-page tech radar: adopt, hold, or replace.
```

---

## Build something new

### 18. Generate an API client
**What it does:** reads a whole OpenAPI spec and writes a typed client with tests.
```
Read every page of api_spec_get and generate a typed Python client for the Acme Order Service in client/acme_client.py (standard library only), plus tests in tests/test_client.py that run without a network. Run the tests.
```

### 19. Build an on-call dashboard
**What it does:** turns live metrics into a single-page dashboard.
```
Page through metrics_query and build dashboard/index.html, one self-contained file, that shows p99 latency over time per region for /pay and /checkout and highlights SLO breaches (300 ms). Embed the data in the page.
```

### 20. Bootstrap an anomaly detector
**What it does:** writes, tests and runs a script that finds bad orders.
```
Look at several pages of orders_list to learn what normal orders look like. Then write tools/order_anomalies.py that reads data/api/orders.json and flags anomalies (negative totals, wrong currency, duplicate ids, outlier quantities), with tests. Run it and show what it finds.
```

### 21. Stand up a mock service
**What it does:** builds a local mock of the API from its spec so other teams can develop against it.
```
Using every page of api_spec_get, build a mock server in mock/server.py (standard library http.server only) that serves the /v1/orders endpoints from data/api/orders.json with paging and filters from the spec. Start it, curl two endpoints, and show the output.
```

### 22. Write an ops CLI
**What it does:** a small command-line tool for alerts and deploys, designed from the real data.
```
Look at alerts_list and deploys_list, then write acmectl.py, a CLI with subcommands `alerts --severity X --since T` and `deploys --service X` that reads data/ops/*.json. Add --help text and tests, and run a few commands.
```

### 23. Write data contracts
**What it does:** infers schemas from real API data and validates every record.
```
From orders_list, issues_list and alerts_list, infer a JSON Schema for each record type and save them in contracts/. Then write contracts/validate.py that checks every record in data/ against them and reports violations. Run it.
```

### 24. Onboard a new SRE
**What it does:** explores everything in the kit and writes the onboarding guide.
```
A new SRE starts Monday. Explore every acme tool, the runbooks, the code in src/ and the data, then write ONBOARDING.md: what each system is, how to investigate an incident here, and the three incidents from 2026-10-12 and 2026-10-13 as worked examples.
```

---

## Data and product

### 25. Find the bad orders
**What it does:** reads all 3,000 orders and finds the four hidden anomalies.
```
Page through ALL orders with orders_list (every page) and list every anomaly you find, with order ids and why each is wrong.
```

### 26. Revenue by region
**What it does:** computes revenue from the largest payload in the kit.
```
Using every page of orders_list, compute total revenue by region and by status, and the top five customers by spend. Show tables.
```

### 27. From duplicate bugs to the code
**What it does:** groups duplicate bug reports, then finds the bug they describe.
```
Go through every page of issues_list. Which issues describe the same underlying bug? Group the duplicates, then find the cause in src/ and explain it in two sentences.
```

### 28. Triage the backlog
**What it does:** turns 250 issues into a prioritized plan.
```
From every page of issues_list, summarize open issues by label and endpoint. Which five should we fix first, and why? Which can we close?
```

---

## Code and CI

### 29. Fix the bug end to end
**What it does:** runs the tests, finds the bug, fixes it, proves it.
```
Run the tests with `uv run --with pytest python -m pytest -q` (or `python3 -m pytest -q`), find the bug, fix it, and rerun until everything passes. Explain the fix.
```

### 30. Why did CI fail?
**What it does:** reads a long CI log and ties the failure to a line of code.
```
Fetch the CI log for build-1234 with ci_get_log. Why did the build fail? Find the line in src/ that produces the wrong value and show the arithmetic.
```

### 31. Tests that would have caught it
**What it does:** writes the missing tests, then proves they catch the bug.
```
Add parametrized tests for discounted_subtotal and total_with_tax covering every combination of loyalty, coupon and region. Run them against the current code and show which fail.
```

### 32. Add multi-currency support
**What it does:** a real feature change, motivated by the EUR order in the data.
```
orders_list contains an order in EUR. Extend src/shop/pricing.py to support EUR and GBP carts with per-currency rounding, update the tests, and run them.
```

---

## Your own repo

Run `headroom wrap claude` (or `codex`) from inside one of your own repositories.
Ask for bash explicitly: Claude Code's built-in Read and Grep results are never
compressed, but command output is.

### 33. Your test suite
```
Run this project's full test suite with bash and summarize the failures, grouped by cause, with the fix you would try first for each.
```

### 34. What changed this month
```
Run `git log --stat --since="30 days ago"` with bash and summarize what changed, by area and by author, and point out anything risky.
```

### 35. Your dependency risk
```
Find this project's dependency manifest. For each direct Python dependency, use osv_query on the pinned version and summarize known vulnerabilities, worst first.
```
