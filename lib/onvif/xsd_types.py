"""
ONVIF XML Schema Type Definitions

Provides factory methods for constructing ONVIF XML elements used in
Device, Media, PTZ, Events, and Imaging service operations.
"""

from typing import Optional, List, Dict, Any
from lxml import etree
from .ws_addressing import generate_message_id


# ONVIF Namespace URIs
ONVIF_NS = "http://www.onvif.org/ver10/schema"
ONVIF_DEVICE_NS = "http://www.onvif.org/ver10/device/wsdl"
ONVIF_MEDIA_NS = "http://www.onvif.org/ver10/media/wsdl"
ONVIF_PTZ_NS = "http://www.onvif.org/ver10/ptz/wsdl"
ONVIF_EVENTS_NS = "http://www.onvif.org/ver10/events/wsdl"
ONVIF_IMAGING_NS = "http://www.onvif.org/ver20/imaging/wsdl"
ONVIF_RECD_NS = "http://www.onvif.org/ver10/recording/wsdl"
ONVIF_SEARCH_NS = "http://www.onvif.org/ver10/search/wsdl"
ONVIF_RECP_NS = "http://www.onvif.org/ver10/receiver/wsdl"

# XSD namespace for standard types
XSD_NS = "http://www.w3.org/2001/XMLSchema"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

# Common ONVIF namespace prefix map
ONVIF_NAMESPACES = {
    "tt": ONVIF_NS,
    "tds": ONVIF_DEVICE_NS,
    "tmd": "http://www.onvif.org/ver10/deviceio/wsdl",
    "tmm": "http://www.onvif.org/ver20/media/wsdl",
    "tptz": "http://www.onvif.org/ver20/ptz/wsdl",
    "tev": "http://www.onvif.org/ver10/events/wsdl",
    "timg": "http://www.onvif.org/ver20/imaging/wsdl",
    "tst": "http://www.onvif.org/ver10/search/wsdl",
    "trt": "http://www.onvif.org/ver10/media/wsdl",
    "trc": "http://www.onvif.org/ver10/recording/wsdl",
    "ter": "http://www.onvif.org/ver10/error",
}


def make_element(
    name: str,
    namespace: str,
    text: Optional[str] = None,
    attrib: Optional[Dict[str, str]] = None,
) -> etree._Element:
    """Create an ONVIF namespaced element."""
    elem = etree.Element(f"{{{namespace}}}{name}")
    if text is not None:
        elem.text = text
    if attrib:
        elem.attrib.update(attrib)
    return elem


def make_complex_element(
    name: str, namespace: str, children: List[etree._Element]
) -> etree._Element:
    """Create an ONVIF element with child elements."""
    elem = etree.Element(f"{{{namespace}}}{name}")
    for child in children:
        elem.append(child)
    return elem


# ============================================================
# Device Service Types (tds)
# ============================================================


def build_get_device_info() -> etree._Element:
    """Build GetDeviceInfo request element."""
    return make_element("GetDeviceInfo", ONVIF_DEVICE_NS)


def build_device_info(
    manufacturer: str = "ONVIF Middleware",
    model: str = "Middleware Camera Emulator",
    firmware_version: str = "1.0.0",
    serial_number: str = "000000000000",
    hardware_id: str = "ONVIF-MW-001",
) -> etree._Element:
    """Build DeviceInfo response element."""
    children = [
        make_element("Manufacturer", ONVIF_NS, manufacturer),
        make_element("Model", ONVIF_NS, model),
        make_element("FirmwareVersion", ONVIF_NS, firmware_version),
        make_element("SerialNumber", ONVIF_NS, serial_number),
        make_element("HardwareId", ONVIF_NS, hardware_id),
    ]
    return make_complex_element("DeviceInfo", ONVIF_NS, children)


def build_get_capabilities() -> etree._Element:
    """Build GetCapabilities request element."""
    return make_element("GetCapabilities", ONVIF_DEVICE_NS)


def build_capabilities(
    capabilities_dict: Optional[Dict[str, str]] = None,
) -> etree._Element:
    """
    Build Capabilities response element.

    Args:
        capabilities_dict: Mapping of capability category to endpoint URL
    """
    if capabilities_dict is None:
        capabilities_dict = {}

    children = []
    for category, url in capabilities_dict.items():
        cap_elem = make_element("Capability", ONVIF_NS)
        addr = make_element("Address", ONVIF_NS, url)
        addr.set("UseAddress", "true")
        cap_elem.append(addr)
        children.append(cap_elem)

    return make_complex_element("Capabilities", ONVIF_NS, children)


def build_get_network_interfaces() -> etree._Element:
    """Build GetNetworkInterfaces request element."""
    return make_element("GetNetworkInterfaces", ONVIF_DEVICE_NS)


def build_network_interface(
    token: str = "NetIf0",
    enabled: bool = True,
    ipv4_address: str = "192.168.1.100",
    ipv4_subnet_prefix: int = 24,
    ipv6_addresses: Optional[List[str]] = None,
    gateway: Optional[str] = None,
    dhcp_enabled: bool = False,
) -> etree._Element:
    """Build NetworkInterface element."""
    children = [
        make_element("Token", ONVIF_NS, token),
        make_element("Enabled", ONVIF_NS, str(enabled).lower()),
    ]

    # IPv4 configuration
    ipv4 = make_element("IPv4", ONVIF_NS)
    addr = make_element("Manual", ONVIF_NS)
    addr.append(make_element("Address", ONVIF_NS, ipv4_address))
    addr.append(make_element("PrefixLength", ONVIF_NS, str(ipv4_subnet_prefix)))
    ipv4.append(addr)
    children.append(ipv4)

    # IPv6 configuration (optional)
    if ipv6_addresses:
        ipv6 = make_element("IPv6", ONVIF_NS)
        for addr in ipv6_addresses:
            ipv6.append(make_element("Manual", ONVIF_NS, addr))
        children.append(ipv6)

    # Gateway (optional)
    if gateway:
        gateway_elem = make_element("Gateway", ONVIF_NS)
        gateway_elem.append(make_element("Address", ONVIF_NS, gateway))
        children.append(gateway_elem)

    # DHCP
    dhcp = make_element("DHCP", ONVIF_NS)
    dhcp.append(make_element("Enabled", ONVIF_NS, str(dhcp_enabled).lower()))
    children.append(dhcp)

    return make_complex_element("NetworkInterface", ONVIF_NS, children)


def build_get_network_protocols() -> etree._Element:
    """Build GetNetworkProtocols request element."""
    return make_element("GetNetworkProtocols", ONVIF_DEVICE_NS)


def build_network_protocol(
    name: str = "HTTP",
    port: int = 80,
) -> etree._Element:
    """Build NetworkProtocol element."""
    children = [
        make_element("Name", ONVIF_NS, name),
        make_element("Port", ONVIF_NS, str(port)),
    ]
    return make_complex_element("NetworkProtocol", ONVIF_NS, children)


def build_set_system_date_and_time(
    use_dhcp: bool = False,
    manual: Optional[str] = None,
) -> etree._Element:
    """Build SetSystemDateAndTime request element."""
    type_elem = make_element("Type", ONVIF_DEVICE_NS, "DHCP" if use_dhcp else "Manual")
    elem = make_element("SetSystemDateAndTime", ONVIF_DEVICE_NS, children=[type_elem])

    if manual:
        date_time = make_element("UTCDateTime", ONVIF_NS)
        date_time.append(make_element("Time", ONVIF_NS, manual))
        elem.append(date_time)

    return elem


def build_get_wsdl_url() -> etree._Element:
    """Build GetWsdl request element."""
    return make_element("GetWsdl", ONVIF_DEVICE_NS)


# ============================================================
# Media Service Types (trt)
# ============================================================


def build_get_profiles() -> etree._Element:
    """Build GetProfiles request element."""
    return make_element("GetProfiles", ONVIF_MEDIA_NS)


def build_get_stream_uri() -> etree._Element:
    """Build GetStreamUri request element."""
    return make_element("GetStreamUri", ONVIF_MEDIA_NS)


def build_stream_uri_request(
    profile_token: str = "profile0",
    stream_setup: str = "RTP-Unicast",
    media_profile_token: Optional[str] = None,
) -> etree._Element:
    """
    Build GetStreamUri request with StreamSetup element.

    Args:
        profile_token: Token of the media profile
        stream_setup: Stream setup type (RTP-Unicast or RTP-Multicast)
        media_profile_token: Optional media profile token
    """
    stream_setup_elem = make_element("StreamSetup", ONVIF_NS)
    protocol = make_element("Stream", ONVIF_NS, stream_setup)
    transport = make_element("Transport", ONVIF_NS)
    protocol_elem = make_element("Protocol", ONVIF_NS, "RTSP")
    transport.append(protocol_elem)
    stream_setup_elem.append(protocol)
    stream_setup_elem.append(transport)

    req = make_element("GetStreamUri", ONVIF_MEDIA_NS)
    req.append(stream_setup_elem)

    if media_profile_token:
        req.append(make_element("ProfileToken", ONVIF_NS, media_profile_token))
    else:
        req.append(make_element("ProfileToken", ONVIF_NS, profile_token))

    return req


def build_stream_uri_response(stream_uri: str) -> etree._Element:
    """Build GetStreamUri response with MediaUri element."""
    media_uri = make_element("MediaUri", ONVIF_NS)
    uri_elem = make_element("Uri", ONVIF_NS, stream_uri)
    media_uri.append(uri_elem)
    # Set timeout hint
    timeout = make_element("InvalidAfterConnect", ONVIF_NS, "true")
    media_uri.append(timeout)
    valid = make_element("ValidUntilOrReboot", ONVIF_NS, "true")
    media_uri.append(valid)
    return media_uri


def build_get_video_sources() -> etree._Element:
    """Build GetVideoSources request element."""
    return make_element("GetVideoSources", ONVIF_MEDIA_NS)


def build_video_source(
    token: str = "video-source-0",
    width: int = 1920,
    height: int = 1080,
    framerate: int = 30,
) -> etree._Element:
    """Build VideoSource element."""
    children = [
        make_element("Token", ONVIF_NS, token),
        make_element("Framerate", ONVIF_NS, str(framerate)),
        make_element("Resolution", ONVIF_NS),
    ]
    resolution = children[2]
    resolution.append(make_element("Width", ONVIF_NS, str(width)))
    resolution.append(make_element("Height", ONVIF_NS, str(height)))
    return make_complex_element("VideoSource", ONVIF_NS, children)


def build_get_video_encoder_configuration_options() -> etree._Element:
    """Build GetVideoEncoderConfigurationOptions request element."""
    return make_element("GetVideoEncoderConfigurationOptions", ONVIF_MEDIA_NS)


def build_h264_configuration_options(
    resolutions: Optional[List[tuple]] = None,
    frame_rate_range: tuple = (1, 30),
    gov_length_range: tuple = (1, 50),
    h264_profiles: Optional[List[str]] = None,
) -> etree._Element:
    """Build H264ConfigurationOptions element."""
    if resolutions is None:
        resolutions = [(1920, 1080), (1280, 720), (640, 480)]
    if h264_profiles is None:
        h264_profiles = ["High", "Main", "Baseline"]

    children = []

    # Supported resolutions
    for w, h in resolutions:
        res = make_element("FrameHeight", ONVIF_NS)
        res.append(make_element("MaxWidth", ONVIF_NS, str(w)))
        res.append(make_element("MaxHeight", ONVIF_NS, str(h)))
        children.append(res)

    # Frame rate range
    range_elem = make_element("FrameRateRange", ONVIF_NS)
    range_elem.append(make_element("MinFramerate", ONVIF_NS, str(frame_rate_range[0])))
    range_elem.append(make_element("MaxFramerate", ONVIF_NS, str(frame_rate_range[1])))
    children.append(range_elem)

    # GOP length range
    gov = make_element("GovLengthRange", ONVIF_NS)
    gov.append(make_element("MinGovLength", ONVIF_NS, str(gov_length_range[0])))
    gov.append(make_element("MaxGovLength", ONVIF_NS, str(gov_length_range[1])))
    children.append(gov)

    # Supported H.264 profiles
    profiles = make_element("H264Profiles", ONVIF_NS)
    for profile in h264_profiles:
        profiles.append(make_element("H264Profile", ONVIF_NS, profile))
    children.append(profiles)

    return make_complex_element("H264ConfigurationOptions", ONVIF_NS, children)


def build_get_profiles_response(profiles: List[etree._Element]) -> etree._Element:
    """Build GetProfiles response element."""
    resp = make_element("GetProfilesResponse", ONVIF_MEDIA_NS)
    for profile in profiles:
        resp.append(profile)
    return resp


def build_media_profile(
    token: str = "profile0",
    name: str = "MainProfile",
    video_source_token: str = "video-source-0",
    video_encoder_token: str = "encoder0",
    video_analytics_token: Optional[str] = None,
    ptz_token: Optional[str] = None,
) -> etree._Element:
    """Build a MediaProfile element."""
    children = [
        make_element("Token", ONVIF_NS, token),
        make_element("Name", ONVIF_NS, name),
    ]

    # VideoSourceConfiguration
    vs_config = make_element("VideoSourceConfiguration", ONVIF_NS)
    vs_config.append(make_element("Token", ONVIF_NS, f"{token}_vs"))
    vs_config.append(make_element("Name", ONVIF_NS, f"{name} Source"))
    vs_config.append(make_element("UseCount", ONVIF_NS, "0"))

    source = make_element("Source", ONVIF_NS)
    source.append(make_element("Token", ONVIF_NS, video_source_token))
    vs_config.append(source)
    children.append(vs_config)

    # VideoEncoderConfiguration
    ve_config = make_element("VideoEncoderConfiguration", ONVIF_NS)
    ve_config.append(make_element("Token", ONVIF_NS, video_encoder_token))
    ve_config.append(make_element("Name", ONVIF_NS, f"{name} Encoder"))
    ve_config.append(make_element("UseCount", ONVIF_NS, "0"))
    ve_config.append(make_element("Encoding", ONVIF_NS, "H264"))
    ve_config.append(make_element("Resolution", ONVIF_NS))
    ve_config.find(".//Resolution")  # already appended
    children.append(ve_config)

    # PTZConfiguration (optional)
    if ptz_token:
        ptz_config = make_element("PTZConfiguration", ONVIF_NS)
        ptz_config.append(make_element("Token", ONVIF_NS, f"{token}_ptz"))
        ptz_config.append(make_element("Name", ONVIF_NS, f"{name} PTZ"))
        ptz_config.append(make_element("UseCount", ONVIF_NS, "0"))
        ptz_config.append(make_element("NodeToken", ONVIF_NS, ptz_token))
        children.append(ptz_config)

    return make_complex_element("Profile", ONVIF_NS, children)


# ============================================================
# PTZ Service Types (tptz)
# ============================================================


def build_get_configurations() -> etree._Element:
    """Build GetConfigurations request element."""
    return make_element("GetConfigurations", ONVIF_PTZ_NS)


def build_ptz_configuration(
    token: str = "ptz-config-0",
    name: str = "PTZConfig",
    node_token: str = "ptz-node-0",
    default_preset_token: Optional[str] = None,
) -> etree._Element:
    """Build PTZConfiguration element."""
    children = [
        make_element("Token", ONVIF_NS, token),
        make_element("Name", ONVIF_NS, name),
        make_element("UseCount", ONVIF_NS, "0"),
        make_element("NodeToken", ONVIF_NS, node_token),
    ]

    if default_preset_token:
        preset = make_element("DefaultAbsolutePantTiltPositionSpace", ONVIF_NS)
        preset.append(make_element("Token", ONVIF_NS, default_preset_token))
        children.append(preset)

    return make_complex_element("PTZConfiguration", ONVIF_NS, children)


def build_ptz_node(
    token: str = "ptz-node-0",
    name: str = "PTZNode",
    supported_speeds: bool = True,
) -> etree._Element:
    """Build PTZNode element."""
    children = [
        make_element("Token", ONVIF_NS, token),
        make_element("Name", ONVIF_NS, name),
        make_element("UseCount", ONVIF_NS, "0"),
        make_element("SupportedPTZSpaces", ONVIF_NS),
    ]

    spaces = children[3]
    # Add supported coordinate spaces
    for space_type in [
        "AbsolutePanTiltPositionSpace",
        "AbsoluteZoomPositionSpace",
        "RelativePanTiltTranslationSpace",
        "RelativeZoomTranslationSpace",
        "ContinuousPanTiltVelocitySpace",
        "ContinuousZoomVelocitySpace",
    ]:
        space = make_element(space_type, ONVIF_NS)
        x_range = make_element("XRange", ONVIF_NS)
        y_range = make_element("YRange", ONVIF_NS)
        x_range.append(make_element("Min", ONVIF_NS, "-1.0"))
        x_range.append(make_element("Max", ONVIF_NS, "1.0"))
        y_range.append(make_element("Min", ONVIF_NS, "-1.0"))
        y_range.append(make_element("Max", ONVIF_NS, "1.0"))
        space.append(x_range)
        space.append(y_range)
        spaces.append(space)

    if supported_speeds:
        speed_elem = make_element("SupportedSpeeds", ONVIF_NS)
        for space_type in [
            "AbsolutePanTiltPositionSpace",
            "AbsoluteZoomPositionSpace",
            "RelativePanTiltTranslationSpace",
            "RelativeZoomTranslationSpace",
            "ContinuousPanTiltVelocitySpace",
            "ContinuousZoomVelocitySpace",
        ]:
            speed = make_element(space_type, ONVIF_NS)
            speed.append(make_element("XRange", ONVIF_NS))
            xr = speed.find(".//XRange")
            xr.append(make_element("Min", ONVIF_NS, "0.0"))
            xr.append(make_element("Max", ONVIF_NS, "1.0"))
            speed_elem.append(speed)
        children.append(speed_elem)

    return make_complex_element("PTZNode", ONVIF_NS, children)


def build_get_preset() -> etree._Element:
    """Build GetPreset request element."""
    return make_element("GetPreset", ONVIF_PTZ_NS)


def build_goto_preset_request(preset_token: str) -> etree._Element:
    """Build GotoPreset request element."""
    req = make_element("GotoPreset", ONVIF_PTZ_NS)
    req.append(make_element("ProfileToken", ONVIF_NS, "profile0"))
    req.append(make_element("PresetToken", ONVIF_NS, preset_token))
    return req


def build_set_preset_request(preset_token: str) -> etree._Element:
    """Build SetPreset request element."""
    req = make_element("SetPreset", ONVIF_PTZ_NS)
    req.append(make_element("ProfileToken", ONVIF_NS, "profile0"))
    req.append(make_element("PresetToken", ONVIF_NS, preset_token))
    return req


def build_remove_preset_request(preset_token: str) -> etree._Element:
    """Build RemovePreset request element."""
    req = make_element("RemovePreset", ONVIF_PTZ_NS)
    req.append(make_element("ProfileToken", ONVIF_NS, "profile0"))
    req.append(make_element("PresetToken", ONVIF_NS, preset_token))
    return req


def build_get_presets() -> etree._Element:
    """Build GetPresets request element."""
    return make_element("GetPresets", ONVIF_PTZ_NS)


def build_preset(
    token: str = "preset0",
    name: str = "HomePosition",
    pan_tilt_x: float = 0.0,
    pan_tilt_y: float = 0.0,
    zoom: float = 0.0,
) -> etree._Element:
    """Build PTZPreset element."""
    children = [
        make_element("Token", ONVIF_NS, token),
        make_element("Name", ONVIF_NS, name),
    ]

    pt = make_element("PTZ", ONVIF_NS)
    pt.append(make_element("PanTilt", ONVIF_NS))
    pt_elem = pt.find(".//PanTilt") or pt
    pt_elem.append(make_element("x", ONVIF_NS, str(pan_tilt_x)))
    pt_elem.append(make_element("y", ONVIF_NS, str(pan_tilt_y)))
    pt_elem.set("space", "http://www.onvif.org/ver10/ptz/location/Vector")
    children.append(pt)

    z = make_element("Zoom", ONVIF_NS)
    z.append(make_element("zoom", ONVIF_NS, str(zoom)))
    z.set("space", "http://www.onvif.org/ver10/ptz/location/Vector")
    children.append(z)

    return make_complex_element("PTZPreset", ONVIF_NS, children)


def build_ptz_status() -> etree._Element:
    """Build PTZStatus element."""
    status = make_element("PTZStatus", ONVIF_NS)
    status.append(make_element("Position", ONVIF_NS))
    position = status.find(".//Position") or status
    position.append(make_element("PanTilt", ONVIF_NS))
    pt = position.find(".//PanTilt") or position
    pt.append(make_element("x", ONVIF_NS, "0.0"))
    pt.append(make_element("y", ONVIF_NS, "0.0"))
    pt.set("space", "http://www.onvif.org/ver10/ptz/location/Vector")
    position.append(make_element("Zoom", ONVIF_NS))
    z = position.find(".//Zoom") or position
    z.append(make_element("zoom", ONVIF_NS, "0.0"))
    z.set("space", "http://www.onvif.org/ver10/ptz/location/Vector")
    status.append(make_element("MoveStatus", ONVIF_NS))
    status.find(".//MoveStatus").append(make_element("PanTilt", ONVIF_NS, "IDLE"))
    status.find(".//MoveStatus").append(make_element("Zoom", ONVIF_NS, "IDLE"))
    status.append(make_element("Error", ONVIF_NS, ""))
    return status


# ============================================================
# Event Service Types (tev)
# ============================================================


def build_subscribe_request() -> etree._Element:
    """Build Subscribe request element."""
    req = make_element("Subscribe", ONVIF_EVENTS_NS)
    receiver = make_element("Consumer", ONVIF_EVENTS_NS)
    address = make_element("Address", ONVIF_EVENTS_NS, "http://localhost/evtpull")
    receiver.append(address)
    req.append(receiver)
    return req


def build_pull_messages_request() -> etree._Element:
    """Build PullMessages request element."""
    req = make_element("PullMessages", ONVIF_EVENTS_NS)
    req.append(make_element("Timeout", ONVIF_EVENTS_NS, "PT10S"))
    req.append(make_element("MessageLimit", ONVIF_EVENTS_NS, "10"))
    return req


def build_notification_message(
    topic_namespace: str = "http://www.onvif.org/ver10/topic/wsdl/VideoSource",
    topic_name: str = "MotionDetection",
    message: Optional[str] = None,
) -> etree._Element:
    """Build a NotificationMessage element."""
    msg = make_element("NotificationMessage", ONVIF_EVENTS_NS)
    topic = make_element("Topic", ONVIF_EVENTS_NS, dtd="{_}true")
    topic.text = f"{topic_namespace}/{topic_name}/{'True' if message else 'False'}"
    msg.append(topic)
    if message:
        data = make_element("Data", ONVIF_EVENTS_NS)
        data.append(make_element("SimpleItem", ONVIF_EVENTS_NS, Name="Value", Value=message))
        msg.append(data)
    return msg


# ============================================================
# Imaging Service Types (timg)
# ============================================================


def build_get_imaging_options() -> etree._Element:
    """Build GetImagingOptions request element."""
    return make_element("GetImagingOptions", ONVIF_IMAGING_NS)


def build_set_imaging_settings(
    token: str = "img-config-0",
    focus_mode: str = "Auto",
    iris_mode: str = "Auto",
    white_balance_mode: str = "Auto",
) -> etree._Element:
    """Build SetImagingSettings request element."""
    req = make_element("SetImagingSettings", ONVIF_IMAGING_NS)
    req.append(make_element("VideoSourceToken", ONVIF_NS, token))

    settings = make_element("ImagingSettings", ONVIF_IMAGING_NS)
    settings.append(make_element("Focus", ONVIF_IMAGING_NS))
    focus = settings.find(".//Focus") or settings
    focus.append(make_element("Mode", ONVIF_IMAGING_NS, focus_mode))
    settings.append(make_element("Iris", ONVIF_IMAGING_NS))
    iris = settings.find(".//Iris") or settings
    iris.append(make_element("Mode", ONVIF_IMAGING_NS, iris_mode))
    settings.append(make_element("WhiteBalance", ONVIF_IMAGING_NS))
    wb = settings.find(".//WhiteBalance") or settings
    wb.append(make_element("Mode", ONVIF_IMAGING_NS, white_balance_mode))

    req.append(settings)
    return req


# ============================================================
# Utility Functions
# ============================================================


def create_onvif_namespace_map() -> dict:
    """Create a complete ONVIF namespace map for lxml serialization."""
    return {
        "tt": ONVIF_NS,
        "tds": ONVIF_DEVICE_NS,
        "trt": ONVIF_MEDIA_NS,
        "tptz": ONVIF_PTZ_NS,
        "tev": ONVIF_EVENTS_NS,
        "timg": ONVIF_IMAGING_NS,
        "tmd": "http://www.onvif.org/ver10/deviceio/wsdl",
        "trc": ONVIF_RECD_NS,
        "tst": ONVIF_SEARCH_NS,
        "ter": "http://www.onvif.org/ver10/error",
    }


def serialize_with_onvif_ns(element: etree._Element) -> bytes:
    """Serialize an element with all ONVIF namespaces declared."""
    return etree.tostring(
        element,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    )
