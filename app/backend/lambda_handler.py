"""
AWS Lambda handler for unified frontend and backend with Nginx reverse proxy
This handler simulates Nginx routing logic within Lambda
"""

import asyncio
import base64
import html
import json
import logging
import os
import traceback
from typing import Any, Dict
from urllib.parse import unquote

from mangum import Mangum

# Configure logging
logger = logging.getLogger()
if logger.hasHandlers():
    logger.handlers.clear()
fmt = logging.Formatter(
    "%(asctime)s - %(module)s.%(funcName)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s"
)
h = logging.StreamHandler()
h.setFormatter(fmt)
logger.setLevel(
    getattr(logging, os.environ.get("LOG_LEVEL", "DEBUG").upper(), logging.DEBUG)
)
logger.addHandler(h)

# Global variables for app instances
backend_app = None
mangum_handler = None
services_initialized = False

# Dynamic route registry - initialized on first request
dynamic_routes_initialized = False
seo_paths = set()

# SEO domain placeholder - will be replaced with actual request domain at runtime
SEO_DOMAIN_PLACEHOLDER = "https://atoms.template.com"

# Shared literals (deduplicated per sonar S1192)
FRONTEND_DIST_DIR = "/var/task/frontend/dist"
BACKEND_DIR = "/var/task/backend"
INDEX_HTML_FILENAME = "index.html"
CONTENT_TYPE_HTML = "text/html"
CONTENT_TYPE_PLAIN = "text/plain"
CONTENT_TYPE_JSON = "application/json"
INTERNAL_SERVER_ERROR_MSG = "Internal server error"


def format_traceback() -> str:
    """Format traceback with newlines replaced by '\\n' string literal"""
    return traceback.format_exc().replace(chr(10), "\\n")


def _scan_seo_routes(dist_path: str) -> set:
    """Walk dist_path and return the set of /blog* URL paths that contain index.html."""
    found = set()
    for root, _dirs, files in os.walk(dist_path):
        if INDEX_HTML_FILENAME not in files:
            continue
        rel_path = os.path.relpath(root, dist_path)
        if rel_path == ".":
            continue
        url_path = "/" + rel_path.replace(os.sep, "/")
        if url_path == "/blog" or url_path.startswith("/blog/"):
            found.add(url_path)
            logger.info(f"Registered SEO route: {url_path}")
    return found


def initialize_dynamic_routes():
    """Initialize dynamic routes by scanning frontend dist directory"""
    global dynamic_routes_initialized, seo_paths

    if dynamic_routes_initialized:
        return

    try:
        if os.path.exists(FRONTEND_DIST_DIR):
            seo_paths = _scan_seo_routes(FRONTEND_DIST_DIR)
        dynamic_routes_initialized = True
        logger.info(f"Dynamic routes initialized: seo_paths={len(seo_paths)}")
    except Exception as e:
        logger.exception(f"Failed to initialize dynamic routes: {e}\n{format_traceback()}")
        dynamic_routes_initialized = True


async def initialize_services_once():
    """Initialize all services once for the Lambda function (equivalent to FastAPI lifespan startup)"""
    global services_initialized

    if not services_initialized:
        try:
            # Import all initialization functions (same as in main.py lifespan)
            # Add backend to sys.path for imports
            import sys

            if BACKEND_DIR not in sys.path:
                sys.path.append(BACKEND_DIR)

            # MODULE_IMPORTS_START
            from services.database import initialize_database
            from services.mock_data import initialize_mock_data
            # MODULE_IMPORTS_END

            # MODULE_STARTUP_START
            await initialize_database()
            await initialize_mock_data()
            # MODULE_STARTUP_END

            services_initialized = True
        except Exception as e:
            logger.exception(
                f"Failed to initialize services: {e}\n{format_traceback()}"
            )
            raise


def get_backend_app():
    """Get or create the FastAPI backend app"""
    global backend_app

    if backend_app is None:
        try:
            # Import the FastAPI app
            import sys

            sys.path.append(BACKEND_DIR)
            # Check if main.py exists
            main_py_path = "/var/task/backend/main.py"
            if not os.path.exists(main_py_path):
                logger.error("/var/task/backend/main.py not found")

            from main import app as backend_app
        except Exception as e:
            logger.exception(f"Failed to import backend app: {e}\n{format_traceback()}")
            raise

    return backend_app


async def get_mangum_handler():
    """Get or create the Mangum handler"""
    global mangum_handler

    if mangum_handler is None:
        try:
            # Initialize all services first (equivalent to FastAPI lifespan startup)
            await initialize_services_once()

            backend_app = get_backend_app()
            # Configure Mangum for API Gateway v2
            mangum_handler = Mangum(backend_app, lifespan="off")
        except Exception as e:
            logger.exception(
                f"Failed to create Mangum handler: {e}\n{format_traceback()}"
            )
            raise

    return mangum_handler


def get_mangum_handler_sync():
    """Get or create the Mangum handler (synchronous version)"""
    global mangum_handler

    if mangum_handler is None:
        try:
            backend_app = get_backend_app()
            # Configure Mangum for API Gateway v2
            mangum_handler = Mangum(backend_app, lifespan="off")
        except Exception as e:
            logger.exception(
                f"Failed to create Mangum handler: {e}\n{format_traceback()}"
            )
            raise

    return mangum_handler


def _parse_event_path_headers(event: Dict[str, Any]) -> tuple:
    """Extract (path, headers) from API Gateway v1 or v2 event format."""
    if "version" in event and event["version"] == "2.0":
        path = event.get("rawPath", "/")
        headers = event.get("headers", {})
        if headers:
            headers = {k.lower(): v for k, v in headers.items()}
    elif "httpMethod" in event:
        path = event.get("path", "/")
        headers = event.get("headers", {})
    else:
        path = "/"
        headers = {}
    return path, headers


def _update_event_path(event: Dict[str, Any], path: str) -> None:
    """Write the normalized path back into the event for downstream handlers."""
    if "version" in event and event["version"] == "2.0":
        event["rawPath"] = path
    elif "httpMethod" in event:
        event["path"] = path


def _dispatch_route(
    path: str,
    event: Dict[str, Any],
    context: Any,
    headers: Dict[str, str],
    request_domain: str,
) -> Dict[str, Any]:
    """Route a normalized path to the correct handler and return its response."""
    if path == "/api/config":
        return handle_config_request(headers)
    if path.startswith("/api/v1/"):
        return handle_backend_request_sync(event, context)
    if path == "/health":
        return {
            "statusCode": 200,
            "headers": {"Content-Type": CONTENT_TYPE_JSON, "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"status": "healthy"}),
        }
    if path.startswith("/database"):
        return {
            "statusCode": 404,
            "headers": {"Content-Type": CONTENT_TYPE_JSON, "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Not found"}),
        }
    if path.endswith((".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".ico",
                       ".svg", ".woff", ".woff2", ".ttf", ".eot")):
        return serve_static_file(path)
    if path == "/sitemap.xml":
        return serve_sitemap(request_domain)
    if path == "/robots.txt":
        return serve_robots()
    if path.rstrip("/") in seo_paths:
        return serve_seo_html(path, request_domain)
    return serve_frontend()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function that simulates Nginx routing
    """
    try:
        initialize_dynamic_routes()

        path, headers = _parse_event_path_headers(event)

        try:
            path = unquote(path, encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to decode path '{path}': {e}, using original path")

        if not path.startswith("/"):
            path = "/" + path

        proto = headers.get("x-forwarded-proto", "https")
        host = (
            headers.get("mgx-external-domain")
            or headers.get("x-forwarded-host")
            or headers.get("host", "")
        )
        request_domain = f"{proto}://{host}" if host else ""

        _update_event_path(event, path)
        return _dispatch_route(path, event, context, headers, request_domain)

    except Exception as e:
        error_info = (
            f"{e}\n{format_traceback()}"
            if os.getenv("ENVIRONMENT", "prod").lower() == "dev"
            else str(e)
        )
        logger.error(f"Lambda handler error: {error_info}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": CONTENT_TYPE_JSON,
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {"error": error_info, "message": INTERNAL_SERVER_ERROR_MSG}
            ),
        }


def handle_backend_request_sync(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle backend API requests using Mangum (synchronous wrapper)"""
    # Initialize services if not already done
    if not services_initialized:
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we can't use it, so create a new one in a thread
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, initialize_services_once())
                    future.result()
            else:
                # If loop is not running, run directly
                loop.run_until_complete(initialize_services_once())
        except RuntimeError:
            # No event loop exists, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(initialize_services_once())
            finally:
                loop.close()

    # Get or create Mangum handler
    mangum_handler = get_mangum_handler_sync()

    # Call Mangum handler
    result = mangum_handler(event, context)
    return result


def serve_frontend() -> Dict[str, Any]:
    """Serve the frontend HTML"""
    # Try to read the built frontend HTML
    html_path = "/var/task/frontend/dist/index.html"
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        response = {
            "statusCode": 200,
            "headers": {
                "Content-Type": CONTENT_TYPE_HTML,
                "Access-Control-Allow-Origin": "*",
            },
            "body": html_content,
        }
        return response
    else:
        # Fallback to a simple HTML response
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Unknown App</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                code {
                    background-color: #f4f4f4;
                    border: 1px solid #ddd;
                    border-radius: 3px;
                    padding: 2px 4px;
                    font-family: 'Courier New', monospace;
                    font-size: 0.9em;
                    color: #e33;
                }
            </style>
        </head>
        <body>
            <h1>Unknown Application</h1>
            <p>✅ Service has been successfully deployed and is running on AWS Lambda</p>
            <p>⚠️ The homepage is missing. Please verify that <code>app/frontend/index.html</code> exists and
             that no other <code>index.html</code> files are interfering with the build output
              at <code>dist/index.html</code>.</p>
            <script>
                console.error('INDEX_HTML_PATH_ERROR: Service has been successfully deployed and is running on'
                + ' AWS Lambda, but the homepage is missing. Please verify that app/frontend/index.html exists'
                + ' and that no other index.html files are interfering with the build output at dist/index.html.');
            </script>
        </body>
        </html>
        """

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": CONTENT_TYPE_HTML,
                "Access-Control-Allow-Origin": "*",
            },
            "body": html_content,
        }


def serve_static_file(path: str) -> Dict[str, Any]:
    """Serve static files"""
    # Map file extensions to content types
    content_types = {
        ".js": "application/javascript",
        ".css": "text/css",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".ico": "image/x-icon",
        ".svg": "image/svg+xml",
    }

    # Get file extension
    ext = os.path.splitext(path)[1].lower()
    content_type = content_types.get(ext, "application/octet-stream")

    # Security: `path` comes from the request URL (untrusted). Resolve the
    # real path and verify it stays within the static root before opening it,
    # to prevent path traversal (e.g. "/../../etc/passwd").
    static_root = os.path.realpath(FRONTEND_DIST_DIR)
    file_path = os.path.realpath(os.path.join(static_root, path.lstrip("/")))
    if not (file_path == static_root or file_path.startswith(static_root + os.sep)):
        logger.warning(f"Blocked path traversal attempt: {path!r}")
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": CONTENT_TYPE_PLAIN,
                "Access-Control-Allow-Origin": "*",
            },
            "body": "File not found",
        }

    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            content = f.read()
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": content_type,
                "Access-Control-Allow-Origin": "*",
            },
            "body": content.decode("utf-8")
            if content_type.startswith("text/")
            else base64.b64encode(content).decode("utf-8"),
            "isBase64Encoded": not content_type.startswith("text/"),
        }
    else:
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": CONTENT_TYPE_PLAIN,
                "Access-Control-Allow-Origin": "*",
            },
            "body": "File not found",
        }


def handle_config_request(headers: dict) -> Dict[str, Any]:
    """Handle configuration requests with security filtering"""
    # Security: Validate request method and origin
    validation_result = validate_config_request(headers)
    if not validation_result["isValid"]:
        return {
            "statusCode": 403,
            "headers": {
                "Content-Type": CONTENT_TYPE_JSON,
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {"error": "Access denied", "message": "Invalid request"}
            ),
        }

    # Security: Only return frontend-required configuration
    # Define what frontend actually needs (based on code analysis)
    frontend_required_config = {
        "API_BASE_URL": os.environ.get("VITE_API_BASE_URL", "http://127.0.0.1:8000")
        # Only add other configs if frontend actually uses them
        # DO NOT expose: VITE_FRONTEND_URL, secrets, internal URLs, etc.
    }

    # Security: Validate and sanitize the configuration
    sanitized_config = sanitize_config(frontend_required_config)
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": CONTENT_TYPE_JSON,
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=300",  # Cache for 5 minutes
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        },
        "body": json.dumps(sanitized_config),
    }


def validate_config_request(headers: dict) -> Dict[str, Any]:
    """Validate configuration request for security"""
    # Check for suspicious user agents (basic bot detection)
    user_agent = headers.get("user-agent", headers.get("User-Agent", ""))
    suspicious_patterns = ["bot", "crawler", "spider", "scraper", "curl", "wget"]

    if any(pattern in user_agent.lower() for pattern in suspicious_patterns):
        return {"isValid": False, "reason": "Suspicious user agent detected"}

    # Optional: Check referer for additional security (can be disabled if needed)
    referer = headers.get("referer", headers.get("Referer", ""))
    if referer and not is_valid_referer(referer):
        return {"isValid": False, "reason": "Invalid referer"}

    return {"isValid": True}


def is_valid_referer(referer: str) -> bool:
    """Check if referer is valid (optional security measure)"""
    # Allow requests from same domain or common frontend domains
    allowed_domains = [
        "localhost",
        "127.0.0.1",
        "amazonaws.com",
        "execute-api.us-east-1.amazonaws.com",
        "lambda-url.us-east-1.on.aws",
    ]
    env_allowed_domains = os.environ.get("ALLOWED_DOMAINS") or ""
    if env_allowed_domains:
        domains = [i.strip() for i in env_allowed_domains.split(",") if i.strip()]
        for domain in domains:
            if domain in allowed_domains:
                continue
            allowed_domains.append(domain)

    try:
        from urllib.parse import urlparse

        parsed_url = urlparse(referer)
        return any(
            domain in parsed_url.hostname
            for domain in allowed_domains
            if parsed_url.hostname
        )
    except Exception:
        return False


def sanitize_config(config: dict) -> dict:
    """Sanitize configuration to ensure only safe, frontend-required data is exposed"""
    sanitized = {}

    # Define allowed configuration keys that frontend actually uses
    allowed_keys = [
        "API_BASE_URL"  # Only this is actually used by frontend
        # Add other keys only if frontend code actually uses them
    ]

    # Only include allowed keys with validation
    for key in allowed_keys:
        if key in config:
            # Additional validation for specific keys
            if key == "API_BASE_URL":
                # Ensure it's a valid URL format
                url = config[key]
                if isinstance(url, str) and url.startswith(("http://", "https://")):
                    sanitized[key] = url
                else:
                    logger.debug(f"Invalid API_BASE_URL format: {url}")
                    sanitized[key] = "http://127.0.0.1:8000"  # Safe fallback
            else:
                sanitized[key] = config[key]

    return sanitized


def replace_seo_domain(content: str, request_domain: str) -> str:
    """Replace SEO placeholder domain with actual request domain"""
    if request_domain and SEO_DOMAIN_PLACEHOLDER in content:
        # Security: request_domain is derived from request headers (Host /
        # X-Forwarded-Host, untrusted) and gets embedded into an HTML
        # document. Escape it before substitution to avoid reflected XSS.
        return content.replace(SEO_DOMAIN_PLACEHOLDER, html.escape(request_domain))
    return content


def serve_sitemap(request_domain: str = "") -> Dict[str, Any]:
    """Serve sitemap.xml file"""
    sitemap_path = "/var/task/frontend/dist/sitemap.xml"
    if not os.path.exists(sitemap_path):
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": CONTENT_TYPE_PLAIN,
                "Access-Control-Allow-Origin": "*",
            },
            "body": "sitemap.xml not found",
        }

    try:
        with open(sitemap_path, "r", encoding="utf-8") as f:
            content = replace_seo_domain(f.read(), request_domain)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/xml",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache",
            },
            "body": content,
        }
    except Exception as e:
        logger.exception(f"Failed to read sitemap.xml: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": CONTENT_TYPE_PLAIN,
                "Access-Control-Allow-Origin": "*",
            },
            "body": INTERNAL_SERVER_ERROR_MSG,
        }


def serve_robots() -> Dict[str, Any]:
    """Serve robots.txt file"""
    robots_path = "/var/task/frontend/dist/robots.txt"
    if not os.path.exists(robots_path):
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": CONTENT_TYPE_PLAIN,
                "Access-Control-Allow-Origin": "*",
            },
            "body": "robots.txt not found",
        }

    try:
        with open(robots_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": CONTENT_TYPE_PLAIN,
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache",
            },
            "body": content,
        }
    except Exception as e:
        logger.exception(f"Failed to read robots.txt: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": CONTENT_TYPE_PLAIN,
                "Access-Control-Allow-Origin": "*",
            },
            "body": INTERNAL_SERVER_ERROR_MSG,
        }


def serve_seo_html(path: str, request_domain: str = "") -> Dict[str, Any]:
    """Serve SEO HTML files from index.html"""
    # Security: `path` comes from the request URL (untrusted, though callers
    # currently gate it against a whitelist of registered SEO paths). Resolve
    # the real path and verify it stays within the static root before opening
    # it, to prevent path traversal (e.g. "/../../etc/passwd").
    static_root = os.path.realpath(FRONTEND_DIST_DIR)
    html_path = os.path.realpath(
        os.path.join(static_root, path.strip("/"), INDEX_HTML_FILENAME)
    )
    if not (
        html_path == os.path.join(static_root, INDEX_HTML_FILENAME)
        or html_path.startswith(static_root + os.sep)
    ):
        logger.warning(f"Blocked path traversal attempt: {path!r}")
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": CONTENT_TYPE_HTML,
                "Access-Control-Allow-Origin": "*",
            },
            "body": "<html><body><h1>404 Not Found</h1></body></html>",
        }

    if not os.path.exists(html_path):
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": CONTENT_TYPE_HTML,
                "Access-Control-Allow-Origin": "*",
            },
            "body": "<html><body><h1>404 Not Found</h1></body></html>",
        }

    try:
        with open(html_path, "r", encoding="utf-8") as f:
            content = replace_seo_domain(f.read(), request_domain)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": CONTENT_TYPE_HTML,
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache",
            },
            "body": content,
        }
    except Exception as e:
        logger.exception(f"Failed to read SEO HTML file {html_path}: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": CONTENT_TYPE_HTML,
                "Access-Control-Allow-Origin": "*",
            },
            "body": "<html><body><h1>500 Internal Server Error</h1></body></html>",
        }


# Export the handler for AWS Lambda
if __name__ == "__main__":
    # Test the handler locally
    test_event = {"httpMethod": "GET", "path": "/", "headers": {}, "body": ""}

    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
