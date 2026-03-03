# Architecture

**Analysis Date:** 2026-03-03

## Pattern Overview

**Overall:** Modular Monolithic with Layered Architecture

This is a FastAPI-based Enterprise Asset Management (EAM) system with a React TypeScript frontend. The backend follows a modular pattern where each domain entity (machines, work orders, interventions, etc.) has its own module with service, model, schema, and router components.

**Key Characteristics:**
- **Modular Structure**: Each domain entity has self-contained modules under `modules/`, `models/`, `services/`, and `schemas/`
- **Layered Architecture**: Clear separation between routes (API), services (business logic), and models (data)
- **Async-First**: Uses Python asyncio with SQLAlchemy async ORM throughout
- **Role-Based Access**: Four user roles (TECHNICIEN, CHEFTECH, CHETOP, ADMIN) with route-level protection

## Layers

### Routes Layer (`routers/`)
- **Purpose**: HTTP endpoint definitions and request handling
- **Location**: `app/backend/routers/`
- **Contains**: FastAPI APIRouter instances with endpoint definitions
- **Depends on**: Services layer
- **Used by**: Auto-discovered by `main.py` and mounted at root level

**Key Routers:**
- `routers/notifications.py` - Notification endpoints
- `routers/plannings.py` - Planning CRUD operations
- `routers/user_approvals.py` - User approval workflows
- `routers/admin_users.py` - Admin user management

### Modules Layer (`modules/`)
- **Purpose**: Business logic and entity-specific API endpoints with full CRUD
- **Location**: `app/backend/modules/`
- **Contains**: APIRouter definitions with embedded Pydantic schemas and service calls
- **Depends on**: Services layer, Models, Schemas
- **Used by**: Auto-included by `main.py`

**Key Modules:**
- `modules/auth/auth.py` - Authentication (register, login, /me)
- `modules/shared/utilisateurs.py` - User entity CRUD
- `modules/shared/machines.py` - Machine entity CRUD
- `modules/shared/ordres_travail.py` - Work order entity CRUD
- `modules/shared/ordres_intervention.py` - Intervention entity CRUD
- `modules/shared/plannings.py` - Planning entity CRUD
- `modules/technicien/technicien.py` - Technician-specific endpoints
- `modules/cheftech/cheftech.py` - ChefTech-specific endpoints
- `modules/ml/router.py` - ML prediction endpoints

### Services Layer (`services/`)
- **Purpose**: Business logic and database operations
- **Location**: `app/backend/services/`
- **Contains**: Service classes that handle database transactions
- **Depends on**: Models, SQLAlchemy AsyncSession
- **Used by**: Modules and routers

**Key Services:**
- `services/utilisateurs.py` - User CRUD operations
- `services/machines.py` - Machine operations
- `services/ordres_travail.py` - Work order operations
- `services/ordres_intervention.py` - Intervention operations
- `services/plannings.py` - Planning operations
- `services/auth.py` - Authentication utilities
- `services/notifications.py` - Notification handling
- `services/storage.py` - Object storage (MinIO/S3)
- `services/rapports.py` - Report generation

### Models Layer (`models/`)
- **Purpose**: SQLAlchemy ORM table definitions
- **Location**: `app/backend/models/`
- **Contains**: SQLAlchemy model classes inheriting from `Base`
- **Depends on**: `core/database.py` (Base)
- **Used by**: Services for database queries

**Key Models:**
- `models/utilisateurs.py` - User table with roles (TECHNICIEN, CHEFTECH, CHETOP, ADMIN)
- `models/machines.py` - Machine/equipment definitions
- `models/ordres_travail.py` - Work order table
- `models/ordres_intervention.py` - Intervention requests
- `models/plannings.py` - Planning/scheduling table
- `models/notifications.py` - Notification records

### Schemas Layer (`schemas/`)
- **Purpose**: Pydantic request/response validation models
- **Location**: `app/backend/schemas/`
- **Contains**: Pydantic BaseModel classes for API validation
- **Depends on**: Pydantic
- **Used by**: Modules and routers for request validation

### Core Layer (`core/`)
- **Purpose**: Application-wide infrastructure
- **Location**: `app/backend/core/`
- **Contains**: Configuration, database connection, authentication, utilities
- **Depends on**: Third-party libraries (FastAPI, SQLAlchemy, JWT)
- **Used by**: All layers

**Key Core Components:**
- `core/config.py` - Settings (Pydantic BaseSettings) with environment variable support
- `core/database.py` - SQLAlchemy async engine and session management
- `core/auth.py` - JWT token creation/validation, password hashing
- `core/email.py` - Email service
- `core/rabbitmq.py` - RabbitMQ message broker
- `core/websocket.py` - WebSocket support

### Dependencies Layer (`dependencies/`)
- **Purpose**: FastAPI dependency injection
- **Location**: `app/backend/dependencies/`
- **Contains**: Depends() functions for request lifecycle
- **Used by**: Routes and modules

**Key Dependencies:**
- `dependencies/auth.py` - `get_current_user()` for JWT authentication
- `dependencies/database.py` - `get_db()` for database session

## Data Flow

**API Request Flow:**

1. **Request Reception**: FastAPI receives HTTP request
2. **Middleware Processing**: CORS middleware (configured in `main.py`)
3. **Route Matching**: Router matches URL path to endpoint
4. **Dependency Injection**: FastAPI injects dependencies (db session, current user)
5. **Schema Validation**: Request body validated against Pydantic schema
6. **Service Execution**: Module calls service layer methods
7. **Database Operation**: Service executes SQLAlchemy async query
8. **Response Construction**: Service returns data, module transforms to response schema
9. **Response Return**: FastAPI serializes response as JSON

**Authentication Flow:**

```
User Login → /api/v1/auth/login → verify_password() → create_access_token()
        ↓
JWT Token returned to client
        ↓
Subsequent requests → Authorization: Bearer <token>
        ↓
get_current_user() dependency → JWT decode → User lookup → UserResponse
        ↓
Protected route receives authenticated user
```

## Key Abstractions

**Entity CRUD Pattern:**
Every domain entity follows this pattern:
- **Model**: SQLAlchemy table definition (`models/xxx.py`)
- **Schema**: Pydantic validation models (defined inline in modules or `schemas/`)
- **Service**: Business logic class (`services/xxx.py`)
- **Module**: APIRouter with endpoints (`modules/xxx.py`)

**Service Class Pattern:**
```python
class XxxService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, data: Dict) -> Xxx:
        # Create logic
    
    async def get_by_id(self, id: int) -> Optional[Xxx]:
        # Get by ID logic
    
    async def get_list(self, skip, limit, **kwargs) -> Dict[str, Any]:
        # Paginated list logic
    
    async def update(self, id: int, data: Dict) -> Optional[Xxx]:
        # Update logic
    
    async def delete(self, id: int) -> bool:
        # Delete logic
```

**Module Router Pattern:**
```python
router = APIRouter(prefix="/api/v1/entities/xxx", tags=["xxx"])

@router.get("", response_model=XxxListResponse)
async def query_xxxs(...):
    service = XxxService(db)
    return await service.get_list(...)

@router.post("", response_model=XxxResponse)
async def create_xxx(...):
    service = XxxService(db)
    return await service.create(...)
```

## Entry Points

### Backend Entry Point
- **Location**: `app/backend/main.py`
- **Triggers**: `python main.py` or uvicorn
- **Responsibilities**:
  - FastAPI app initialization
  - Lifespan management (startup/shutdown)
  - Router auto-discovery and registration
  - CORS middleware setup
  - Logging configuration

### Frontend Entry Point
- **Location**: `app/frontend/src/main.tsx` (implicit)
- **Triggers**: Vite dev server or production build
- **Responsibilities**:
  - React Query client setup
  - Auth context provider
  - Browser router initialization
  - App routes mounting

### Lambda Entry Point
- **Location**: `app/backend/lambda_handler.py`
- **Triggers**: AWS Lambda invocation
- **Responsibilities**: AWS Lambda handler for serverless deployment

## Error Handling

**Strategy:** Exception-based with HTTPException for HTTP errors

**Patterns:**
- Service layer raises exceptions on database errors, rolls back transactions
- Module layer catches exceptions and returns appropriate HTTP status codes
- 404 Not Found for missing entities
- 400 Bad Request for validation errors
- 401 Unauthorized for auth failures
- 403 Forbidden for permission denied
- 500 Internal Server Error for unhandled exceptions

**Logging:**
- Python `logging` module with file and console handlers
- Log files: `logs/app_YYYYMMDD_HHMMSS.log`
- Structured logging with exception tracebacks

## Cross-Cutting Concerns

**Authentication:** JWT tokens with `python-jose` library
- Token expires in 24 hours (configurable)
- Stored in `Authorization: Bearer <token>` header

**Authorization:** Role-based access control (RBAC)
- Four roles: ADMIN, CHETOP, CHEFTECH, TECHNICIEN
- Route-level protection via `ProtectedRoute` component (frontend)
- Dependency-level protection via `get_current_user` (backend)

**Database:** SQLAlchemy async with SQLite (development)
- Async connection pool management
- Migration support via Alembic (`alembic/`)

**Validation:** Pydantic for request/response validation
- Inline schemas in modules
- Shared schemas in `schemas/` directory

**File Storage:** MinIO (S3-compatible) for document storage
- Configured via `core/config.py` settings

---

*Architecture analysis: 2026-03-03*
