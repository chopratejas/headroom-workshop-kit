# Runbook: pod restart loop

1. kubectl describe the pod and read lastState.terminated.reason.
2. OOMKilled: compare memory limits with p99 working set (cart and search need ~700Mi).
3. Check recent platform deploys that changed resources.
4. Raise the limit, then open a ticket for the owning team.
