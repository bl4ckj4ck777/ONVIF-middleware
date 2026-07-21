"""
ONVIF Request Parser

Parses incoming SOAP/XML requests from the NVR, extracts WS-Addressing headers,
identifies the ONVIF service and operation, and extracts request parameters.
"""

import logging
from typing import Optional, Dict, Any, Tuple
from lxml import etree

from .ws_addressing import (
    parse_ws_addressing_header,
    extract_soap_body,
    WS_ADDR_NS,
)

logger = logging.getLogger(__name__)

# ONVIF namespace mapping for operation identification
ONVIF_NAMESPACES = {
    "tds": "http://www.onvif.org/ver10/device/wsdl",
    "trt": "http://www.onvif.org/ver10/media/wsdl",
    "tptz": "http://www.onvif.org/ver10/ptz/wsdl",
    "tev": "http://www.onvif.org/ver10/events/wsdl",
    "timg": "http://www.onvif.org/ver20/imaging/wsdl",
    "trc": "http://www.onvif.org/ver10/recording/wsdl",
    "tst": "http://www.onvif.org/ver10/search/wsdl",
    "ter": "http://www.onvif.org/ver10/error",
}


class ONVIFRequest:
    """Represents a parsed ONVIF SOAP request from the NVR."""

    def __init__(
        self,
        operation: str,
        service: str,
        action: str,
        source_ip: str,
        timestamp: str,
        message_id: str,
        relates_to: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        raw_body: Optional[etree._Element] = None,
    ):
        self.operation = operation
        self.service = service
        self.action = action
        self.source_ip = source_ip
        self.timestamp = timestamp
        self.message_id = message_id
        self.relates_to = relates_to
        self.parameters = parameters or {}
        self.raw_body = raw_body

    def __repr__(self) -> str:
        return (
            f"ONVIFRequest(service={self.service}, operation={self.operation}, "
            f"message_id={self.message_id}, source={self.source_ip})"
        )


class ONVIFRequestParser:
    """
    Parses incoming ONVIF SOAP requests.

    Extracts:
    - WS-Addressing headers (MessageID, Action, ReplyTo, RelatesTo)
    - Service and operation from the Action header or body element
    - Request parameters from the SOAP body
    """

    def __init__(self):
        self.ns = ONVIF_NAMESPACES

    def parse(
        self,
        raw_xml: bytes,
        source_ip: str = "127.0.0.1",
    ) -> ONVIFRequest:
        """
        Parse a complete ONVIF SOAP request.

        Args:
            raw_xml: Raw SOAP XML bytes from the NVR
            source_ip: Source IP address of the request

        Returns:
            Parsed ONVIFRequest object

        Raises:
            etree.XMLSyntaxError: If the XML is malformed
            ValueError: If the request cannot be parsed
        """
        try:
            root = etree.fromstring(raw_xml)
        except etree.XMLSyntaxError as e:
            logger.error(f"Malformed XML received from {source_ip}: {e}")
            raise

        # Extract WS-Addressing headers
        ws_addr = parse_ws_addressing_header(root)

        # Extract SOAP body
        body = extract_soap_body(root)
        if body is None:
            raise ValueError("No SOAP Body found in request")

        # Identify the operation
        operation, service = self._identify_operation(body)

        # Extract parameters from the body
        parameters = self._extract_parameters(body, operation)

        return ONVIFRequest(
            operation=operation,
            service=service,
            action=ws_addr.get("action", ""),
            source_ip=source_ip,
            timestamp=ws_addr.get("message_id", ""),
            message_id=ws_addr.get("message_id", ""),
            relates_to=ws_addr.get("relates_to"),
            parameters=parameters,
            raw_body=body,
        )

    def _identify_operation(self, body: etree._Element) -> Tuple[str, str]:
        """
        Identify the ONVIF operation and service from the SOAP body.

        Returns:
            Tuple of (operation_name, service_name)
        """
        # Get the local name of the body element
        body_tag = body.tag
        if isinstance(body_tag, str):
            # Extract local name from fully qualified tag
            if "}" in body_tag:
                local_name = body_tag.split("}")[1]
            else:
                local_name = body_tag
        else:
            local_name = str(body_tag)

        # Map operations to services based on known ONVIF operations
        service_map = self._get_service_map()

        if local_name in service_map:
            return local_name, service_map[local_name]

        # Try to identify from namespace
        for prefix, namespace in self.ns.items():
            if namespace in body_tag:
                return local_name, prefix

        logger.warning(f"Unknown ONVIF operation: {local_name}")
        return local_name, "unknown"

    def _get_service_map(self) -> Dict[str, str]:
        """Return mapping of operation names to service names."""
        return {
            # Device service operations
            "GetCapabilities": "tds",
            "GetDeviceInformation": "tds",
            "GetDeviceDateAndTime": "tds",
            "SetSystemDateAndTime": "tds",
            "GetSystemDateAndTime": "tds",
            "GetNodes": "tds",
            "GetScopes": "tds",
            "SetScopes": "tds",
            "AddScopes": "tds",
            "RemoveScopes": "tds",
            "GetDiscoveryMode": "tds",
            "SetDiscoveryMode": "tds",
            "GetRemoteDiscoveryMode": "tds",
            "GetDPAddresses": "tds",
            "GetInterfaces": "tds",
            "SetInterface": "tds",
            "GetNetworkProtocols": "tds",
            "SetNetworkProtocol": "tds",
            "Reboot": "tds",
            "GetWsdl": "tds",
            "GetUsers": "tds",
            "CreateUsers": "tds",
            "DeleteUsers": "tds",
            "ModifyUsers": "tds",
            "GetUserLevels": "tds",
            "GetServiceCapabilities": "tds",
            "GetAuthInformation": "tds",
            # Media service operations
            "GetProfiles": "trt",
            "GetProfile": "trt",
            "CreateProfile": "trt",
            "DeleteProfile": "trt",
            "GetVideoSources": "trt",
            "GetVideoSourceModes": "trt",
            "GetStreamOptions": "trt",
            "GetStreamUri": "trt",
            "StartStreamUri": "trt",
            "StopStreamUri": "trt",
            "GetSnaps": "trt",
            "GetVideoEncoderConfiguration": "trt",
            "SetVideoEncoderConfiguration": "trt",
            "GetVideoEncoderConfigurationOptions": "trt",
            "GetVideoAnalyticsConfiguration": "trt",
            "SetVideoAnalyticsConfiguration": "trt",
            "GetMetadataConfiguration": "trt",
            "SetMetadataConfiguration": "trt",
            "GetAudioEncoderConfiguration": "trt",
            "SetAudioEncoderConfiguration": "trt",
            "GetAudioStreams": "trt",
            # PTZ service operations
            "GetConfigurations": "tptz",
            "GetConfigurationOptions": "tptz",
            "GetNode": "tptz",
            "GetNodes": "tptz",
            "GetPresets": "tptz",
            "GetPreset": "tptz",
            "SetPreset": "tptz",
            "RemovePreset": "tptz",
            "GotoPreset": "tptz",
            "GetDynamicPresets": "tptz",
            "GotoPresetStyle": "tptz",
            "ContinuousMove": "tptz",
            "RelativeMove": "tptz",
            "Stop": "tptz",
            "AbsoluteMove": "tptz",
            "SendAuxiliaryCommand": "tptz",
            # Event service operations
            "Subscribe": "tev",
            "Unsubscribe": "tev",
            "GetEventProperties": "tev",
            "PullMessages": "tev",
            "UnpullMessages": "tev",
            "Renew": "tev",
            # Imaging service operations
            "GetOptions": "timg",
            "GetStatus": "timg",
            "GetImagingSettings": "timg",
            "SetImagingSettings": "timg",
            "GetMovieMode": "timg",
            "SetMovieMode": "timg",
        }

    def _extract_parameters(
        self, body: etree._Element, operation: str
    ) -> Dict[str, Any]:
        """
        Extract request parameters from the SOAP body element.

        Args:
            body: The SOAP Body element
            operation: The identified operation name

        Returns:
            Dictionary of parameter names and values
        """
        params = {}

        # Handle different operations with specific parameter extraction
        if operation == "GetStreamUri":
            params = self._extract_stream_uri_params(body)
        elif operation in ("AbsoluteMove", "RelativeMove", "ContinuousMove"):
            params = self._extract_ptz_params(body)
        elif operation in ("GotoPreset", "SetPreset", "RemovePreset", "GetPresets"):
            params = self._extract_ptz_preset_params(body)
        elif operation == "SetImagingSettings":
            params = self._extract_imaging_params(body)
        elif operation == "SetSystemDateAndTime":
            params = self._extract_date_time_params(body)
        elif operation == "GetConfigurations":
            params = self._extract_config_params(body)
        else:
            # Generic parameter extraction for other operations
            params = self._generic_extract(body)

        logger.debug(f"Extracted parameters for {operation}: {list(params.keys())}")
        return params

    def _extract_stream_uri_params(self, body: etree._Element) -> Dict[str, Any]:
        """Extract GetStreamUri request parameters."""
        params = {}

        stream_setup = body.find(".//tt:StreamSetup", {"tt": "http://www.onvif.org/ver10/schema"})
        if stream_setup is not None:
            stream = stream_setup.find("tt:Stream", {"tt": "http://www.onvif.org/ver10/schema"})
            if stream is not None and stream.text:
                params["stream"] = stream.text
            transport = stream_setup.find("tt:Transport", {"tt": "http://www.onvif.org/ver10/schema"})
            if transport is not None:
                protocol = transport.find("tt:Protocol", {"tt": "http://www.onvif.org/ver10/schema"})
                if protocol is not None and protocol.text:
                    params["protocol"] = protocol.text

        profile_token = body.find("tt:ProfileToken", {"tt": "http://www.onvif.org/ver10/schema"})
        if profile_token is not None and profile_token.text:
            params["profile_token"] = profile_token.text

        return params

    def _extract_ptz_params(self, body: etree._Element) -> Dict[str, Any]:
        """Extract PTZ movement parameters."""
        params = {}

        profile_token = body.find("tt:ProfileToken", {"tt": "http://www.onvif.org/ver10/schema"})
        if profile_token is not None and profile_token.text:
            params["profile_token"] = profile_token.text

        # Extract pan/tilt/zoom values
        for axis in ["PanTilt", "Zoom"]:
            elem = body.find(f".//tt:{axis}", {"tt": "http://www.onvif.org/ver10/schema"})
            if elem is not None:
                x_elem = elem.find("tt:x", {"tt": "http://www.onvif.org/ver10/schema"})
                y_elem = elem.find("tt:y", {"tt": "http://www.onvif.org/ver10/schema"})
                if x_elem is not None:
                    params[f"{axis.lower()}_x"] = float(x_elem.text) if x_elem.text else 0.0
                if y_elem is not None:
                    params[f"{axis.lower()}_y"] = float(y_elem.text) if y_elem.text else 0.0
                # Zoom uses 'zoom' instead of 'x'
                if axis == "Zoom":
                    zoom_elem = elem.find("tt:zoom", {"tt": "http://www.onvif.org/ver10/schema"})
                    if zoom_elem is not None:
                        params["zoom"] = float(zoom_elem.text) if zoom_elem.text else 0.0

        # Duration (optional)
        duration = body.find("tt:Timeout", {"tt": "http://www.onvif.org/ver10/schema"})
        if duration is not None and duration.text:
            params["duration"] = duration.text

        return params

    def _extract_ptz_preset_params(self, body: etree._Element) -> Dict[str, Any]:
        """Extract PTZ preset-related parameters."""
        params = {}

        profile_token = body.find("tt:ProfileToken", {"tt": "http://www.onvif.org/ver10/schema"})
        if profile_token is not None and profile_token.text:
            params["profile_token"] = profile_token.text

        preset_token = body.find("tt:PresetToken", {"tt": "http://www.onvif.org/ver10/schema"})
        if preset_token is not None and preset_token.text:
            params["preset_token"] = preset_token.text

        return params

    def _extract_imaging_params(self, body: etree._Element) -> Dict[str, Any]:
        """Extract imaging settings parameters."""
        params = {}

        video_source_token = body.find(
            "tt:VideoSourceToken", {"tt": "http://www.onvif.org/ver10/schema"}
        )
        if video_source_token is not None and video_source_token.text:
            params["video_source_token"] = video_source_token.text

        # Extract imaging settings
        settings = body.find("timg:ImagingSettings", {"timg": "http://www.onvif.org/ver20/imaging/wsdl"})
        if settings is not None:
            for setting_name in ["Focus", "Iris", "WhiteBalance", "Brightness", "Contrast"]:
                setting_elem = settings.find(f"tt:{setting_name}", {"tt": "http://www.onvif.org/ver10/schema"})
                if setting_elem is not None:
                    mode = setting_elem.find("tt:Mode", {"tt": "http://www.onvif.org/ver10/schema"})
                    if mode is not None and mode.text:
                        params[f"{setting_name.lower()}_mode"] = mode.text

        return params

    def _extract_date_time_params(self, body: etree._Element) -> Dict[str, Any]:
        """Extract date/time configuration parameters."""
        params = {}

        # Type (DHCP or Manual)
        type_elem = body.find("tt:Type", {"tt": "http://www.onvif.org/ver10/schema"})
        if type_elem is not None and type_elem.text:
            params["type"] = type_elem.text

        # DHCP preserve
        dhcp = body.find("tt:DHCPPreserve", {"tt": "http://www.onvif.org/ver10/schema"})
        if dhcp is not None and dhcp.text:
            params["dhcp_preserve"] = dhcp.text.lower() == "true"

        return params

    def _extract_config_params(self, body: etree._Element) -> Dict[str, Any]:
        """Extract configuration request parameters."""
        params = {}

        token = body.find("tt:Token", {"tt": "http://www.onvif.org/ver10/schema"})
        if token is not None and token.text:
            params["token"] = token.text

        return params

    def _generic_extract(self, body: etree._Element) -> Dict[str, Any]:
        """
        Generic parameter extraction for operations not specifically handled.

        Extracts all child elements as key-value pairs.
        """
        params = {}
        ns = {"tt": "http://www.onvif.org/ver10/schema"}

        for child in body:
            tag = child.tag
            if isinstance(tag, str) and "}" in tag:
                tag = tag.split("}")[1]

            if child.text and child.text.strip():
                params[tag] = child.text.strip()
            else:
                # Try to extract nested values
                nested = {}
                for sub in child:
                    if sub.text and sub.text.strip():
                        nested[sub.tag.split("}")[1] if "}" in sub.tag else sub.tag] = sub.text.strip()
                if nested:
                    params[tag] = nested

        return params
