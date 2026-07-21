"""
ONVIF Device Service Handler

Handles all ONVIF Device service operations (tds namespace).
These are the most commonly used ONVIF operations that NVRs rely on
for camera discovery, configuration, and status monitoring.
"""

import logging
from typing import Optional, Dict, Any
from lxml import etree

from .parser import ONVIFRequest
from .responder import ONVIFResponder
from .xsd_types import (
    ONVIF_DEVICE_NS,
    ONVIF_NS,
    make_element,
    make_complex_element,
)

logger = logging.getLogger(__name__)


class DeviceServiceHandler:
    """
    Handles ONVIF Device service operations.

    Supported operations:
    - GetDeviceInformation
    - GetCapabilities
    - GetDeviceDateAndTime
    - GetSystemDateAndTime
    - SetSystemDateAndTime
    - GetNetworkInterfaces
    - GetNetworkProtocols
    - GetScopes
    - GetWsdl
    - GetUsers
    - GetServiceCapabilities
    """

    def __init__(self, responder: ONVIFResponder, camera_config: Optional[Dict[str, Any]] = None):
        self.responder = responder
        self.camera_config = camera_config or {}

    def handle(self, request: ONVIFRequest) -> bytes:
        """
        Route and handle a Device service request.

        Args:
            request: Parsed ONVIF request

        Returns:
            SOAP response bytes
        """
        operation = request.operation

        handlers = {
            "GetDeviceInformation": self._handle_get_device_info,
            "GetCapabilities": self._handle_get_capabilities,
            "GetDeviceDateAndTime": self._handle_get_device_date_time,
            "GetSystemDateAndTime": self._handle_get_system_date_time,
            "SetSystemDateAndTime": self._handle_set_system_date_time,
            "GetNetworkInterfaces": self._handle_get_network_interfaces,
            "GetNetworkProtocols": self._handle_get_network_protocols,
            "GetScopes": self._handle_get_scopes,
            "GetWsdl": self._handle_get_wsdl,
            "GetUsers": self._handle_get_users,
            "GetServiceCapabilities": self._handle_get_service_capabilities,
            "GetDPAddresses": self._handle_get_dp_addresses,
            "Reboot": self._handle_reboot,
        }

        handler = handlers.get(operation)
        if handler is None:
            logger.warning(f"Unhandled Device operation: {operation}")
            return self.responder.build_error_response(
                request_message_id=request.message_id,
                action=request.action,
                code="tds:ActionNotSupported",
                message=f"Operation {operation} is not supported by this device",
            )

        try:
            return handler(request)
        except Exception as e:
            logger.error(f"Error handling {operation}: {e}", exc_info=True)
            return self.responder.build_error_response(
                request_message_id=request.message_id,
                action=request.action,
                code="tds:InternalServerError",
                message=str(e),
            )

    def _handle_get_device_info(self, request: ONVIFRequest) -> bytes:
        """Handle GetDeviceInfo request."""
        config = self.camera_config
        return self.responder.build_device_info_response(
            request_message_id=request.message_id,
            manufacturer=config.get("manufacturer", "ONVIF Middleware"),
            model=config.get("model", "Middleware Camera Emulator"),
            firmware_version=config.get("firmware_version", "1.0.0"),
            serial_number=config.get("serial_number", "000000000000"),
            hardware_id=config.get("hardware_id", "ONVIF-MW-001"),
        )

    def _handle_get_capabilities(self, request: ONVIFRequest) -> bytes:
        """Handle GetCapabilities request."""
        config = self.camera_config
        base_url = config.get("onvif_url", "http://0.0.0.0:8080/onvif")

        capabilities = {
            "Device": f"{base_url}/device",
            "Media": f"{base_url}/media",
            "PTZ": f"{base_url}/ptz",
            "Events": f"{base_url}/events",
            "Imaging": f"{base_url}/imaging",
            "Recording": f"{base_url}/recording",
            "Search": f"{base_url}/search",
            "Receiver": f"{base_url}/receiver",
        }

        # Add Analytics if configured
        if config.get("analytics", False):
            capabilities["Analytics"] = f"{base_url}/analytics"

        # Add DeviceIO if configured
        if config.get("deviceio", False):
            capabilities["DeviceIO"] = f"{base_url}/deviceio"

        return self.responder.build_capabilities_response(
            request_message_id=request.message_id,
            capabilities=capabilities,
        )

    def _handle_get_device_date_time(self, request: ONVIFRequest) -> bytes:
        """Handle GetDeviceDateAndTime request."""
        from datetime import datetime, timezone

        action = "http://www.onvif.org/ver10/device/wsdl/GetDeviceDateAndTime"
        utc_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        resp = make_element("GetDeviceDateAndTimeResponse", ONVIF_DEVICE_NS)
        date_time = make_element("DeviceDateTime", ONVIF_NS)
        date_time.append(make_element("UTCDateTime", ONVIF_NS, utc_now))
        resp.append(date_time)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_get_system_date_time(self, request: ONVIFRequest) -> bytes:
        """Handle GetSystemDateAndTime request."""
        return self.responder.build_system_date_time_response(
            request_message_id=request.message_id,
        )

    def _handle_set_system_date_time(self, request: ONVIFRequest) -> bytes:
        """Handle SetSystemDateAndTime request."""
        action = "http://www.onvif.org/ver10/device/wsdl/SetSystemDateAndTime"

        resp = make_element("SetSystemDateAndTimeResponse", ONVIF_DEVICE_NS)
        logger.info(f"SetSystemDateAndTime requested: {request.parameters}")

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_get_network_interfaces(self, request: ONVIFRequest) -> bytes:
        """Handle GetNetworkInterfaces request."""
        return self.responder.build_network_interfaces_response(
            request_message_id=request.message_id,
        )

    def _handle_get_network_protocols(self, request: ONVIFRequest) -> bytes:
        """Handle GetNetworkProtocols request."""
        return self.responder.build_network_protocols_response(
            request_message_id=request.message_id,
        )

    def _handle_get_scopes(self, request: ONVIFRequest) -> bytes:
        """Handle GetScopes request."""
        action = "http://www.onvif.org/ver10/device/wsdl/GetScopes"

        resp = make_element("GetScopesResponse", ONVIF_DEVICE_NS)
        scopes_elem = make_element("Scopes", ONVIF_NS)

        # Default scopes
        default_scopes = [
            "onvif://www.onvif.org/type/IPC",
            "onvif://www.onvif.org/hardware/MiddlewareCamera",
            "onvif://www.onvif.org/Profile/Streaming",
            "onvif://www.onvif.org/Device/Onvif",
        ]

        # Add any configured scopes
        configured_scopes = self.camera_config.get("scopes", default_scopes)

        for scope in configured_scopes:
            scope_elem = make_element("Item", ONVIF_NS, scope)
            scopes_elem.append(scope_elem)

        resp.append(scopes_elem)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_get_wsdl(self, request: ONVIFRequest) -> bytes:
        """Handle GetWsdl request."""
        # ONVIF WSDL is typically served as a separate file
        # Return a minimal placeholder or redirect
        wsdl = self._generate_device_wsdl()
        return self.responder.build_wsdl_response(
            request_message_id=request.message_id,
            wsdl_content=wsdl,
        )

    def _handle_get_users(self, request: ONVIFRequest) -> bytes:
        """Handle GetUsers request."""
        action = "http://www.onvif.org/ver10/device/wsdl/GetUsers"

        resp = make_element("GetUsersResponse", ONVIF_DEVICE_NS)

        # Return default admin user
        user = make_element("User", ONVIF_NS)
        user.append(make_element("UserName", ONVIF_NS, "admin"))
        user.append(make_element("UserLevel", ONVIF_NS, "Administrator"))
        resp.append(user)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_get_service_capabilities(self, request: ONVIFRequest) -> bytes:
        """Handle GetServiceCapabilities request."""
        action = "http://www.onvif.org/ver10/device/wsdl/GetServiceCapabilities"

        resp = make_element("GetServiceCapabilitiesResponse", ONVIF_DEVICE_NS)

        caps = make_element("Capabilities", ONVIF_NS)
        caps.set("DeviceCapabilities_XSI_TYPE", "tds:DeviceCapabilities")

        # Device capabilities
        dev_caps = make_element("DeviceCapabilities", ONVIF_NS)
        dev_caps.set("XSI_TYPE", "tds:DeviceCapabilities")
        caps.append(dev_caps)

        resp.append(caps)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_get_dp_addresses(self, request: ONVIFRequest) -> bytes:
        """Handle GetDPAddresses request (Discovery Protocol addresses)."""
        action = "http://www.onvif.org/ver10/device/wsdl/GetDPAddresses"

        resp = make_element("GetDPAddressesResponse", ONVIF_DEVICE_NS)

        # Return discovery proxy addresses
        addr = make_element("FromDP", ONVIF_NS)
        addr.append(make_element("FromAddress", ONVIF_NS, "192.168.1.100"))
        addr.append(make_element("FromPort", ONVIF_NS, "3702"))
        resp.append(addr)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_reboot(self, request: ONVIFRequest) -> bytes:
        """Handle Reboot request (returns success without actually rebooting)."""
        action = "http://www.onvif.org/ver10/device/wsdl/Reboot"

        logger.warning("Reboot requested - middleware will not actually reboot")

        resp = make_element("RebootResponse", ONVIF_DEVICE_NS)

        return self.responder.build_response(request.message_id, action, resp)

    def _generate_device_wsdl(self) -> str:
        """Generate a minimal ONVIF Device WSDL response."""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<definitions name="DeviceService"
    targetNamespace="http://www.onvif.org/ver10/device/wsdl"
    xmlns="http://schemas.xmlsoap.org/wsdl/"
    xmlns:tds="http://www.onvif.org/ver10/device/wsdl"
    xmlns:trt="http://www.onvif.org/ver10/media/wsdl"
    xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/">

    <types>
        <schema targetNamespace="http://www.onvif.org/ver10/schema"
            xmlns="http://www.w3.org/2001/XMLSchema">
            <element name="DeviceInformation">
                <complexType>
                    <sequence>
                        <element name="Manufacturer" type="tt:ReferenceToken"/>
                        <element name="Model" type="tt:ReferenceToken"/>
                        <element name="FirmwareVersion" type="tt:ReferenceToken"/>
                        <element name="SerialNumber" type="tt:ReferenceToken"/>
                        <element name="HardwareId" type="tt:ReferenceToken"/>
                    </sequence>
                </complexType>
            </element>
        </schema>
    </types>

    <message name="GetDeviceInfoRequest">
        <part name="body" element="tds:GetDeviceInfo"/>
    </message>
    <message name="GetDeviceInfoResponse">
        <part name="body" element="tds:GetDeviceInfoResponse"/>
    </message>

    <portType name="DeviceService">
        <operation name="GetDeviceInfo">
            <input message="tds:GetDeviceInfoRequest"/>
            <output message="tds:GetDeviceInfoResponse"/>
        </operation>
    </portType>
</definitions>
'''
