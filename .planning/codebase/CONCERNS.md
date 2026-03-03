# Codebase Concerns

**Analysis Date:** 2026-03-03

## Security Considerations

### Hardcoded JWT Secret Key
- **Risk:** JWT signing key is hardcoded in source code
- **Files:** `app/backend/core/config.py`
- **Current Value:** `jwt_secret_key: str = "tIRsAEcKfeyd8YN2SqdaiKZWCkinh-KcCm96v0PlDfM"`
- **Impact:** Anyone with access to source code can forge JWT tokens
- **Recommendations:** 
  - Move JWT_SECRET_KEY to environment variables only
  - Generate a new secure random key
  - Add validation to fail startup if not provided in production

### Hardcoded Encryption Keys
- **Risk:** Mask encryption key is hardcoded
- **Files:** `app/backend/core/mask_crypto.py`
- **Current Value:** `secret_key = "Mgx@FunctionSea"`
- **Impact:** Sensitive masked data can be decrypted by anyone with source access
- **Recommendations:** 
  - Move to environment variables
  - Use proper secrets management

### Exposed Credentials in Docker Compose
- **Risk:** Multiple credentials hardcoded in docker-compose.yml
- **Files:** `docker-compose.yml`
- **Exposed Secrets:**
  - SMTP password: `krhcqurxeiazyvbt` (line 131)
  - JWT secret fallback: `tIRsAEcKfeyd8YN2SqdaiKZWCkinh-KcCm96v0PlDfM` (line 120)
  - MinIO credentials: `minioadmin` (lines 135-136)
  - pgAdmin password: `admin` (line 99)
- **Impact:** Anyone with access to docker-compose.yml has full system access
- **Recommendations:** 
  - Use `.env` file with environment variable substitution only
  - Never commit credentials to version control
  - Use Docker secrets or external secrets management

### Wide-Open CORS Policy
- **Risk:** CORS allows any origin
- **Files:** `app/backend/main.py`
- **Current Setting:** `allow_origin_regex=r".*"`
- **Impact:** Any website can make authenticated requests to the API
- **Recommendations:** 
  - Restrict to specific frontend domains
  - Use environment variable for allowed origins

### Email Credentials in Source
- **Risk:** Email username and password visible in docker-compose
- **Files:** `docker-compose.yml` (lines 130-131)
- **Impact:** Spam/abuse of email service, reputation damage
- **Recommendations:** 
  - Use app-specific passwords or OAuth
  - Never commit to version control

---

## Tech Debt

### Disabled Validation (Greenlet Spawn Issue)
- **Issue:** Planning validation disabled to isolate async database issue
- **Files:** `app/backend/routers/plannings.py` (lines 518-519)
- **Code:**
  ```python
  # TODO: Temporarily disable validation to isolate greenlet_spawn issue
  # await validate_planning_data(db, data)
  ```
- **Impact:** Invalid planning data can be created without validation
- **Fix approach:** 
  - Investigate and fix the greenlet_spawn issue with SQLAlchemy async
  - Re-enable validation
  - Add integration tests for the validation flow

### Multiple Duplicate MinIO Bucket Creation Scripts
- **Issue:** 7+ nearly identical scripts for creating MinIO buckets
- **Files:**
  - `create_minio_bucket.py`
  - `create_minio_bucket_simple.py`
  - `create_minio_bucket_mc.py`
  - `create_minio_bucket_mc_fixed.py`, `create_minio_bucket_mc_fixed2.py`, `create_minio_bucket_mc_fixed3.py`
  - `create_minio_bucket_manual.py`
  - `create_minio_bucket_mc_docker.py`, `create_minio_bucket_mc_docker_fixed.py`
- **Impact:** Maintenance confusion, inconsistency, potential for wrong script usage
- **Fix approach:** 
  - Consolidate into single script
  - Add proper error handling and logging
  - Keep only the working version

### Disabled Planning Validation Workaround
- **Issue:** Direct database insert bypasses service layer validation
- **Files:** `app/backend/routers/plannings.py` (lines 521-537)
- **Impact:** Business logic inconsistency, potential data integrity issues
- **Fix approach:** 
  - Fix async service layer to work properly
  - Restore proper validation through service layer

---

## Known Issues

### Async SQLAlchemy Greenlet Spawn Issue
- **Symptoms:** Errors related to `greenlet_spawn` when using async database operations
- **Files:** `app/backend/services/plannings.py`, `app/backend/routers/plannings.py`
- **Trigger:** Async database operations in certain contexts
- **Workaround:** 
  - Currently bypassing service layer validation
  - Direct database commits in router
- **Fix approach:** 
  - Review async session management
  - Ensure proper event loop handling
  - Add connection pool configuration

### Role Check Inconsistency
- **Issue:** Role comparison uses string literals instead of enum
- **Files:** `app/backend/dependencies/auth.py`
- **Code:** `if current_user.role not in ['ADMIN', 'CHETOP', 'CHEFTECH']:`
- **Impact:** Potential mismatch with UserRole enum values
- **Fix approach:** Use `UserRole` enum consistently

---

## Test Coverage Gaps

### Minimal Backend Test Suite
- **What's not tested:** Most backend services and routers
- **Files tested:** Only 3 test files in `tests/backend/`
  - `test_ml_prediction.py`
  - `test_failure_probability.py`
  - `test_p2_failure_type.py`
- **Risk:** Breaking changes go undetected, regressions in core functionality
- **Priority:** High
- **Fix approach:** 
  - Add tests for all critical API endpoints
  - Add tests for authentication/authorization
  - Add tests for CRUD operations on all models
  - Add integration tests for service layer

### No Frontend Tests
- **What's not tested:** All React/TypeScript components
- **Risk:** UI bugs, regressions, broken interactions
- **Priority:** Medium
- **Fix approach:** 
  - Add Vitest or Jest test suite
  - Add component tests with React Testing Library
  - Add E2E tests with Playwright/Cypress

---

## Performance Bottlenecks

### Large Model Files in Repository
- **Problem:** ML model files stored in repository
- **Files:** `app/backend/modules/ml/*.pkl`
- **Cause:** Binary files bloating repository
- **Improvement path:** 
  - Use Git LFS for model files
  - Or download models at build time from artifact storage

### No Database Connection Pooling Configuration
- **Problem:** Default SQLAlchemy connection pool settings
- **Files:** `app/backend/core/database.py`
- **Impact:** Performance degradation under load
- **Improvement path:** 
  - Configure pool size based on expected load
  - Add pool pre-warming
  - Configure timeout settings

---

## Fragile Areas

### Complex Dynamic Settings Loading
- **Files:** `app/backend/core/config.py` (lines 59-85)
- **Why fragile:** 
  - Custom `__getattr__` makes settings behavior non-obvious
  - Silent fallback to environment variables can mask misconfiguration
  - Hard to debug when environment variable names don't match expectations
- **Safe modification:** 
  - Add type hints for all expected settings
  - Add explicit validation on startup
  - Document all environment variables
- **Test coverage:** Add startup validation tests

### Multiple Authentication Approaches
- **Files:** 
  - `app/backend/core/auth.py`
  - `app/backend/dependencies/auth.py`
  - `app/backend/modules/auth/auth.py`
  - `app/backend/routers/notifications.py`
- **Why fragile:** 
  - Multiple places where JWT is handled
  - Some routes have custom token extraction (notifications.py)
  - Inconsistent error handling across auth methods
- **Safe modification:** 
  - Centralize all auth logic in dependencies
  - Use dependency injection consistently
  - Add comprehensive auth integration tests

---

## Dependencies at Risk

### Pydantic v1 Compatibility
- **Risk:** Using Pydantic v1 patterns with v2 installed
- **Files:** Throughout backend (schemas, config)
- **Impact:** Potential deprecation warnings, future breaking changes
- **Migration plan:** 
  - Update to Pydantic v2 patterns
  - Use `model_validator`, `field_validator` v2 syntax
  - Test thoroughly before production

### Outdated Celery Configuration
- **Risk:** Celery broker configuration might need updates
- **Files:** `app/backend/core/celery_app.py`
- **Impact:** Message queue issues, task failures
- **Migration plan:** 
  - Review Celery version compatibility
  - Add proper error handling for broker connection
  - Add task monitoring/alerting

---

## Missing Critical Features

### No Rate Limiting
- **Problem:** API has no rate limiting
- **Impact:** DoS vulnerability, abuse potential
- **Blocks:** Production deployment without proper protection

### No Request Logging/Audit Trail
- **Problem:** No comprehensive request logging
- **Impact:** Difficult to debug issues, security auditing limited
- **Blocks:** Compliance requirements, security investigations

### No API Versioning Strategy
- **Problem:** API routes lack versioning
- **Impact:** Breaking changes affect all clients
- **Blocks:** Long-term API stability

### No Comprehensive Error Handling
- **Problem:** Inconsistent error responses across API
- **Impact:** Poor client experience, difficult debugging
- **Blocks:** Professional API documentation

---

## Code Quality Issues

### Duplicate Code Between Modules and Services
- **Files:** 
  - `app/backend/modules/shared/*.py`
  - `app/backend/services/*.py`
- **Issue:** Business logic duplicated between module handlers and service layer
- **Impact:** Maintenance burden, inconsistency risk
- **Fix approach:** 
  - Use service layer as single source of truth
  - Module handlers should only handle HTTP concerns

### Inconsistent Error Message Language
- **Issue:** Mix of French and English error messages
- **Files:** Throughout backend
- **Impact:** User experience inconsistency
- **Fix approach:** Standardize on one language (French based on domain)

### Missing Type Hints
- **Issue:** Some functions lack return type annotations
- **Impact:** Type checking benefits reduced, potential for runtime errors
- **Fix approach:** Add comprehensive type hints throughout

---

*Concerns audit: 2026-03-03*
