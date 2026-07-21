"""
ONVIF Response Builder

Constructs properly formatted ONVIF SOAP responses with WS-Addressing headers.
Wraps service-specific response elements in complete SOAP envelopes.
"""

import logging
from typing import Optional, Dict, Any
from lxml import etree

from .ws_addressing import (
    build_ws_addressing_header,
    build_soap_envelope,
    generate_message_id,
    generate_action,
    WS_ADDR_NS,
)
from .xsd_types import (
    ONVIF_DEVICE_NS,
    ONVIF_MEDIA_NS,
    ONVIF_PTZ_NS,
    ONVIF_EVENTS_NS,
    ONVIF_IMAGING_NS,
    ONVIF_NS,
    make_element,
    make_complex_element,
)

logger = logging.getLogger(__name__)


class ONVIFResponder:
    """
    Builds ONVIF SOAP responses for NVR requests.

    Handles:
    - WS-Addressing header generation (echoing request headers)
    - Service-specific response construction
    - Error/fault response formatting
    - SOAP envelope wrapping
    """

    def __init__(self, server_url: str = "http://0.0.0.0:8080/onvif"):
        self.server_url = server_url

    def build_response(
        self,
        request_message_id: str,
        action: str,
        body_element: etree._Element,
    ) -> bytes:
        """
        Build a complete ONVIF SOAP response.

        Args:
            request_message_id: MessageID from the incoming request
            action: Action header from the incoming request
            body_element: The response body element

        Returns:
            Complete SOAP envelope as bytes
        """
        # Build WS-Addressing header echoing request headers
        ws_header = build_ws_addressing_header(
            message_id=generate_message_id(),
            action=action,
            reply_to=self.server_url,
            relates_to=request_message_id,
            to=self.server_url,
        )

        # Wrap in SOAP envelope
        return build_soap_envelope(
            body_element=body_element,
            ws_addressing_header=ws_header,
        )

    def build_error_response(
        self,
        request_message_id: str,
        action: str,
        code: str,
        message: str,
        detail: Optional[str] = None,
    ) -> bytes:
        """
        Build a SOAP Fault response.

        Args:
            request_message_id: MessageID from the incoming request
            action: Action header from the incoming request
            code: SOAP fault code
            message: Human-readable fault message
            detail: Optional fault detail

        Returns:
            SOAP Fault envelope as bytes
        """
        fault = {
            "code": code,
            "string": message,
            "detail": detail or "",
        }

        ws_header = build_ws_addressing_header(
            message_id=generate_message_id(),
            action=action,
            reply_to=self.server_url,
            relates_to=request_message_id,
            to=self.server_url,
        )

        return build_soap_envelope(
            body_element=None,
            ws_addressing_header=ws_header,
            fault=fault,
        )

    # ============================================================
    # Device Service Responses
    # ============================================================

    def build_device_info_response(
        self,
        request_message_id: str,
        manufacturer: str = "ONVIF Middleware",
        model: str = "Middleware Camera Emulator",
        firmware_version: str = "1.0.0",
        serial_number: str = "000000000000",
        hardware_id: str = "ONVIF-MW-001",
    ) -> bytes:
        """Build GetDeviceInfo response."""
        action = generate_action("device", "GetDeviceInfo")

        from .xsd_types import build_device_info

        device_info = build_device_info(
            manufacturer=manufacturer,
            model=model,
            firmware_version=firmware_version,
            serial_number=serial_number,
            hardware_id=hardware_id,
        )

        resp = make_element("GetDeviceInfoResponse", ONVIF_DEVICE_NS)
        resp.append(device_info)

        return self.build_response(request_message_id, action, resp)

    def build_capabilities_response(
        self,
        request_message_id: str,
        capabilities: Optional[Dict[str, str]] = None,
    ) -> bytes:
        """Build GetCapabilities response."""
        action = generate_action("device", "GetCapabilities")

        if capabilities is None:
            capabilities = {
                "Device": f"{self.server_url}/device",
                "Media": f"{self.server_url}/media",
                "PTZ": f"{self.server_url}/ptz",
                "Events": f"{self.server_url}/events",
                "Imaging": f"{self.server_url}/imaging",
                "Recording": f"{self.server_url}/recording",
                "Search": f"{self.server_url}/search",
                "Receiver": f"{self.server_url}/receiver",
                "Analytics": f"{self.server_url}/analytics",
                "DeviceIO": f"{self.server_url}/deviceio",
            }

        from .xsd_types import build_capabilities

        caps = build_capabilities(capabilities)

        resp = make_element("GetCapabilitiesResponse", ONVIF_DEVICE_NS)
        resp.append(caps)

        return self.build_response(request_message_id, action, resp)

    def build_network_interfaces_response(
        self,
        request_message_id: str,
        interfaces: Optional[list] = None,
    ) -> bytes:
        """Build GetNetworkInterfaces response."""
        action = generate_action("device", "GetNetworkInterfaces")

        if interfaces is None:
            from .xsd_types import build_network_interface

            interfaces = [
                build_network_interface(
                    token="0",
                    enabled=True,
                    ipv4_address="192.168.1.100",
                    ipv4_subnet_prefix=24,
                    dhcp_enabled=False,
                ),
            ]

        resp = make_element("GetNetworkInterfacesResponse", ONVIF_DEVICE_NS)
        for iface in interfaces:
            resp.append(iface)

        return self.build_response(request_message_id, action, resp)

    def build_network_protocols_response(
        self,
        request_message_id: str,
        protocols: Optional[list] = None,
    ) -> bytes:
        """Build GetNetworkProtocols response."""
        action = generate_action("device", "GetNetworkProtocols")

        if protocols is None:
            from .xsd_types import build_network_protocol

            protocols = [
                build_network_protocol(name="HTTP", port=80),
                build_network_protocol(name="HTTPS", port=443),
                build_network_protocol(name="RTSP", port=554),
            ]

        resp = make_element("GetNetworkProtocolsResponse", ONVIF_DEVICE_NS)
        for proto in protocols:
            resp.append(proto)

        return self.build_response(request_message_id, action, resp)

    def build_system_date_time_response(
        self,
        request_message_id: str,
        use_dhcp: bool = False,
        utc_datetime: Optional[str] = None,
    ) -> bytes:
        """Build GetSystemDateAndTime response."""
        action = generate_action("device", "GetSystemDateAndTime")

        from datetime import datetime, timezone

        if utc_datetime is None:
            utc_datetime = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        children = [
            make_element("UTCDateTime", ONVIF_NS),
            make_element("Type", ONVIF_DEVICE_NS, "Manual" if not use_dhcp else "DHCP"),
        ]
        date_time_elem = children[0]
        date_time_elem.append(make_element("Time", ONVIF_NS, utc_datetime))

        resp = make_element("GetSystemDateAndTimeResponse", ONVIF_DEVICE_NS)
        resp.append(make_complex_element("SystemDateTime", ONVIF_NS, children))

        return self.build_response(request_message_id, action, resp)

    def build_wsdl_response(
        self,
        request_message_id: str,
        wsdl_content: str = "",
    ) -> bytes:
        """Build GetWsdl response."""
        action = generate_action("device", "GetWsdl")

        resp = make_element("GetWsdlResponse", ONVIF_DEVICE_NS)
        wsdl_elem = make_element("Wsdl", ONVIF_DEVICE_NS, wsdl_content)
        resp.append(wsdl_elem)

        return self.build_response(request_message_id, action, resp)

    # ============================================================
    # Media Service Responses
    # ============================================================

    def build_profiles_response(
        self,
        request_message_id: str,
        profiles: Optional[list] = None,
    ) -> bytes:
        """Build GetProfiles response."""
        action = generate_action("media", "GetProfiles")

        if profiles is None:
            from .xsd_types import build_media_profile

            profiles = [
                build_media_profile(
                    token="profile0",
                    name="Main",
                    video_source_token="video-source-0",
                    video_encoder_token="encoder0",
                    ptz_token="ptz-node-0",
                ),
                build_media_profile(
                    token="profile1",
                    name="Sub",
                    video_source_token="video-source-0",
                    video_encoder_token="encoder1",
                ),
            ]

        resp = make_element("GetProfilesResponse", ONVIF_MEDIA_NS)
        for profile in profiles:
            resp.append(profile)

        return self.build_response(request_message_id, action, resp)

    def build_stream_uri_response(
        self,
        request_message_id: str,
        stream_uri: str,
    ) -> bytes:
        """Build GetStreamUri response."""
        action = generate_action("media", "GetStreamUri")

        from .xsd_types import build_stream_uri_response

        media_uri = build_stream_uri_response(stream_uri)

        resp = make_element("GetStreamUriResponse", ONVIF_MEDIA_NS)
        resp.append(media_uri)

        return self.build_response(request_message_id, action, resp)

    def build_video_sources_response(
        self,
        request_message_id: str,
        sources: Optional[list] = None,
    ) -> bytes:
        """Build GetVideoSources response."""
        action = generate_action("media", "GetVideoSources")

        if sources is None:
            from .xsd_types import build_video_source

            sources = [
                build_video_source(token="video-source-0", width=1920, height=1080, framerate=30),
            ]

        resp = make_element("GetVideoSourcesResponse", ONVIF_MEDIA_NS)
        for source in sources:
            resp.append(source)

        return self.build_response(request_message_id, action, resp)

    def build_video_encoder_config_options_response(
        self,
        request_message_id: str,
        h264_options: Optional[etree._Element] = None,
        mpeg4_options: Optional[etree._Element] = None,
        jpeg_options: Optional[etree._Element] = None,
    ) -> bytes:
        """Build GetVideoEncoderConfigurationOptions response."""
        action = generate_action("media", "GetVideoEncoderConfigurationOptions")

        resp = make_element("GetVideoEncoderConfigurationOptionsResponse", ONVIF_MEDIA_NS)

        if h264_options:
            resp.append(h264_options)
        if mpeg4_options:
            resp.append(mpeg4_options)
        if jpeg_options:
            resp.append(jpeg_options)

        return self.build_response(request_message_id, action, resp)

    # ============================================================
    # PTZ Service Responses
    # ============================================================

    def build_ptz_configurations_response(
        self,
        request_message_id: str,
        configurations: Optional[list] = None,
    ) -> bytes:
        """Build GetConfigurations response."""
        action = generate_action("ptz", "GetConfigurations")

        if configurations is None:
            from .xsd_types import build_ptz_configuration, build_ptz_node

            node = build_ptz_node(token="ptz-node-0", name="PTZNode")
            config = build_ptz_configuration(
                token="ptz-config-0",
                name="PTZConfig",
                node_token="ptz-node-0",
            )
            configurations = [config]

        resp = make_element("GetConfigurationsResponse", ONVIF_PTZ_NS)
        for config in configurations:
            resp.append(config)

        return self.build_response(request_message_id, action, resp)

    def build_ptz_node_response(
        self,
        request_message_id: str,
        node: Optional[etree._Element] = None,
    ) -> bytes:
        """Build GetNode response."""
        action = generate_action("ptz", "GetNode")

        if node is None:
            from .xsd_types import build_ptz_node

            node = build_ptz_node(token="ptz-node-0", name="PTZNode")

        resp = make_element("GetNodeResponse", ONVIF_PTZ_NS)
        resp.append(node)

        return self.build_response(request_message_id, action, resp)

    def build_ptz_presets_response(
        self,
        request_message_id: str,
        presets: Optional[list] = None,
    ) -> bytes:
        """Build GetPresets response."""
        action = generate_action("ptz", "GetPresets")

        if presets is None:
            from .xsd_types import build_preset

            presets = [
                build_preset(token="preset0", name="HomePosition"),
                build_preset(token="preset1", name="LeftCorner", pan_tilt_x=-0.5, pan_tilt_y=-0.3),
                build_preset(token="preset2", name="RightCorner", pan_tilt_x=0.5, pan_tilt_y=-0.3),
            ]

        resp = make_element("GetPresetsResponse", ONVIF_PTZ_NS)
        for preset in presets:
            resp.append(preset)

        return self.build_response(request_message_id, action, resp)

    def build_ptz_status_response(
        self,
        request_message_id: str,
    ) -> bytes:
        """Build PTZ status response."""
        action = generate_action("ptz", "GetStatus")

        from .xsd_types import build_ptz_status

        status = build_ptz_status()

        resp = make_element("GetStatusResponse", ONVIF_PTZ_NS)
        resp.append(status)

        return self.build_response(request_message_id, action, resp)

    def build_ptz_move_response(
        self,
        request_message_id: str,
        operation: str = "AbsoluteMove",
    ) -> bytes:
        """Build PTZ move operation response."""
        action = generate_action("ptz", operation)

        resp = make_element(f"{operation}Response", ONVIF_PTZ_NS)

        return self.build_response(request_message_id, action, resp)

    def build_preset_response(
        self,
        request_message_id: str,
        operation: str = "SetPreset",
    ) -> bytes:
        """Build preset operation response."""
        action = generate_action("ptz", operation)

        resp = make_element(f"{operation}Response", ONVIF_PTZ_NS)

        return self.build_response(request_message_id, action, resp)

    # ============================================================
    # Event Service Responses
    # ============================================================

    def build_subscribe_response(
        self,
        request_message_id: str,
        subscription_id: str,
        notification_endpoint: str,
    ) -> bytes:
        """Build Subscribe response."""
        action = generate_action("events", "Subscribe")

        resp = make_element("SubscribeResponse", ONVIF_EVENTS_NS)
        subscription = make_element("SubscriptionReference", ONVIF_NS)
        addr = make_element("Address", ONVIF_NS, notification_endpoint)
        addr.set("MessageExchangePattern", "http://www.w3.org/2005/08/addressing/reply")
        subscription.append(addr)
        resp.append(subscription)

        return self.build_response(request_message_id, action, resp)

    def build_pull_messages_response(
        self,
        request_message_id: str,
        messages: Optional[list] = None,
    ) -> bytes:
        """Build PullMessages response."""
        action = generate_action("events", "PullMessages")

        resp = make_element("PullMessagesResponse", ONVIF_EVENTS_NS)

        if messages:
            for msg in messages:
                resp.append(msg)

        return self.build_response(request_message_id, action, resp)

    # ============================================================
    # Imaging Service Responses
    # ============================================================

    def build_imaging_options_response(
        self,
        request_message_id: str,
    ) -> bytes:
        """Build GetImagingOptions response."""
        action = generate_action("imaging", "GetImagingOptions")

        resp = make_element("GetImagingOptionsResponse", ONVIF_IMAGING_NS)

        return self.build_response(request_message_id, action, resp)

    def build_imaging_settings_response(
        self,
        request_message_id: str,
    ) -> bytes:
        """Build GetImagingSettings response."""
        action = generate_action("imaging", "GetImagingSettings")

        resp = make_element("GetImagingSettingsResponse", ONVIF_IMAGING_NS)

        return self.build_response(request_message_id, action, resp)

    def build_set_imaging_settings_response(
        self,
        request_message_id: str,
    ) -> bytes:
        """Build SetImagingSettings response."""
        action = generate_action("imaging", "SetImagingSettings")

        resp = make_element("SetImagingSettingsResponse", ONVIF_IMAGING_NS)

        return self.build_response(request_message_id, action, resp)
