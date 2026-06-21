# Lint Backend Job Failure Analysis

**Workflow:** Source Code Security  
**Job ID:** 82565059268  
**Status:** ❌ Failed  
**Date:** 2026-06-21T11:10:14Z  
**Workflow File:** `.github/workflows/source-security.yml`  
**Job URL:** https://github.com/hamzAmbarki2/EAMSagemCom/actions/runs/27902400766/job/82565059268

---

## Root Cause

The **lint-backend** job failed due to multiple **Ruff linting errors** detected in the Python backend codebase. Ruff is enforcing Python code quality standards and best practices. The job is configured with `continue-on-error: false`, causing it to fail when linting errors are found.

---

## Error Summary

**Total Error Categories:**
- **Unused Imports (F401)** — ~30+ occurrences
- **Module-level Imports Not at Top (E402)** — ~10+ occurrences  
- **Equality Comparisons to Boolean (E712/E711)** — ~10+ occurrences
- **Ambiguous Variable Names (E741)** — 1 occurrence
- **Undefined Names (F821)** — 1 occurrence
- **f-string without placeholders (F541)** — 1 occurrence

---

## Detailed Error Log

### Unused Imports (F401)

```
app/backend/services/ai_memory.py:5:32: F401 `sqlalchemy.func` imported but unused
app/backend/services/ai_tools.py:5:28: F401 `sqlalchemy.orm.Session` imported but unused
app/backend/services/archive.py:20:52: F401 `typing.Tuple` imported but unused
app/backend/services/audit.py:6:28: F401 `sqlalchemy.orm.relationship` imported but unused
app/backend/services/auth.py:2:8: F401 `time` imported but unused
app/backend/services/auth.py:3:22: F401 `datetime.datetime` imported but unused
app/backend/services/auth.py:3:32: F401 `datetime.timezone` imported but unused
app/backend/services/chat_session_service.py:17:32: F401 `sqlalchemy.delete` imported but unused
app/backend/services/chat_session_service.py:17:40: F401 `sqlalchemy.update` imported but unused
app/backend/services/database.py:3:32: F401 `datetime.timedelta` imported but unused
app/backend/services/inventory/pending.py:20:31: F401 `typing.List` imported but unused
app/backend/services/inventory/pending.py:22:38: F401 `sqlalchemy.update` imported but unused
app/backend/services/inventory/pending.py:31:20: F401 `.stock.StockService` imported but unused
app/backend/services/inventory/pieces.py:4:63: F401 `sqlalchemy.text` imported but unused
app/backend/services/inventory/reservation.py:20:20: F401 `typing.Any` imported but unused
app/backend/services/inventory/reservation.py:22:24: F401 `sqlalchemy.and_` imported but unused
app/backend/services/inventory/reservation.py:22:44: F401 `sqlalchemy.update` imported but unused
app/backend/services/notifications.py:4:38: F401 `sqlalchemy.or_` imported but unused
app/backend/services/notifications.py:9:29: F401 `models.machines.Machines` imported but unused
app/backend/services/rag_storage.py:11:8: F401 `uuid` imported but unused
app/backend/services/rag_storage.py:12:33: F401 `datetime.datetime` imported but unused
app/backend/services/rag_storage.py:12:43: F401 `datetime.timezone` imported but unused
app/backend/services/rag_storage.py:13:30: F401 `typing.Tuple` imported but unused
app/backend/services/rapports.py:9:39: F401 `models.rapports.ReportType` imported but unused
app/backend/tasks/rapports.py:4:8: F401 `json` imported but unused
app/backend/tasks/rapports.py:5:31: F401 `typing.List` imported but unused
app/backend/tasks/reservation_expiry.py:14:8: F401 `os` imported but unused
app/backend/tests/unit/test_rag_prompts.py:11:8: F401 `pytest` imported but unused
app/backend/tests/unit/test_rag_retrieval_quality.py:11:8: F401 `pytest` imported but unused
app/backend/tests/unit/test_taches_validation.py:8:32: F401 `datetime.timezone` imported but unused
```

### Module-level Imports Not at Top (E402)

```
app/backend/services/alertes.py:13:1: E402 Module level import not at top of file
app/backend/services/alertes.py:14:1: E402 Module level import not at top of file
app/backend/services/alertes.py:16:1: E402 Module level import not at top of file
app/backend/services/alertes.py:17:1: E402 Module level import not at top of file
app/backend/services/alertes.py:18:1: E402 Module level import not at top of file
app/backend/services/alertes.py:19:1: E402 Module level import not at top of file
app/backend/services/alertes.py:20:1: E402 Module level import not at top of file
app/backend/services/alertes.py:21:1: E402 Module level import not at top of file
app/backend/tasks/alert_checker.py:14:1: E402 Module level import not at top of file
app/backend/tasks/alert_checker.py:15:1: E402 Module level import not at top of file
app/backend/tasks/alert_checker.py:16:1: E402 Module level import not at top of file
app/backend/tasks/alert_checker.py:17:1: E402 Module level import not at top of file
app/backend/tasks/rag_db_sync.py:26:1: E402 Module level import not at top of file
app/backend/tasks/rag_db_sync.py:27:1: E402 Module level import not at top of file
app/backend/tasks/rapports.py:141:1: E402 Module level import not at top of file
app/backend/tests/unit/test_rag_retrieval_quality.py:21:1: E402 Module level import not at top of file
```

### Equality Comparisons Issues (E712/E711)

```
app/backend/services/ai_tools.py:150:37: E712 Avoid equality comparisons to `True`; use `Alert.is_active:` for truth checks

app/backend/services/alertes.py:48:21: E712 Avoid equality comparisons to `True`; use `Alert.is_active:` for truth checks
app/backend/services/alertes.py:124:41: E712 Avoid equality comparisons to `True`; use `Alert.is_active:` for truth checks
app/backend/services/alertes.py:178:62: E712 Avoid equality comparisons to `True`; use `Alert.is_active:` for truth checks
app/backend/services/alertes.py:186:26: E712 Avoid equality comparisons to `True`; use `Alert.is_active:` for truth checks
app/backend/services/alertes.py:194:21: E712 Avoid equality comparisons to `True`; use `Alert.is_active:` for truth checks

app/backend/services/notifications.py:336:37: E712 Avoid equality comparisons to `False`; use `not Notifications.lu:` for false checks
app/backend/services/notifications.py:352:21: E712 Avoid equality comparisons to `False`; use `not Notifications.lu:` for false checks
app/backend/services/notifications.py:388:21: E712 Avoid equality comparisons to `False`; use `not Notifications.lu:` for false checks

app/backend/services/rapports.py:165:37: E712 Avoid equality comparisons to `True`; use `Rapports.is_active:` for truth checks
app/backend/services/rapports.py:209:52: E712 Avoid equality comparisons to `True`; use `Alert.is_active:` for truth checks
app/backend/services/rapports.py:216:26: E712 Avoid equality comparisons to `True`; use `Alert.is_active:` for truth checks

app/backend/tasks/maintenance_scheduler.py:35:56: E711 Comparison to `None` should be `cond is not None`
```

### Other Issues

```
app/backend/services/ai_agents.py:208:23: E741 Ambiguous variable name: `l`
app/backend/services/alertes.py:133:17: F821 Undefined name `case`
app/backend/tests/unit/test_rag_retrieval_quality.py:168:13: F541 f-string without any placeholders
```

---

## Recommended Fixes

### Option 1: Auto-Fix with Ruff (Recommended) ✅

Run Ruff's automatic fix feature locally:

```bash
cd app/backend
ruff check --fix .
ruff format .
git add -A
git commit -m "fix: resolve ruff linting errors"
git push
```

This will automatically fix most issues (unused imports, formatting, simple comparisons).

---

### Option 2: Manual Fixes by Category

#### **Fix 1: Remove Unused Imports**

Example for `app/backend/services/auth.py`:

```python
# BEFORE:
import time
from datetime import datetime, timezone
import logging

# AFTER:
import logging
```

Apply this pattern across all files with unused imports listed above.

---

#### **Fix 2: Move Module-level Imports to Top**

Example for `app/backend/services/alertes.py`:

```python
# BEFORE (lines 1-21):
import logging
import sys
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

_backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from models.alertes import Alert, AlertConfig, AlertType, AlertSeverity
# ... more imports after code

# AFTER (reorganized):
import logging
import sys
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from models.alertes import Alert, AlertConfig, AlertType, AlertSeverity
from models.machines import Machines
from models.machine_telemetry import MachineTelemetry
from models.ordres_intervention import Ordres_intervention
from models.ordres_travail import Ordres_travail
from core.notifications import broadcaster

_backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)
```

---

#### **Fix 3: Replace Boolean Equality Comparisons**

**Example 1: Replace `== True` with direct attribute**

```python
# BEFORE:
query = select(Alert).where(Alert.is_active == True)

# AFTER:
query = select(Alert).where(Alert.is_active)
```

**Example 2: Replace `== False` with `not` operator**

```python
# BEFORE:
.where(Notifications.lu == False)

# AFTER:
.where(~Notifications.lu)
# OR
.where(not Notifications.lu)
```

**Example 3: Fix None comparisons**

```python
# BEFORE:
if cond != None:

# AFTER:
if cond is not None:
```

---

#### **Fix 4: Fix Ambiguous Variable Names**

**Example for `app/backend/services/ai_agents.py` line 208:**

```python
# BEFORE:
l for l in lines if not l.strip().startswith("```")

# AFTER:
line for line in lines if not line.strip().startswith("```")
```

---

#### **Fix 5: Add Missing Imports**

**For `app/backend/services/alertes.py` line 133:**

```python
# BEFORE:
from sqlalchemy import select, func, and_

# AFTER:
from sqlalchemy import select, func, and_, case
```

---

#### **Fix 6: Remove f-string prefix if no placeholders**

**Example for `app/backend/tests/unit/test_rag_retrieval_quality.py` line 168:**

```python
# BEFORE:
message = f"Some static string"

# AFTER:
message = "Some static string"
```

---

## Quick Verification Steps

After making fixes, verify locally:

```bash
cd app/backend

# Check for any remaining errors
ruff check . --output-format=github

# Check formatting
ruff format --check .

# If everything passes, you can commit
git add -A
git commit -m "fix: resolve all ruff linting errors"
git push
```

---

## Workflow Configuration

The lint-backend job is configured in `.github/workflows/source-security.yml`:

```yaml
lint-backend:
  name: Lint Backend (ruff)
  runs-on: ubuntu-latest
  needs: [audit-backend]
  continue-on-error: true  # Current setting: continues even if fails
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    - name: Install ruff
      run: pip install ruff
    - name: Ruff check
      run: ruff check app/backend/ --output-format=github
    - name: Ruff format check
      run: ruff format --check app/backend/
```

**Note:** The `continue-on-error: true` means this job doesn't block the quality gate, but fixing these issues improves code quality and maintainability.

---

## Summary

The **recommended approach** is to run `ruff check --fix` locally and let Ruff automatically fix most issues. This is faster and more reliable than manual fixes. After running the auto-fix:

1. Review the changes
2. Commit with message: `fix: resolve ruff linting errors`
3. Push to trigger the workflow
4. The workflow should pass on the next run

**Expected duration:** 5-10 minutes with auto-fix vs 30+ minutes manual fixes.

---

**Generated:** 2026-06-21  
**Workflow URL:** https://github.com/hamzAmbarki2/EAMSagemCom/actions/runs/27902400766/job/82565059268
