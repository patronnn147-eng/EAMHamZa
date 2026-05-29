# Post-Maintenance Recovery — End-to-End Test (Machine #10)

Three SQL phases seed machine #10 to validate the Recovery feature without
touching the UI for writes. Observe via curl or visit the machine page after
each phase.

## Prerequisites

- Stack up: `docker compose up -d`
- Migration applied: `alembic_version = add_health_snapshots`
- ML microservice running: `asset_management_ml_service` in `docker ps`
- Machine #10 has 0 prior WOs and 0 prior telemetry rows (default after clean DB)

## Run order

```bash
# Phase A — bad telemetry, no WO yet
docker exec -i asset_management_db psql -U postgres -d asset_management \
    < scripts/test_recovery/phase_a_bad_telemetry.sql

curl -s http://localhost:8000/api/v1/ml/machines/10/unified-health \
    | jq '.unified_health_score, .recovery'
# → low score, recovery: null

# Phase B — insert completed WO with low pre/post snapshots
docker exec -i asset_management_db psql -U postgres -d asset_management \
    < scripts/test_recovery/phase_b_completed_wo.sql

curl -s http://localhost:8000/api/v1/ml/machines/10/unified-health \
    | jq '.recovery'
# → status: "No improvement", delta ≈ 0, within_recovery_window: true

# Phase C — healthy post-maintenance telemetry
docker exec -i asset_management_db psql -U postgres -d asset_management \
    < scripts/test_recovery/phase_c_good_telemetry.sql

curl -s http://localhost:8000/api/v1/ml/machines/10/unified-health \
    | jq '.unified_health_score, .recovery'
# → unified_health_score ≥ 75, recovery.status: "Recovered", delta ≥ +40

# Reset for re-run
docker exec -i asset_management_db psql -U postgres -d asset_management \
    < scripts/test_recovery/phase_z_cleanup.sql
```

## Expected outcomes

| After phase | unified_health_score | recovery | UI badge |
|-------------|----------------------|----------|----------|
| A — bad telem only   | ~25–40 | `null` (no completed WO) | none |
| B — + completed WO   | ~25–40 | `status:"No improvement"`, `delta ≈ 0` | red "Aucune amélioration" |
| C — + healthy telem  | ~80–92 | `status:"Recovered"`, `delta ≈ +55` | green "Récupérée (+55 pts)" |

## Frontend verification

After phase C, open `http://localhost:3000/machines/10`:

- **Header**: green "Récupérée (+X pts)" badge next to status/risk badges
- **ML Intelligence tab**: "Post-Maintenance Recovery" card showing Before→Now bar, status badge, days remaining
- **Work Order detail** (click into the test WO): "Impact sur la Santé Machine" card with 4 columns (Avant / À la complétion / Maintenant / Amélioration nette) plus TrendingUp icon

## Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| `recovery` is `null` after Phase B | WO `date_fin` is `NULL` or > 7 days old. Re-run phase_b (it deletes prior). |
| `current_score` is `null` | ML microservice down — `docker compose up -d ml-service`. |
| Score stays low after Phase C | History too short for DST kalman — verify Phase A ran (~30 rows). |
| Frontend badge missing | Hard-reload (Ctrl+Shift+R) — frontend image may be cached. |
| Re-running Phase A errors | It's idempotent — deletes machine-10 telemetry first. Safe to re-run. |
| Want to skip auth on curl | Endpoint is unauthenticated by default in this codebase. If your env enforces auth, add `-H "Authorization: Bearer $TOKEN"`. |

## Reset between runs

```bash
docker exec -i asset_management_db psql -U postgres -d asset_management \
    < scripts/test_recovery/phase_z_cleanup.sql
```

Removes test WO + all machine-10 telemetry. Machine row itself is preserved.
