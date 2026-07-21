"""
WS-Addressing header handling for ONVIF SOAP messages.

ONVIF relies on WS-Addressing for message identification, correlation,
and routing. Every SOAP request from the NVR includes WS-Addressing headers
that must be echoed back in responses.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from lxml import etree


# ONVIF namespace constants
WS_ADDR_NS = "http://www.w3.org/2005/08/addressing"
SOAP_ENVELOPE_NS = "http://schemas.xmlsoap.org/soap/envelope/"


def generate_message_id() -> str:
    """Generate a unique WS-Addressing MessageID UUID."""
    return f"urn:uuid:{uuid.uuid4()}"


def generate_action(service: str, operation: str) -> str:
    """
    Generate a WS-Addressing Action header value.

    Args:
        service: ONVIF service name (e.g., 'device', 'media', 'ptz')
        operation: Operation name (e.g., 'GetDeviceInfo', 'GetProfiles')

    Returns:
        Formatted Action string (e.g., 'http://www.onvif.org/ver10/device/wsdl/GetDeviceInfo')
    """
    return f"http://www.onvif.org/ver{_service_version(service)}/{service}/wsdl/{operation}"


def _service_version(service: str) -> str:
    """Return the ONVIF version string for a given service."""
    versions = {
        "device": "10",
        "media": "10",
        "ptz": "10",
        "events": "10",
        "imaging": "20",
        "analytics": "10",
        "deviceio": "10",
        "replay": "20",
        "receiver": "10",
        "recording": "10",
        "search": "10",
        "thermal": "10",
        "actionengine": "10",
    }
    return versions.get(service, "10")


def build_ws_addressing_header(
    message_id: Optional[str] = None,
    action: Optional[str] = None,
    reply_to: Optional[str] = None,
    relates_to: Optional[str] = None,
    to: Optional[str] = None,
) -> etree._Element:
    """
    Build a WS-Addressing header element.

    Args:
        message_id: Unique message identifier
        action: The operation being performed
        reply_to: Endpoint reference for replies
        relates_to: MessageID this response relates to
        to: Target endpoint URL

    Returns:
        lxml Element representing the WS-Addressing header
    """
    nsmap = {"wsa": WS_ADDR_NS}

    header = etree.Element(
        f"{{{WS_ADDR_NS}}}Header", nsmap=nsmap
    )

    if message_id:
        msg_id = etree.SubElement(header, f"{{{WS_ADDR_NS}}}MessageID")
        msg_id.text = message_id

    if action:
        act = etree.SubElement(header, f"{{{WS_ADDR_NS}}}Action")
        act.text = action

    if reply_to:
        reply_elem = etree.SubElement(header, f"{{{WS_ADDR_NS}}}ReplyTo")
        address = etree.SubElement(reply_elem, f"{{{WS_ADDR_NS}}}Address")
        address.text = reply_to

    if relates_to:
        rel = etree.SubElement(header, f"{{{WS_ADDR_NS}}}RelatesTo")
        rel.text = relates_to

    if to:
        to_elem = etree.SubElement(header, f"{{{WS_ADDR_NS}}}To")
        to_elem.text = to

    return header


def parse_ws_addressing_header(soap_xml: etree._Element) -> dict:
    """
    Extract WS-Addressing headers from an incoming SOAP message.

    Args:
        soap_xml: Parsed SOAP envelope element

    Returns:
        Dictionary with WS-Addressing header values
    """
    result = {
        "message_id": None,
        "action": None,
        "reply_to": None,
        "relates_to": None,
        "to": None,
    }

    # Find the SOAP header
    soap_ns = {"soap": SOAP_ENVELOPE_NS, "wsa": WS_ADDR_NS}
    header_elem = soap_xml.find("soap:Header", soap_ns)

    if header_elem is None:
        return result

    # Extract each WS-Addressing field
    for field in ["MessageID", "Action", "ReplyTo", "RelatesTo", "To"]:
        elem = header_elem.find(f"{{{WS_ADDR_NS}}}{field}")
        if elem is not None and elem.text:
            if field == "ReplyTo":
                addr_elem = elem.find(f"{{{WS_ADDR_NS}}}Address")
                result["reply_to"] = addr_elem.text if addr_elem is not None else None
            else:
                result[field.lower()] = elem.text

    return result


def extract_soap_body(soap_xml: etree._Element) -> Optional[etree._Element]:
    """
    Extract the SOAP Body element from a parsed SOAP envelope.

    Args:
        soap_xml: Parsed SOAP envelope element

    Returns:
        The SOAP Body element, or None if not found
    """
    ns = {"soap": SOAP_ENVELOPE_NS}
    body = soap_xml.find("soap:Body", ns)
    return body


def build_soap_envelope(
    body_element: etree._Element,
    ws_addressing_header: Optional[etree._Element] = None,
    fault: Optional[dict] = None,
) -> bytes:
    """
    Build a complete SOAP envelope with optional WS-Addressing headers.

    Args:
        body_element: The element to place in the SOAP Body
        ws_addressing_header: Optional WS-Addressing header element
        fault: Optional fault information dict with 'code', 'string', 'detail'

    Returns:
        Serialized SOAP envelope as bytes
    """
    nsmap = {
        "soap": SOAP_ENVELOPE_NS,
        "wsa": WS_ADDR_NS,
    }

    envelope = etree.Element(
        f"{{{SOAP_ENVELOPE_NS}}}Envelope", nsmap=nsmap
    )

    # Add WS-Addressing header if provided
    if ws_addressing_header is not None:
        envelope.insert(0, ws_addressing_header)

    # Build body
    body = etree.SubElement(envelope, f"{{{SOAP_ENVELOPE_NS}}}Body")

    if fault:
        fault_elem = etree.SubElement(body, f"{{{SOAP_ENVELOPE_NS}}}Fault")
        _build_fault(fault_elem, fault)
    else:
        body.append(body_element)

    return etree.tostring(
        envelope,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    )


def _build_fault(fault_elem: etree._Element, fault_info: dict) -> None:
    """Build a SOAP Fault element from a dictionary."""
    code_elem = etree.SubElement(fault_elem, "faultcode")
    code_elem.text = fault_info.get("code", "soap:Server")

    string_elem = etree.SubElement(fault_elem, "faultstring")
    string_elem.text = fault_info.get("string", "Server error")

    # Optional detail
    detail_text = fault_info.get("detail", "")
    if detail_text:
        detail_elem = etree.SubElement(fault_elem, "detail")
        detail_elem.text = detail_text
