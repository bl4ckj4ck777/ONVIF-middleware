"""
ONVIF SOAP Server

Main HTTP server that listens for ONVIF SOAP requests from the NVR,
routes them to the appropriate service handlers, and returns properly
formatted SOAP responses.
"""

import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Optional, Dict, Any, Callable
from urllib.parse import urlparse

from .parser import ONVIFRequestParser, ONVIFRequest
from .responder import ONVIFResponder
from .device_service import DeviceServiceHandler
from .media_service import MediaServiceHandler
from .ptz_service import PTZServiceHandler
from .event_service import EventServiceHandler
from .imaging_service import ImagingServiceHandler

logger = logging.getLogger(__name__)


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTP server that handles each request in a new thread."""
    daemon_threads = True
    allow_reuse_address = True


class ONVIFRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for ONVIF SOAP requests."""

    # Reference to the server instance
    server_instance: "ONVIFServer" = None

    def do_POST(self) -> None:
        """Handle POST requests (ONVIF SOAP calls)."""
        # Parse the URL to determine the target service
        parsed = urlparse(self.path)
        service_path = parsed.path.strip("/").lower()

        # Read request body
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b""

        # Get source IP
        source_ip = self.client_address[0]

        logger.info(f"ONVIF request from {source_ip}: {self.path}")

        # Route to appropriate handler
        try:
            if self._is_device_service(service_path):
                response = self.server_instance._handle_device_request(raw_body, source_ip)
            elif self._is_media_service(service_path):
                response = self.server_instance._handle_media_request(raw_body, source_ip)
            elif self._is_ptz_service(service_path):
                response = self.server_instance._handle_ptz_request(raw_body, source_ip)
            elif self._is_event_service(service_path):
                response = self.server_instance._handle_event_request(raw_body, source_ip)
            elif self._is_imaging_service(service_path):
                response = self.server_instance._handle_imaging_request(raw_body, source_ip)
            elif service_path in ("onvif", "onvif/device", "onvif/media", "onvif/ptz", "onvif/events", "onvif/imaging"):
                # Generic ONVIF endpoint - try to parse and route
                response = self.server_instance._handle_generic_request(raw_body, source_ip)
            else:
                response = self.server_instance._not_found(service_path)
        except Exception as e:
            logger.error(f"Error processing ONVIF request: {e}", exc_info=True)
            response = self.server_instance._handle_error(
                message_id="",
                action="",
                code="soap:Sender",
                message=f"Server error processing request: {e}",
            )

        # Send response
        self._send_response(response)

    def do_GET(self) -> None:
        """Handle GET requests (WSDL, health checks)."""
        parsed = urlparse(self.path)
        service_path = parsed.path.strip("/").lower()

        if service_path in ("wsdl", "onvif/wsdl", "device.wsdl", "media.wsdl", "ptz.wsdl"):
            response = self.server_instance._get_wsdl(service_path)
        elif service_path in ("health", "onvif/health", "status"):
            response = self.server_instance._health_check()
        else:
            response = self.server_instance._not_found(service_path)

        self._send_response(response)

    def _send_response(self, response: bytes) -> None:
        """Send HTTP response with ONVIF SOAP body."""
        self.send_response(200)
        self.send_header("Content-Type", "application/soap+xml; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Server", "ONVIF-Middleware/1.0")
        self.end_headers()
        self.wfile.write(response)

    def _is_device_service(self, path: str) -> bool:
        """Check if path maps to Device service."""
        return path in ("device", "onvif/device", "onvif/devicemgmt")

    def _is_media_service(self, path: str) -> bool:
        """Check if path maps to Media service."""
        return path in ("media", "onvif/media")

    def _is_ptz_service(self, path: str) -> bool:
        """Check if path maps to PTZ service."""
        return path in ("ptz", "onvif/ptz")

    def _is_event_service(self, path: str) -> bool:
        """Check if path maps to Event service."""
        return path in ("events", "onvif/events")

    def _is_imaging_service(self, path: str) -> bool:
        """Check if path maps to Imaging service."""
        return path in ("imaging", "onvif/imaging")

    def log_message(self, format: str, *args: Any) -> None:
        """Override to use logger instead of stderr."""
        logger.debug(f"HTTP: {format % args}")


class ONVIFServer:
    """
    ONVIF middleware server that intercepts and handles ONVIF SOAP requests.

    Listens on a configurable port and routes incoming ONVIF requests to
    the appropriate service handlers. Each service handler translates the
    ONVIF request into native camera API calls and formats the response
    back into ONVIF format.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        camera_config: Optional[Dict[str, Any]] = None,
        request_timeout: int = 30,
    ):
        self.host = host
        self.port = port
        self.camera_config = camera_config or {}
        self.request_timeout = request_timeout
        self._running = False
        self._server: Optional[ThreadingHTTPServer] = None
        self._request_parser = ONVIFRequestParser()
        self._responder = ONVIFResponder(
            server_url=f"http://{host}:{port}/onvif"
        )

        # Initialize service handlers
        self._device_handler = DeviceServiceHandler(self._responder, self.camera_config)
        self._media_handler = MediaServiceHandler(self._responder, self.camera_config)
        self._ptz_handler = PTZServiceHandler(self._responder, self.camera_config)
        self._event_handler = EventServiceHandler(self._responder, self.camera_config)
        self._imaging_handler = ImagingServiceHandler(self._responder, self.camera_config)

        # Custom request hooks
        self._custom_handlers: Dict[str, Callable] = {}

    def start(self) -> None:
        """Start the ONVIF server."""
        # Configure the request handler
        ONVIFRequestHandler.server_instance = self

        # Create and start the server
        self._server = ThreadingHTTPServer((self.host, self.port), ONVIFRequestHandler)
        self._running = True

        logger.info(f"ONVIF Middleware server starting on {self.host}:{self.port}")
        logger.info(f"Camera config: {list(self.camera_config.keys())}")

        try:
            self._server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Server shutting down...")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the ONVIF server."""
        self._running = False
        if self._server:
            self._server.shutdown()
            self._server = None
            logger.info("ONVIF Middleware server stopped")

    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._running

    # ============================================================
    # Request Handlers
    # ============================================================

    def _handle_device_request(self, raw_xml: bytes, source_ip: str) -> bytes:
        """Handle a Device service request."""
        try:
            request = self._request_parser.parse(raw_xml, source_ip)
            return self._device_handler.handle(request)
        except ValueError as e:
            return self._responder.build_error_response(
                request_message_id="",
                action="",
                code="soap:Receiver",
                message=str(e),
            )

    def _handle_media_request(self, raw_xml: bytes, source_ip: str) -> bytes:
        """Handle a Media service request."""
        try:
            request = self._request_parser.parse(raw_xml, source_ip)
            return self._media_handler.handle(request)
        except ValueError as e:
            return self._responder.build_error_response(
                request_message_id="",
                action="",
                code="soap:Receiver",
                message=str(e),
            )

    def _handle_ptz_request(self, raw_xml: bytes, source_ip: str) -> bytes:
        """Handle a PTZ service request."""
        try:
            request = self._request_parser.parse(raw_xml, source_ip)
            return self._ptz_handler.handle(request)
        except ValueError as e:
            return self._responder.build_error_response(
                request_message_id="",
                action="",
                code="soap:Receiver",
                message=str(e),
            )

    def _handle_event_request(self, raw_xml: bytes, source_ip: str) -> bytes:
        """Handle an Event service request."""
        try:
            request = self._request_parser.parse(raw_xml, source_ip)
            return self._event_handler.handle(request)
        except ValueError as e:
            return self._responder.build_error_response(
                request_message_id="",
                action="",
                code="soap:Receiver",
                message=str(e),
            )

    def _handle_imaging_request(self, raw_xml: bytes, source_ip: str) -> bytes:
        """Handle an Imaging service request."""
        try:
            request = self._request_parser.parse(raw_xml, source_ip)
            return self._imaging_handler.handle(request)
        except ValueError as e:
            return self._responder.build_error_response(
                request_message_id="",
                action="",
                code="soap:Receiver",
                message=str(e),
            )

    def _handle_generic_request(self, raw_xml: bytes, source_ip: str) -> bytes:
        """
        Handle a generic ONVIF request by parsing and routing based on Action header.

        Used when the request comes to a generic ONVIF endpoint without
        a specific service path.
        """
        try:
            request = self._request_parser.parse(raw_xml, source_ip)
        except ValueError as e:
            return self._responder.build_error_response(
                request_message_id="",
                action="",
                code="soap:Receiver",
                message=str(e),
            )

        # Route based on service type from the parsed request
        service_handlers = {
            "tds": self._device_handler.handle,
            "trt": self._media_handler.handle,
            "tptz": self._ptz_handler.handle,
            "tev": self._event_handler.handle,
            "timg": self._imaging_handler.handle,
        }

        handler = service_handlers.get(request.service)
        if handler:
            return handler(request)

        # Try custom handlers
        for pattern, custom_handler in self._custom_handlers.items():
            if pattern in request.operation.lower():
                return custom_handler(request)

        return self._responder.build_error_response(
            request_message_id=request.message_id,
            action=request.action,
            code="soap:Receiver",
            message=f"Unknown ONVIF service: {request.service}",
        )

    def _handle_error(
        self,
        message_id: str,
        action: str,
        code: str,
        message: str,
    ) -> bytes:
        """Build a generic error response."""
        return self._responder.build_error_response(
            request_message_id=message_id,
            action=action,
            code=code,
            message=message,
        )

    def _not_found(self, service_path: str) -> bytes:
        """Return 404 response."""
        response = b"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <soap:Fault>
      <faultcode>soap:Receiver</faultcode>
      <faultstring>Not Found: /{path}</faultstring>
    </soap:Fault>
  </soap:Body>
</soap:Envelope>""".format(path=service_path).encode("utf-8")
        return response

    def _get_wsdl(self, service_path: str) -> bytes:
        """Return WSDL content for the requested service."""
        wsdl_map = {
            "wsdl": self._device_handler._generate_device_wsdl(),
            "onvif/wsdl": self._device_handler._generate_device_wsdl(),
            "device.wsdl": self._device_handler._generate_device_wsdl(),
        }
        content = wsdl_map.get(service_path, self._device_handler._generate_device_wsdl())
        return content.encode("utf-8")

    def _health_check(self) -> bytes:
        """Return health check response."""
        status = {
            "status": "ok",
            "service": "ONVIF Middleware",
            "version": "1.0.0",
            "active_subscriptions": self._event_handler.get_subscription_count(),
            "ptz_moving": self._ptz_handler.is_moving(),
        }
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <HealthResponse xmlns="http://onvif.middleware/health">
      <Status>OK</Status>
      <Service>ONVIF Middleware</Service>
      <Version>1.0.0</Version>
    </HealthResponse>
  </soap:Body>
</soap:Envelope>""".encode("utf-8")

    # ============================================================
    # Configuration Accessors
    # ============================================================

    def get_ptz_position(self) -> Dict[str, float]:
        """Get current PTZ position."""
        return self._ptz_handler.get_current_position()

    def get_presets(self) -> list:
        """Get all PTZ presets."""
        return self._ptz_handler.get_presets_list()

    def get_active_subscriptions(self) -> int:
        """Get count of active event subscriptions."""
        return self._event_handler.get_subscription_count()

    def add_custom_handler(self, pattern: str, handler: Callable) -> None:
        """
        Register a custom handler for specific operations.

        Args:
            pattern: String pattern to match against operation names
            handler: Callable that takes an ONVIFRequest and returns bytes
        """
        self._custom_handlers[pattern] = handler

    def add_event_message(self, message_data: Dict[str, Any]) -> None:
        """
        Add an event message to the queue (for camera-to-NVR notifications).

        Args:
            message_data: Dictionary containing event data
        """
        self._event_handler.add_event_message(message_data)
