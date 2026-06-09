"""
HTTP server implementation using only Python standard library.
Supports routing, middleware, JSON parsing, and streaming responses.
"""

import json
import socketserver
import http.server
import threading
import time
import logging
from typing import Dict, Any, Callable, Optional, List, Tuple
from urllib.parse import urlparse, parse_qs


class Request:
    """HTTP Request wrapper."""

    def __init__(self, handler: http.server.BaseHTTPRequestHandler):
        self.handler = handler
        self.method = handler.command
        self.path = handler.path
        self.headers = dict(handler.headers)
        self.body: Optional[bytes] = None
        self.json_body: Optional[Dict[str, Any]] = None
        self.query_params: Dict[str, List[str]] = {}
        self.path_params: Dict[str, str] = {}
        self._parse_url()

    def _parse_url(self):
        """Parse URL components."""
        parsed = urlparse(self.path)
        self.path = parsed.path
        self.query_params = parse_qs(parsed.query)

    def read_body(self) -> bytes:
        """Read request body."""
        if self.body is None:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                self.body = self.handler.rfile.read(content_length)
            else:
                self.body = b""
        return self.body

    def get_json(self) -> Optional[Dict[str, Any]]:
        """Parse JSON body."""
        if self.json_body is None:
            body = self.read_body()
            if body:
                try:
                    self.json_body = json.loads(body.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    self.json_body = None
        return self.json_body

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get header value."""
        return self.headers.get(name, default)

    def get_client_ip(self) -> str:
        """Get client IP address."""
        forwarded = self.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self.handler.client_address[0]


class Response:
    """HTTP Response builder."""

    def __init__(self):
        self.status_code = 200
        self.headers: Dict[str, str] = {"Content-Type": "application/json"}
        self.body: Optional[bytes] = None
        self._streaming = False

    def set_status(self, code: int) -> "Response":
        self.status_code = code
        return self

    def set_header(self, name: str, value: str) -> "Response":
        self.headers[name] = value
        return self

    def json(self, data: Any) -> "Response":
        self.body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.headers["Content-Type"] = "application/json"
        return self

    def text(self, text: str, content_type: str = "text/plain") -> "Response":
        self.body = text.encode("utf-8")
        self.headers["Content-Type"] = content_type
        return self

    def error(self, message: str, status_code: int = 500) -> "Response":
        self.status_code = status_code
        self.json({"error": {"message": message, "type": "api_error", "code": status_code}})
        return self

    def stream(self, content_type: str = "text/event-stream") -> "Response":
        self._streaming = True
        self.headers["Content-Type"] = content_type
        self.headers["Cache-Control"] = "no-cache"
        self.headers["Connection"] = "keep-alive"
        return self


HandlerFunc = Callable[[Request], Response]
MiddlewareFunc = Callable[[Request, HandlerFunc], Response]


class Router:
    """Simple URL router."""

    def __init__(self):
        self.routes: Dict[str, Dict[str, HandlerFunc]] = {}
        self.middleware: List[MiddlewareFunc] = []

    def add_route(self, method: str, path: str, handler: HandlerFunc):
        """Add a route."""
        method = method.upper()
        if method not in self.routes:
            self.routes[method] = {}
        self.routes[method][path] = handler

    def get(self, path: str, handler: HandlerFunc):
        self.add_route("GET", path, handler)

    def post(self, path: str, handler: HandlerFunc):
        self.add_route("POST", path, handler)

    def put(self, path: str, handler: HandlerFunc):
        self.add_route("PUT", path, handler)

    def delete(self, path: str, handler: HandlerFunc):
        self.add_route("DELETE", path, handler)

    def add_middleware(self, middleware: MiddlewareFunc):
        """Add middleware."""
        self.middleware.append(middleware)

    def match(self, method: str, path: str) -> Tuple[Optional[HandlerFunc], Dict[str, str]]:
        """Match route and extract path parameters."""
        method = method.upper()
        if method not in self.routes:
            return None, {}

        # Exact match first
        if path in self.routes[method]:
            return self.routes[method][path], {}

        # Pattern match
        for route_path, handler in self.routes[method].items():
            if "{" in route_path:
                pattern = route_path
                param_names = []
                # Simple pattern: /api/{name} -> regex
                parts = []
                for segment in pattern.split("/"):
                    if segment.startswith("{") and segment.endswith("}"):
                        param_names.append(segment[1:-1])
                        parts.append("([^/]+)")
                    else:
                        parts.append(segment)
                regex_pattern = "^" + "/".join(parts) + "$"
                import re
                match = re.match(regex_pattern, path)
                if match:
                    params = {}
                    for i, name in enumerate(param_names):
                        params[name] = match.group(i + 1)
                    return handler, params

        return None, {}

    def handle(self, request: Request) -> Response:
        """Handle request through middleware chain."""
        handler, path_params = self.match(request.method, request.path)
        if handler is None:
            return Response().error("Not found", 404)

        request.path_params = path_params

        # Build middleware chain
        final_handler = handler
        for mw in reversed(self.middleware):
            final_handler = lambda req, h=final_handler, m=mw: m(req, h)

        return final_handler(request)


class HTTPServerHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler."""

    router: Optional[Router] = None
    logger: Optional[logging.Logger] = None

    def log_message(self, format: str, *args):
        if self.logger:
            self.logger.info(f"{self.address_string()} - {format % args}")
        else:
            super().log_message(format, *args)

    def do_GET(self):
        self._handle_request()

    def do_POST(self):
        self._handle_request()

    def do_PUT(self):
        self._handle_request()

    def do_DELETE(self):
        self._handle_request()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def _handle_request(self):
        if self.router is None:
            self.send_error(500, "Router not configured")
            return

        try:
            request = Request(self)
            response = self.router.handle(request)

            self.send_response(response.status_code)
            for name, value in response.headers.items():
                self.send_header(name, value)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            if response.body:
                self.wfile.write(response.body)

        except Exception as e:
            if self.logger:
                self.logger.error(f"Request error: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            error_body = json.dumps({"error": str(str(e))}).encode("utf-8")
            self.wfile.write(error_body)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Threaded HTTP server."""
    daemon_threads = True
    allow_reuse_address = True


class Server:
    """HTTP server wrapper."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        router: Optional[Router] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.host = host
        self.port = port
        self.router = router or Router()
        self.logger = logger
        self._server: Optional[ThreadedHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self, blocking: bool = True):
        """Start the server."""
        HTTPServerHandler.router = self.router
        HTTPServerHandler.logger = self.logger

        self._server = ThreadedHTTPServer((self.host, self.port), HTTPServerHandler)

        if self.logger:
            self.logger.info(f"Server starting on {self.host}:{self.port}")

        if blocking:
            self._server.serve_forever()
        else:
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()

    def stop(self):
        """Stop the server."""
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            if self.logger:
                self.logger.info("Server stopped")

    def is_running(self) -> bool:
        """Check if server is running."""
        return self._server is not None and self._thread is not None and self._thread.is_alive()
