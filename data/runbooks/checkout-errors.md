# Runbook: checkout error rate high

1. Check payments and checkout logs for timeouts.
2. Check db connection pool saturation (db.pool.active vs db.pool.max_connections).
3. If the pool is saturated, compare db.pool.max_connections with the value in the last known-good config (50 in prod).
4. Roll back the last config sync if it changed pool settings.
5. Page the database on-call if saturation persists after rollback.
