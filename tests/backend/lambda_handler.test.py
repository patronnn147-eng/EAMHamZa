"""Unit tests for app/backend/lambda_handler.py — the Nginx-style routing
layer used when the app is deployed behind AWS Lambda. Pure functions and
filesystem-backed handlers, no DB involved."""
import json
import os
from unittest.mock import mock_open, patch

import pytest

import lambda_handler as lh


# ── _scan_seo_routes ─────────────────────────────────────────────────────────

def test_scan_seo_routes_finds_blog_index_pages(tmp_path):
    blog_dir = tmp_path / "blog" / "my-post"
    blog_dir.mkdir(parents=True)
    (blog_dir / "index.html").write_text("<html></html>")
    (tmp_path / "index.html").write_text("root")  # not under /blog, should be skipped

    result = lh._scan_seo_routes(str(tmp_path))
    assert "/blog/my-post" in result
    assert "/" not in result


def test_scan_seo_routes_ignores_non_blog_dirs(tmp_path):
    other_dir = tmp_path / "docs" / "guide"
    other_dir.mkdir(parents=True)
    (other_dir / "index.html").write_text("<html></html>")

    result = lh._scan_seo_routes(str(tmp_path))
    assert result == set()


# ── initialize_dynamic_routes ─────────────────────────────────────────────────

def test_initialize_dynamic_routes_is_idempotent(monkeypatch):
    monkeypatch.setattr(lh, "dynamic_routes_initialized", True)
    monkeypatch.setattr(lh, "seo_paths", {"/blog/sentinel"})
    lh.initialize_dynamic_routes()
    assert lh.seo_paths == {"/blog/sentinel"}  # untouched, short-circuited


def test_initialize_dynamic_routes_handles_missing_dist_dir(monkeypatch):
    monkeypatch.setattr(lh, "dynamic_routes_initialized", False)
    monkeypatch.setattr(lh, "seo_paths", set())
    monkeypatch.setattr(lh, "FRONTEND_DIST_DIR", "/nonexistent/path/xyz")
    lh.initialize_dynamic_routes()
    assert lh.dynamic_routes_initialized is True
    assert lh.seo_paths == set()


def test_initialize_dynamic_routes_swallows_scan_failure(monkeypatch):
    monkeypatch.setattr(lh, "dynamic_routes_initialized", False)
    monkeypatch.setattr(lh, "seo_paths", set())
    monkeypatch.setattr(lh, "FRONTEND_DIST_DIR", "/some/dir")
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    monkeypatch.setattr(lh, "_scan_seo_routes", lambda p: (_ for _ in ()).throw(RuntimeError("boom")))
    lh.initialize_dynamic_routes()  # must not raise
    assert lh.dynamic_routes_initialized is True


# ── _parse_event_path_headers / _update_event_path ────────────────────────────

def test_parse_event_path_headers_v2_lowercases_headers():
    event = {"version": "2.0", "rawPath": "/api/v1/foo", "headers": {"Host": "example.com"}}
    path, headers = lh._parse_event_path_headers(event)
    assert path == "/api/v1/foo"
    assert headers == {"host": "example.com"}


def test_parse_event_path_headers_v1():
    event = {"httpMethod": "GET", "path": "/foo", "headers": {"Host": "example.com"}}
    path, headers = lh._parse_event_path_headers(event)
    assert path == "/foo"
    assert headers == {"Host": "example.com"}


def test_parse_event_path_headers_unknown_format_defaults():
    path, headers = lh._parse_event_path_headers({})
    assert path == "/"
    assert headers == {}


def test_update_event_path_v2():
    event = {"version": "2.0", "rawPath": "/old"}
    lh._update_event_path(event, "/new")
    assert event["rawPath"] == "/new"


def test_update_event_path_v1():
    event = {"httpMethod": "GET", "path": "/old"}
    lh._update_event_path(event, "/new")
    assert event["path"] == "/new"


# ── _dispatch_route ──────────────────────────────────────────────────────────

def test_dispatch_route_config():
    with patch.object(lh, "handle_config_request", return_value={"statusCode": 200}) as m:
        result = lh._dispatch_route("/api/config", {}, None, {}, "")
        assert result == {"statusCode": 200}
        m.assert_called_once()


def test_dispatch_route_backend_api():
    with patch.object(lh, "handle_backend_request_sync", return_value={"statusCode": 200}) as m:
        result = lh._dispatch_route("/api/v1/machines", {}, None, {}, "")
        assert result == {"statusCode": 200}
        m.assert_called_once()


def test_dispatch_route_health():
    result = lh._dispatch_route("/health", {}, None, {}, "")
    assert result["statusCode"] == 200
    assert json.loads(result["body"]) == {"status": "healthy"}


def test_dispatch_route_database_not_found():
    result = lh._dispatch_route("/database/foo", {}, None, {}, "")
    assert result["statusCode"] == 404


def test_dispatch_route_static_asset():
    with patch.object(lh, "serve_static_file", return_value={"statusCode": 200}) as m:
        lh._dispatch_route("/assets/app.js", {}, None, {}, "")
        m.assert_called_once_with("/assets/app.js")


def test_dispatch_route_sitemap():
    with patch.object(lh, "serve_sitemap", return_value={"statusCode": 200}) as m:
        lh._dispatch_route("/sitemap.xml", {}, None, {}, "https://x.com")
        m.assert_called_once_with("https://x.com")


def test_dispatch_route_robots():
    with patch.object(lh, "serve_robots", return_value={"statusCode": 200}) as m:
        lh._dispatch_route("/robots.txt", {}, None, {}, "")
        m.assert_called_once()


def test_dispatch_route_seo_path(monkeypatch):
    monkeypatch.setattr(lh, "seo_paths", {"/blog/my-post"})
    with patch.object(lh, "serve_seo_html", return_value={"statusCode": 200}) as m:
        lh._dispatch_route("/blog/my-post", {}, None, {}, "https://x.com")
        m.assert_called_once_with("/blog/my-post", "https://x.com")


def test_dispatch_route_falls_back_to_frontend(monkeypatch):
    monkeypatch.setattr(lh, "seo_paths", set())
    with patch.object(lh, "serve_frontend", return_value={"statusCode": 200}) as m:
        lh._dispatch_route("/some/unknown/route", {}, None, {}, "")
        m.assert_called_once()


# ── lambda_handler (top-level) ────────────────────────────────────────────────

def test_lambda_handler_dispatches_health_route(monkeypatch):
    monkeypatch.setattr(lh, "initialize_dynamic_routes", lambda: None)
    event = {"httpMethod": "GET", "path": "/health", "headers": {}}
    result = lh.lambda_handler(event, None)
    assert result["statusCode"] == 200


def test_lambda_handler_normalizes_missing_leading_slash(monkeypatch):
    monkeypatch.setattr(lh, "initialize_dynamic_routes", lambda: None)
    captured = {}

    def _fake_dispatch(path, event, context, headers, domain):
        captured["path"] = path
        return {"statusCode": 200}

    monkeypatch.setattr(lh, "_dispatch_route", _fake_dispatch)
    event = {"httpMethod": "GET", "path": "health", "headers": {}}
    lh.lambda_handler(event, None)
    assert captured["path"] == "/health"


def test_lambda_handler_builds_request_domain_from_headers(monkeypatch):
    monkeypatch.setattr(lh, "initialize_dynamic_routes", lambda: None)
    captured = {}

    def _fake_dispatch(path, event, context, headers, domain):
        captured["domain"] = domain
        return {"statusCode": 200}

    monkeypatch.setattr(lh, "_dispatch_route", _fake_dispatch)
    event = {
        "httpMethod": "GET", "path": "/",
        "headers": {"x-forwarded-proto": "https", "host": "example.com"},
    }
    lh.lambda_handler(event, None)
    assert captured["domain"] == "https://example.com"


def test_lambda_handler_catches_exception_and_returns_500(monkeypatch):
    monkeypatch.setattr(lh, "initialize_dynamic_routes", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    event = {"httpMethod": "GET", "path": "/", "headers": {}}
    result = lh.lambda_handler(event, None)
    assert result["statusCode"] == 500
    body = json.loads(result["body"])
    assert body["message"] == lh.INTERNAL_SERVER_ERROR_MSG


# ── handle_config_request / validate_config_request / is_valid_referer ────────

def test_handle_config_request_denies_bot_user_agent():
    result = lh.handle_config_request({"user-agent": "curl/8.0"})
    assert result["statusCode"] == 403


def test_handle_config_request_success():
    result = lh.handle_config_request({"user-agent": "Mozilla/5.0"})
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert "API_BASE_URL" in body


def test_validate_config_request_invalid_referer():
    result = lh.validate_config_request({"user-agent": "Mozilla", "referer": "https://evil.example.net/x"})
    assert result["isValid"] is False


def test_validate_config_request_valid_referer():
    result = lh.validate_config_request({"user-agent": "Mozilla", "referer": "https://localhost/x"})
    assert result["isValid"] is True


def test_is_valid_referer_allowed_domain():
    assert lh.is_valid_referer("https://localhost:3000/page") is True


def test_is_valid_referer_disallowed_domain():
    assert lh.is_valid_referer("https://evil.example.net/x") is False


def test_is_valid_referer_malformed_url_returns_false():
    assert lh.is_valid_referer("not a url \x00") is False


# ── sanitize_config ────────────────────────────────────────────────────────────

def test_sanitize_config_keeps_valid_url():
    result = lh.sanitize_config({"API_BASE_URL": "https://api.example.com"})
    assert result == {"API_BASE_URL": "https://api.example.com"}


def test_sanitize_config_falls_back_on_invalid_url():
    result = lh.sanitize_config({"API_BASE_URL": "not-a-url"})
    assert result["API_BASE_URL"] == "http://127.0.0.1:8000"


def test_sanitize_config_drops_unknown_keys():
    result = lh.sanitize_config({"SECRET_KEY": "shh"})
    assert result == {}


# ── replace_seo_domain ────────────────────────────────────────────────────────

def test_replace_seo_domain_substitutes_and_escapes():
    content = f"<link href='{lh.SEO_DOMAIN_PLACEHOLDER}'>"
    result = lh.replace_seo_domain(content, "https://example.com/<script>")
    assert lh.SEO_DOMAIN_PLACEHOLDER not in result
    assert "&lt;script&gt;" in result


def test_replace_seo_domain_noop_without_domain():
    content = f"<link href='{lh.SEO_DOMAIN_PLACEHOLDER}'>"
    result = lh.replace_seo_domain(content, "")
    assert result == content


# ── serve_static_file ──────────────────────────────────────────────────────────

def test_serve_static_file_serves_text_file(monkeypatch, tmp_path):
    # .css maps to "text/css", the only content-type family this handler
    # serves without base64-encoding (see content_type.startswith("text/")).
    (tmp_path / "app.css").write_text("body { color: red; }")
    monkeypatch.setattr(lh, "FRONTEND_DIST_DIR", str(tmp_path))
    result = lh.serve_static_file("/app.css")
    assert result["statusCode"] == 200
    assert result["headers"]["Content-Type"] == "text/css"
    assert result["isBase64Encoded"] is False


def test_serve_static_file_serves_binary_file_base64(monkeypatch, tmp_path):
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n")
    monkeypatch.setattr(lh, "FRONTEND_DIST_DIR", str(tmp_path))
    result = lh.serve_static_file("/logo.png")
    assert result["statusCode"] == 200
    assert result["isBase64Encoded"] is True


def test_serve_static_file_not_found(monkeypatch, tmp_path):
    monkeypatch.setattr(lh, "FRONTEND_DIST_DIR", str(tmp_path))
    result = lh.serve_static_file("/missing.js")
    assert result["statusCode"] == 404


def test_serve_static_file_blocks_path_traversal(monkeypatch, tmp_path):
    monkeypatch.setattr(lh, "FRONTEND_DIST_DIR", str(tmp_path))
    result = lh.serve_static_file("/../../../etc/passwd.js")
    assert result["statusCode"] == 404


# ── serve_frontend ────────────────────────────────────────────────────────────

def test_serve_frontend_fallback_when_dist_missing():
    with patch.object(os.path, "exists", return_value=False):
        result = lh.serve_frontend()
    assert result["statusCode"] == 200
    assert "Unknown Application" in result["body"]


def test_serve_frontend_reads_built_index():
    with patch.object(os.path, "exists", return_value=True), \
         patch("builtins.open", mock_open(read_data="<html>built</html>")):
        result = lh.serve_frontend()
    assert result["body"] == "<html>built</html>"


# ── serve_sitemap ──────────────────────────────────────────────────────────────

def test_serve_sitemap_not_found():
    with patch.object(os.path, "exists", return_value=False):
        result = lh.serve_sitemap()
    assert result["statusCode"] == 404


def test_serve_sitemap_success():
    with patch.object(os.path, "exists", return_value=True), \
         patch("builtins.open", mock_open(read_data="<urlset></urlset>")):
        result = lh.serve_sitemap("https://x.com")
    assert result["statusCode"] == 200
    assert result["body"] == "<urlset></urlset>"


def test_serve_sitemap_read_failure_returns_500():
    with patch.object(os.path, "exists", return_value=True), \
         patch("builtins.open", side_effect=OSError("disk error")):
        result = lh.serve_sitemap()
    assert result["statusCode"] == 500


# ── serve_robots ───────────────────────────────────────────────────────────────

def test_serve_robots_not_found():
    with patch.object(os.path, "exists", return_value=False):
        result = lh.serve_robots()
    assert result["statusCode"] == 404


def test_serve_robots_success():
    with patch.object(os.path, "exists", return_value=True), \
         patch("builtins.open", mock_open(read_data="User-agent: *")):
        result = lh.serve_robots()
    assert result["statusCode"] == 200
    assert result["body"] == "User-agent: *"


def test_serve_robots_read_failure_returns_500():
    with patch.object(os.path, "exists", return_value=True), \
         patch("builtins.open", side_effect=OSError("disk error")):
        result = lh.serve_robots()
    assert result["statusCode"] == 500


# ── serve_seo_html ─────────────────────────────────────────────────────────────

def test_serve_seo_html_success(monkeypatch, tmp_path):
    post_dir = tmp_path / "blog" / "my-post"
    post_dir.mkdir(parents=True)
    (post_dir / "index.html").write_text(f"<title>{lh.SEO_DOMAIN_PLACEHOLDER}</title>")
    monkeypatch.setattr(lh, "FRONTEND_DIST_DIR", str(tmp_path))

    result = lh.serve_seo_html("/blog/my-post", "https://real.example.com")
    assert result["statusCode"] == 200
    assert "https://real.example.com" in result["body"]


def test_serve_seo_html_not_found(monkeypatch, tmp_path):
    monkeypatch.setattr(lh, "FRONTEND_DIST_DIR", str(tmp_path))
    result = lh.serve_seo_html("/blog/missing")
    assert result["statusCode"] == 404


def test_serve_seo_html_blocks_path_traversal(monkeypatch, tmp_path):
    monkeypatch.setattr(lh, "FRONTEND_DIST_DIR", str(tmp_path))
    result = lh.serve_seo_html("/../../etc/passwd")
    assert result["statusCode"] == 404


def test_serve_seo_html_read_failure_returns_500(monkeypatch, tmp_path):
    post_dir = tmp_path / "blog" / "my-post"
    post_dir.mkdir(parents=True)
    (post_dir / "index.html").write_text("content")
    monkeypatch.setattr(lh, "FRONTEND_DIST_DIR", str(tmp_path))
    with patch("builtins.open", side_effect=OSError("disk error")):
        result = lh.serve_seo_html("/blog/my-post")
    assert result["statusCode"] == 500
