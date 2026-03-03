# Codebase Structure

**Analysis Date:** 2026-03-03

## Directory Layout

```
EAMSagemCom/
├── app/
│   ├── backend/                    # Python FastAPI backend
│   │   ├── alembic/                 # Database migrations
│   │   │   └── versions/            # Migration scripts
│   │   ├── core/                    # Core infrastructure
│   │   ├── dependencies/            # FastAPI dependencies
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── modules/                 # Entity-specific API modules
│   │   │   ├── auth/                # Authentication module
│   │   │   ├── cheftech/            # ChefTech role module
│   │   │   ├── ml/                  # ML prediction module
│   │   │   ├── shared/              # Shared CRUD modules
│   │   │   └── technicien/           # Technician role module
│   │   ├── routers/                 # Additional routers
│   │   ├── schemas/                 # Pydantic schemas
│   │   ├── services/                # Business logic services
│   │   ├── tasks/                   # Celery background tasks
│   │   ├── main.py                  # Backend entry point
│   │   └── lambda_handler.py        # AWS Lambda handler
│   └── frontend/                    # React TypeScript frontend
│       ├── src/
│       │   ├── app/
│       │   │   └── routing/         # Route definitions
│       │   ├── components/           # Shared UI components
│       │   │   ├── layout/           # Layout components
│       │   │   └── ui/               # UI component library
│       │   ├── contexts/             # React contexts
│       │   ├── hooks/                # Custom React hooks
│       │   ├── modules/              # Feature modules by role
│       │   │   ├── admin/            # Admin-specific pages
│       │   │   ├── auth/             # Authentication pages
│       │   │   ├── cheftech/          # ChefTech pages
│       │   │   ├── chetop/            # Chetop pages
│       │   │   ├── shared/            # Shared pages
│       │   │   └── technicien/        # Technician pages
│       │   ├── App.tsx               # Root app component
│       │   └── main.tsx              # Frontend entry point
│       ├── package.json              # Node dependencies
│       ├── vite.config.ts            # Vite configuration
│       └── tailwind.config.ts        # Tailwind CSS config
├── tests/                           # Test files
│   └── backend/                     # Backend tests
├── ml_problems/                     # ML model training scripts
├── notebooks/                       # Jupyter notebooks
├── ML_Pipeline/                    # ML documentation
└── .env                            # Environment variables (secrets)
```

## Directory Purposes

### Backend Core

**`app/backend/core/`:**
- Purpose: Application-wide infrastructure and configuration
- Contains: Config, database, auth, email, RabbitMQ, WebSocket utilities
- Key files: `config.py`, `database.py`, `auth.py`

**`app/backend/models/`:**
- Purpose: SQLAlchemy ORM table definitions
- Contains: Model classes for all database tables
- Key files: `utilisateurs.py`, `machines.py`, `ordres_travail.py`, `ordres_intervention.py`, `plannings.py`

**`app/backend/services/`:**
- Purpose: Business logic layer
- Contains: Service classes with CRUD and business operations
- Key files: `utilisateurs.py`, `machines.py`, `ordres_travail.py`, `auth.py`

**`app/backend/modules/`:**
- Purpose: Entity-specific API endpoints
- Contains: APIRouter definitions with full CRUD operations
- Key files: `auth/auth.py`, `shared/utilisateurs.py`, `shared/machines.py`

**`app/backend/schemas/`:**
- Purpose: Pydantic validation models
- Contains: Request/response schemas
- Key files: `auth.py`, `storage.py`, `aihub.py`

**`app/backend/dependencies/`:**
- Purpose: FastAPI dependency injection
- Contains: `get_current_user()`, `get_db()` functions

**`app/backend/routers/`:**
- Purpose: Additional API routers
- Contains: Non-entity routers (notifications, admin)
- Key files: `notifications.py`, `plannings.py`

**`app/backend/tasks/`:**
- Purpose: Background tasks (Celery)
- Contains: Task definitions for async processing
- Key files: `maintenance_scheduler.py`, `planning_emails.py`

**`app/backend/alembic/`:**
- Purpose: Database migrations
- Contains: Migration configuration and version scripts

### Frontend Core

**`app/frontend/src/modules/`:**
- Purpose: Feature pages organized by user role
- Contains: Page components, hooks, utils

**`app/frontend/src/components/ui/`:**
- Purpose: Reusable UI component library
- Contains: Shadcn/ui components (button, dialog, table, etc.)

**`app/frontend/src/components/layout/`:**
- Purpose: Layout components (Sidebar, Header)
- Contains: `Layout.tsx`, `Sidebar.tsx`, `Header.tsx`, `TechnicianLayout.tsx`

**`app/frontend/src/contexts/`:**
- Purpose: React context providers
- Contains: `AuthContext.tsx`, `DataSyncContext.tsx`

**`app/frontend/src/hooks/`:**
- Purpose: Custom React hooks
- Contains: `use-mobile.tsx`

**`app/frontend/src/app/routing/`:**
- Purpose: Route definitions and guards
- Contains: `AppRoutes.tsx`, `ProtectedRoute.tsx`, `RoleBasedRedirect.tsx`

## Key File Locations

### Entry Points

- **Backend**: `app/backend/main.py` - FastAPI application initialization
- **Frontend**: `app/frontend/src/main.tsx` - React app bootstrap
- **Lambda**: `app/backend/lambda_handler.py` - AWS Lambda handler

### Configuration

- **Backend settings**: `app/backend/core/config.py` - Environment configuration
- **Frontend config**: `app/frontend/vite.config.ts` - Vite bundler config
- **Tailwind**: `app/frontend/tailwind.config.ts` - CSS framework config
- **TypeScript**: `app/frontend/tsconfig.json` - TypeScript compiler options
- **Environment**: `.env` - Environment variables (not committed)

### Core Logic

- **Authentication**: `app/backend/core/auth.py` - JWT utilities
- **Database**: `app/backend/core/database.py` - SQLAlchemy setup
- **User models**: `app/backend/models/utilisateurs.py` - User table

### Testing

- **Backend tests**: `tests/backend/*.py` - Python unit tests

## Naming Conventions

### Backend Python Files

- **Models**: `snake_case.py` (e.g., `utilisateurs.py`, `ordres_travail.py`)
- **Services**: `snake_case.py` (e.g., `utilisateurs.py`, `machines.py`)
- **Modules**: `snake_case.py` (e.g., `utilisateurs.py`, `machines.py`)
- **Schemas**: `snake_case.py` (e.g., `auth.py`, `storage.py`)
- **Core utilities**: `snake_case.py` (e.g., `config.py`, `database.py`)

### Frontend TypeScript Files

- **Components**: `PascalCase.tsx` (e.g., `Dashboard.tsx`, `WorkOrdersList.tsx`)
- **Hooks**: `camelCase.ts` or `camelCase.tsx` (e.g., `useMachines.ts`, `useWorkOrders.ts`)
- **Utilities**: `camelCase.ts` (e.g., `healthScore.ts`, `reliabilityMetrics.ts`)
- **Context**: `PascalCase.tsx` (e.g., `AuthContext.tsx`)

### Directories

- **Backend modules**: `snake_case/` (e.g., `modules/shared/`, `services/`)
- **Frontend modules**: `camelCase/` or `PascalCase/` (e.g., `modules/shared/`, `modules/technicien/`)
- **Components**: `PascalCase/` (e.g., `components/ui/`, `components/layout/`)

### Database Tables

- **Table names**: Snake_case (e.g., `utilisateurs`, `ordres_travail`, `plannings`)

### API Endpoints

- **Path pattern**: `/api/v1/entities/{entity_name}` (e.g., `/api/v1/entities/utilisateurs`)
- **HTTP methods**: RESTful conventions (GET, POST, PUT, DELETE)

## Where to Add New Code

### New Backend Entity

1. **Create model** in `app/backend/models/{entity_name}.py`
2. **Create service** in `app/backend/services/{entity_name}.py`
3. **Create module** in `app/backend/modules/shared/{entity_name}.py`
4. **Register routes**: Auto-discovered, no changes needed to `main.py`

Example structure:
```python
# app/backend/models/new_entity.py
from core.database import Base
from sqlalchemy import Column, Integer, String

class NewEntity(Base):
    __tablename__ = "new_entities"
    id = Column(Integer, primary_key=True)
    name = Column(String)

# app/backend/services/new_entity.py
class NewEntityService:
    def __init__(self, db):
        self.db = db
    # CRUD methods...

# app/backend/modules/shared/new_entity.py
router = APIRouter(prefix="/api/v1/entities/new_entity", tags=["new_entity"])
# Endpoints...
```

### New Backend Feature (Non-CRUD)

1. **Router**: Create `app/backend/routers/{feature_name}.py`
2. **Service**: Add methods to existing service or create new service
3. **Module**: Create `app/backend/modules/{feature_name}/{feature_name}.py`

### New Frontend Page

1. **Create component** in appropriate role module folder:
   - Admin: `app/frontend/src/modules/admin/`
   - ChefTech: `app/frontend/src/modules/cheftech/`
   - Chetop: `app/frontend/src/modules/chetop/`
   - Technician: `app/frontend/src/modules/technicien/`
   - Shared: `app/frontend/src/modules/shared/`

2. **Add route** in `app/frontend/src/app/routing/AppRoutes.tsx`

3. **Add navigation** in `app/frontend/src/components/layout/Sidebar.tsx`

### New Frontend Component

1. **UI Component**: Add to `app/frontend/src/components/ui/`
2. **Layout Component**: Add to `app/frontend/src/components/layout/`
3. **Feature Component**: Add to appropriate module folder

### New Database Migration

1. **Generate migration**: `alembic revision --autogenerate -m "description"`
2. **Edit migration**: `alembic/versions/{revision}.py`
3. **Run migration**: `alembic upgrade head`

## Special Directories

**`app/backend/alembic/versions/`:**
- Purpose: Database schema migrations
- Generated: Yes (via Alembic)
- Committed: Yes (must track schema changes)

**`app/frontend/src/components/ui/`:**
- Purpose: Shadcn/ui component library
- Generated: Partially (base components from shadcn)
- Committed: Yes (customized components)

**`app/backend/venv/`:**
- Purpose: Python virtual environment
- Generated: Yes (via `python -m venv`)
- Committed: No (in `.gitignore`)

**`app/frontend/node_modules/`:**
- Purpose: Node.js dependencies
- Generated: Yes (via `npm install`)
- Committed: No (in `.gitignore`)

---

*Structure analysis: 2026-03-03*
