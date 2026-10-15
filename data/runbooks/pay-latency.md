# Runbook: /pay p99 latency high

1. Open traces for /pay and find the slowest span.
2. If fraud.check dominates, disable the fraud_sync flag (fraud runs async by default).
3. If psp.charge dominates, check the PSP status page.
4. Roll back the latest payments deploy if it started within 15 minutes of the alert.
