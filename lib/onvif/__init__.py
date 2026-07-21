"""
ONVIF Middleware - ONVIF Protocol Communication Layer

Handles all ONVIF SOAP/XML communication with the NVR, including:
- Device, Media, PTZ, Event, and Imaging service operations
- WS-Addressing header parsing and generation
- ONVIF XML schema type construction
- Request routing to appropriate service handlers
"""

from .server import ONVIFServer
from .parser import ONVIFRequestParser
from .responder import ONVIFResponder

__all__ = ["ONVIFServer", "ONVIFRequestParser", "ONVIFResponder"]
