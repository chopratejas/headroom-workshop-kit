# Tasks

Pick any task, paste the prompt into Claude Code (or Codex), and let the agent
work. Every task uses real MCP servers on real data:

- **github**: read-only access to public repositories (issues, pull requests, CI runs, code)
- **context7**: current documentation for thousands of libraries
- **fetch**: any public web page

When it finishes, check your savings:

```bash
headroom savings
curl -s localhost:8787/stats | jq '.tokens'
```

and watch your sandbox appear in the Headroom portal's fleet view.

| Track | Tasks | What the agent reads |
|---|---|---|
| [SRE and incidents](#sre-and-incidents) | 1–8 | CI logs, issue threads, real postmortems |
| [Research](#research) | 9–16 | docs, release notes, papers, web pages |
| [Engineering leadership](#engineering-leadership) | 17–22 | PR history, review load, roadmaps |
| [Build something new](#build-something-new) | 23–28 | library docs, specs, example repos |
| [Open source due diligence](#open-source-due-diligence) | 29–32 | whole-project health |

Tasks take 5 to 15 minutes. Longer tasks read more and show more savings.

---

## SRE and incidents

### 1. Why is CI failing?
**What it does:** finds the most recent failed CI run in a big project, reads the job logs, and explains the failure.
```
Using the github tools, find the three most recent failed GitHub Actions workflow runs in kubernetes/kubernetes. For each, read the failing job's logs and explain the root cause in two sentences. Is any failure flaky rather than a real bug?
```

### 2. Triage a flaky test
**What it does:** reads the long tail of "flaky test" issues and finds the patterns.
```
Search open issues in kubernetes/kubernetes labelled kind/flake. Read the 15 most recently updated, including their comments. Group them by root cause, and tell me which three a team should fix first and why.
```

### 3. Learn from a real outage
**What it does:** reads a full public postmortem and turns it into lessons for your org.
```
Fetch https://blog.cloudflare.com/post-mortem-on-cloudflare-control-plane-and-analytics-outage/ and read it fully. Write a one-page summary: timeline, root cause, why recovery took so long, and five concrete checks I should run on my own infrastructure this quarter.
```

### 4. Compare outage patterns
**What it does:** reads GitHub's real incident feed and finds what keeps going wrong.
```
Fetch https://www.githubstatus.com/api/v2/incidents.json (GitHub's incident feed, raw JSON). Classify every incident in it by affected service and cause, using the incident updates. Which services fail most often, and what does that suggest about their architecture?
```

### 5. Production incident in an issue tracker
**What it does:** reconstructs an incident from a long, noisy issue thread.
```
In vercel/next.js, find the most-commented open bug report from the last 60 days. Read the whole thread. Reconstruct what users experienced, what the maintainers learned, the current workaround, and whether a fix has landed.
```

### 6. Write the postmortem template
**What it does:** studies several real postmortems and writes a better template.
```
Fetch these and read them fully: https://sre.google/sre-book/example-postmortem/ , https://blog.cloudflare.com/post-mortem-on-cloudflare-control-plane-and-analytics-outage/ and https://github.blog/news-insights/company-news/oct21-post-incident-analysis/ . Compare their structure, then write a postmortem template that takes the best of each, with a short explanation for every section.
```

### 7. Review a risky change
**What it does:** reviews a large real pull request the way a senior SRE would.
```
In prometheus/prometheus, find the largest merged pull request from the last 30 days (by lines changed). Read its diff and review discussion. What could go wrong in production, how would you roll it out, and what would you monitor?
```

### 8. Build an on-call runbook from issues
**What it does:** mines real operational issues into a runbook.
```
Search open and closed issues in grafana/loki mentioning "out of memory" or "OOM". Read the 10 most relevant with comments. Write a runbook: symptoms, how to confirm, mitigations that worked, and settings to tune.
```

---

## Research

### 9. What changed in a framework this year?
**What it does:** reads current docs and release notes to brief you on a framework.
```
Use context7 to read the current Next.js documentation on caching and the App Router, and use the github tools to read the release notes for every Next.js release in the last six months. Brief me: what changed, what breaks on upgrade, and what a team on Next.js 14 should do.
```

### 10. Choose between two libraries
**What it does:** compares two libraries on docs, activity and open problems.
```
Compare FastAPI and Litestar for a new internal API platform. Use context7 for both docs, and the github tools for release cadence, open issue counts, and the most-discussed open issues. Give me a recommendation with the three facts that decided it.
```

### 11. Read a spec so you don't have to
**What it does:** reads a real protocol spec and explains what matters.
```
Fetch the Model Context Protocol specification at https://modelcontextprotocol.io/specification/2025-06-18 and the pages it links to for authorization and transports. Explain the security model to a CTO: what an MCP server can do, where the trust boundaries are, and what policies we should set before allowing MCP servers company-wide.
```

### 12. Track an emerging standard
**What it does:** follows a fast-moving open-source project through its issues and PRs.
```
Using the github tools on modelcontextprotocol/modelcontextprotocol, read the open proposals and the most active discussions from the last 60 days. What is the community debating, what is likely to change, and how should we prepare?
```

### 13. Literature review
**What it does:** reads papers on a topic and builds a reading list.
```
Fetch https://export.arxiv.org/api/query?search_query=all:%22context%20compression%22%20AND%20all:LLM&sortBy=submittedDate&max_results=30 and read the results. Pick the eight most relevant papers on context compression for LLM agents, fetch each abstract page, and give me a reading list with one line on each contribution.
```

### 14. Upgrade risk report
**What it does:** works out what a major upgrade would cost your team.
```
We run Pydantic v1 across many services. Use context7 for the Pydantic v2 migration guide and the github tools on pydantic/pydantic for open migration issues. Estimate the effort per service, list the changes that break silently, and propose a migration plan.
```

### 15. Security advisories for a stack
**What it does:** reads real security advisories for popular projects.
```
Using the github tools, read the published security advisories for django/django, pallets/flask and psf/requests. Summarize every advisory from the last two years by severity, affected versions and fix, and tell me which ones a typical company is most likely still exposed to.
```

### 16. Market scan
**What it does:** reads vendors' own pages to map a market.
```
Fetch the home pages and pricing pages of LiteLLM, Portkey, Kong AI Gateway and Cloudflare AI Gateway. Build a comparison table: deployment model, pricing, caching, guardrails, and observability. Where are the gaps?
```

---

## Engineering leadership

### 17. Who reviews what?
**What it does:** analyzes review load across a real team.
```
In hashicorp/terraform, look at the last 50 merged pull requests. Who reviewed them, how long did reviews take, and how many review rounds did each need? Is review load concentrated on a few people? Show a table.
```

### 18. Where does time go?
**What it does:** measures cycle time from real PR history.
```
For the last 40 merged pull requests in astral-sh/uv, compute time from open to first review and from open to merge. Which kinds of change are slowest, and what would you change in the process?
```

### 19. Read a roadmap from the work
**What it does:** infers what a team is building from issues and PRs alone.
```
Using only the github tools on open-telemetry/opentelemetry-collector, infer the team's roadmap for the next six months from open issues, milestones and recent PRs. What are they betting on, and what are they neglecting?
```

### 20. Onboard into a codebase
**What it does:** builds an onboarding guide for a big unfamiliar repository.
```
I am joining the team that maintains grafana/grafana. Using the github tools, read the README, CONTRIBUTING guide, the top-level directory structure and the 20 most recent merged PRs. Write my first-week onboarding guide: architecture, where things live, how changes get made, and five good first issues.
```

### 21. Quality trend
**What it does:** reads bug reports over time to judge whether quality is improving.
```
In microsoft/vscode, compare bugs opened in the last 30 days with the same 30 days a year ago: volume, areas affected, and time to first response. Is quality improving? Back every claim with numbers.
```

### 22. Contributor health
**What it does:** checks bus factor and community health of a dependency.
```
For psf/requests and encode/httpx, use the github tools to check who has merged code in the last year, how fast issues get a response, and how many open PRs are stale. Which is the safer long-term dependency?
```

---

## Build something new

### 23. Bootstrap a service from docs
**What it does:** builds a working service using current documentation only.
```
Use context7 to read the current FastAPI and SQLModel docs. Then build a small orders API in ~/build/orders with create, list and get endpoints, SQLite storage, and tests. Run the tests.
```

### 24. Write an MCP server
**What it does:** builds a real MCP server from the official spec and SDK docs.
```
Use context7 for the MCP Python SDK docs and fetch https://modelcontextprotocol.io/specification/2025-06-18 for the protocol. Build an MCP server in ~/build/notes-mcp that stores and searches notes, with tests. Run the tests.
```

### 25. Copy a pattern from a great repo
**What it does:** studies how a famous project solves a problem, then applies it.
```
Using the github tools, study how astral-sh/ruff structures its CLI and configuration loading. Then write a Python CLI skeleton in ~/build/cli that follows the same patterns (config file discovery, overrides, clear errors), with tests. Run them.
```

### 26. Generate a client from an OpenAPI spec
**What it does:** reads a real API spec and writes a typed client.
```
Fetch the GitHub REST API OpenAPI description for the issues endpoints from https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json (read only the parts you need). Write a typed Python client for listing, creating and commenting on issues in ~/build/gh_client, with tests that do not touch the network.
```

### 27. Terraform module from docs
**What it does:** writes infrastructure code from the provider's current docs.
```
Use context7 for the current Terraform AWS provider docs. Write a Terraform module in ~/build/tf-service that creates an ECS Fargate service behind an ALB with autoscaling and least-privilege IAM. Run terraform fmt if available and explain each design choice.
```

### 28. Dashboard for a public dataset
**What it does:** builds a single-page dashboard from live public data.
```
Using the github tools, collect the last 90 days of issues opened and closed in kubernetes/kubernetes. Build ~/build/dashboard/index.html, one self-contained file that charts opened vs closed per week and the median time to close. Embed the data in the page.
```

---

## Open source due diligence

### 29. Should we adopt this project?
**What it does:** a full health check of an open-source project.
```
We are considering adopting langchain-ai/langgraph in production. Using github, context7 and fetch, assess release stability, breaking-change history, issue response times, security advisories and documentation quality. Give a go/no-go with conditions.
```

### 30. License and supply chain review
**What it does:** checks licenses and dependencies of a project.
```
For vercel/ai, use the github tools to read its package manifests and the licenses of its direct dependencies. Flag anything with a copyleft license or an unmaintained dependency, and summarize the supply-chain risk.
```

### 31. Fork or contribute?
**What it does:** decides whether to fork a project or work upstream.
```
We need a feature in BerriAI/litellm that does not exist yet: per-team budget alerts by email. Search its issues and PRs for prior discussion, read how maintainers respond to feature PRs, and recommend whether to contribute upstream or maintain a fork.
```

### 32. Compare two projects head to head
**What it does:** side-by-side comparison of two competing projects.
```
Compare temporalio/temporal and restatedev/restate for durable workflows: architecture (from docs via context7 or fetch), release cadence, open bug counts, and community activity (github). Recommend one for a team of 50 engineers.
```
