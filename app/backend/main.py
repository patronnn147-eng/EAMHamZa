import importlib
import logging
import os
import pkgutil
from contextlib import asynccontextmanager
from datetime import datetime

from core.config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter

# MODULE_IMPORTS_START
from services.database import initialize_database, close_database
from services.mock_data import initialize_mock_data
from core.rabbitmq import get_rabbitmq, RabbitMQService
# Import all models to ensure they are registered with SQLAlchemy metadata
# MODULE_IMPORTS_END


def setup_logging():
    """Configure the logging system."""
    if os.environ.get("IS_LAMBDA") == "true":
        return

    # Create the logs directory
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{log_dir}/app_{timestamp}.log"

    # Configure log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure the root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        handlers=[
            # File handler
            logging.FileHandler(log_file, encoding="utf-8"),
            # Console handler
            logging.StreamHandler(),
        ],
    )

    # Set log levels for specific modules
    logging.getLogger("uvicorn").setLevel(logging.DEBUG)
    logging.getLogger("fastapi").setLevel(logging.DEBUG)

    # Log configuration details
    logger = logging.getLogger(__name__)
    logger.info("=== Logging system initialized ===")
    logger.info(f"Log file: {log_file}")
    logger.info("Log level: INFO")
    logger.info(f"Timestamp: {timestamp}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger(__name__)
    logger.info("=== Application startup initiated ===")

    # MODULE_STARTUP_START
    await initialize_database()
    await initialize_mock_data()
    try:
        await get_rabbitmq()
        logger.info("RabbitMQ connection established")
    except Exception as e:
        logger.warning(f"RabbitMQ connection failed (app will still run): {e}")

    # Register event-driven RAG sync hooks (after_commit on selected models).
    try:
        from services.rag_change_hooks import register_rag_hooks

        register_rag_hooks()
    except Exception as e:
        logger.warning(f"RAG change hooks registration failed (sync disabled): {e}")

    # Initial backfill — dispatch full sync to Celery if KB has no auto-synced docs yet,
    # or unconditionally when RAG_BACKFILL_ON_STARTUP=true. Non-blocking — task runs
    # in celery_worker so app startup is not delayed.
    try:
        import os
        from sqlalchemy import text
        from core.database import db_manager

        force = os.getenv("RAG_BACKFILL_ON_STARTUP", "false").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        async with db_manager.async_session_maker() as s:
            row = await s.execute(
                text("SELECT COUNT(*) FROM documents WHERE filename LIKE 'db:%'")
            )
            count = row.scalar() or 0
        if force or count == 0:
            from tasks.rag_db_sync import rag_sync_all

            rag_sync_all.delay(None, True)
            logger.info(
                f"[rag_backfill] dispatched (force={force}, existing_db_docs={count})"
            )
        else:
            logger.info(f"[rag_backfill] skipped — {count} db:* docs already present")
    except Exception as e:
        logger.warning(f"RAG backfill dispatch failed: {e}")
    # MODULE_STARTUP_END

    logger.info("=== Application startup completed successfully ===")
    yield
    # MODULE_SHUTDOWN_START
    try:
        rmq = RabbitMQService._instance
        if rmq:
            await rmq.close()
    except Exception as e:
        logger.warning(f"RabbitMQ close failed: {e}")
    await close_database()
    # MODULE_SHUTDOWN_END


app = FastAPI(
    title="FastAPI Modular Template",
    description="A best-practice FastAPI template with modular architecture",
    version="1.0.0",
    lifespan=lifespan,
)


# MODULE_MIDDLEWARE_START
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
# MODULE_MIDDLEWARE_END


# Auto-discover and include all routers from the local `routers` package
def include_routers_from_package(app: FastAPI, package_name: str = "routers") -> None:
    """Discover and include all APIRouter objects from a package.

    This scans the given package (and subpackages) for module-level variables that
    are instances of FastAPI's APIRouter. It supports "router", "admin_router" names.
    """

    logger = logging.getLogger(__name__)

    try:
        # nosemgrep: python.lang.security.audit.non-literal-import.non-literal-import -- package_name is a hardcoded default ("routers"), not user input
        pkg = importlib.import_module(package_name)  # fmt: skip
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.debug("Routers package '%s' not loaded: %s", package_name, exc)
        return

    discovered: int = 0
    for _finder, module_name, is_pkg in pkgutil.walk_packages(
        pkg.__path__, pkg.__name__ + "."
    ):
        # Only import leaf modules; subpackages will be walked automatically
        if is_pkg:
            continue
        try:
            # nosemgrep: python.lang.security.audit.non-literal-import.non-literal-import -- module_name comes from pkgutil.walk_packages() enumerating the local routers/ package, never user input
            module = importlib.import_module(module_name)  # fmt: skip
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to import module '%s': %s", module_name, exc)
            continue

        # Check for router variable names: router and admin_router
        for attr_name in ("router", "admin_router"):
            if not hasattr(module, attr_name):
                continue

            attr = getattr(module, attr_name)

            if isinstance(attr, APIRouter):
                # Add /api/v1/auth prefix for auth router
                if "auth" in module_name:
                    app.include_router(attr, prefix="/api/v1/auth")
                else:
                    app.include_router(attr)
                discovered += 1
                logger.info("Included router: %s.%s", module_name, attr_name)
            elif isinstance(attr, (list, tuple)):
                for idx, item in enumerate(attr):
                    if isinstance(item, APIRouter):
                        app.include_router(item)
                        discovered += 1
                        logger.info(
                            "Included router from list: %s.%s[%d]",
                            module_name,
                            attr_name,
                            idx,
                        )

    if discovered == 0:
        logger.debug("No routers discovered in package '%s'", package_name)


# Setup logging before router discovery
setup_logging()
include_routers_from_package(app, "modules")

# Include ML router (not auto-discovered due to different path)
from modules.ml.router import router as ml_router  # noqa: E402

app.include_router(ml_router)

# Note: PlanningTaches routers are auto-included via include_routers_from_package


@app.get("/")
def root():
    return {"message": "FastAPI Modular Template is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/v1/health")
async def api_health_check():
    from services.database import check_database_health

    db_healthy = await check_database_health()
    return {"status": "ok", "database": "connected" if db_healthy else "disconnected"}


def run_in_debug_mode(app: FastAPI):
    """Run the FastAPI app in debug mode with proper asyncio handling.

    This function handles the special case of running in a debugger (PyCharm, VS Code, etc.)
    where asyncio is patched, causing conflicts with uvicorn's asyncio_run.

    It loads environment variables from ../.env and uses asyncio.run() directly
    to avoid uvicorn's asyncio_run conflicts.

    Args:
        app: The FastAPI application instance
    """
    import asyncio
    from pathlib import Path

    import uvicorn
    from dotenv import load_dotenv

    # Load environment variables from ../.env in debug mode
    # If `LOCAL_DEBUG=true` is set, then MetaGPT's `ProjectBuilder.build()` will generate the `.env` file
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
        logger = logging.getLogger(__name__)
        logger.info(f"Loaded environment variables from {env_path}")

    # In debug mode, use asyncio.run() directly to avoid uvicorn's asyncio_run conflicts
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=int(settings.port),
        log_level="info",
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


if __name__ == "__main__":
    import sys

    import uvicorn

    # Detect if running in debugger (PyCharm, VS Code, etc.)
    # Debuggers patch asyncio which conflicts with uvicorn's asyncio_run
    is_debugging = "pydevd" in sys.modules or (
        hasattr(sys, "gettrace") and sys.gettrace() is not None
    )

    if is_debugging:
        run_in_debug_mode(app)
    else:
        # Enable reload in normal mode
        uvicorn.run(
            app,
            host=settings.host,
            port=int(settings.port),
            reload_excludes=["**/*.py"],
        )
