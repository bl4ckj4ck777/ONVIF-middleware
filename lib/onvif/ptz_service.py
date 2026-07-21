"""
ONVIF PTZ Service Handler

Handles all ONVIF PTZ (Pan-Tilt-Zoom) service operations.
Manages PTZ configurations, presets, and movement commands.
"""

import logging
from typing import Optional, Dict, Any, List
from lxml import etree

from .parser import ONVIFRequest
from .responder import ONVIFResponder
from .xsd_types import (
    ONVIF_PTZ_NS,
    ONVIF_NS,
    make_element,
    make_complex_element,
)

logger = logging.getLogger(__name__)


class PTZServiceHandler:
    """
    Handles ONVIF PTZ service operations.

    Supported operations:
    - GetConfigurations
    - GetConfigurationOptions
    - GetNode
    - GetNodes
    - GetPresets
    - GetPreset
    - SetPreset
    - RemovePreset
    - GotoPreset
    - GotoPresetStyle
    - GetDynamicPresets
    - AbsoluteMove
    - RelativeMove
    - ContinuousMove
    - Stop
    - SendAuxiliaryCommand
    - GetStatus
    """

    def __init__(self, responder: ONVIFResponder, camera_config: Optional[Dict[str, Any]] = None):
        self.responder = responder
        self.camera_config = camera_config or {}
        self._presets: Dict[str, Dict[str, Any]] = {}
        self._ptz_position = {"pan": 0.0, "tilt": 0.0, "zoom": 0.0}
        self._is_moving = False
        self._initialize_presets()

    def _initialize_presets(self) -> None:
        """Initialize default PTZ presets."""
        config = self.camera_config

        self._presets = {
            "preset0": {
                "token": "preset0",
                "name": config.get("preset_home_name", "HomePosition"),
                "pan_tilt_x": 0.0,
                "pan_tilt_y": 0.0,
                "zoom": 0.0,
            },
        }

        # Add any configured presets
        configured_presets = config.get("presets", [])
        for i, preset_config in enumerate(configured_presets):
            token = preset_config.get("token", f"preset{i+1}")
            self._presets[token] = {
                "token": token,
                "name": preset_config.get("name", f"Preset {i+1}"),
                "pan_tilt_x": preset_config.get("pan_tilt_x", 0.0),
                "pan_tilt_y": preset_config.get("pan_tilt_y", 0.0),
                "zoom": preset_config.get("zoom", 0.0),
            }

    def handle(self, request: ONVIFRequest) -> bytes:
        """
        Route and handle a PTZ service request.

        Args:
            request: Parsed ONVIF request

        Returns:
            SOAP response bytes
        """
        operation = request.operation

        handlers = {
            "GetConfigurations": self._handle_get_configurations,
            "GetConfigurationOptions": self._handle_get_configuration_options,
            "GetNode": self._handle_get_node,
            "GetNodes": self._handle_get_nodes,
            "GetPresets": self._handle_get_presets,
            "GetPreset": self._handle_get_preset,
            "SetPreset": self._handle_set_preset,
            "RemovePreset": self._handle_remove_preset,
            "GotoPreset": self._handle_goto_preset,
            "GotoPresetStyle": self._handle_goto_preset_style,
            "GetDynamicPresets": self._handle_get_dynamic_presets,
            "AbsoluteMove": self._handle_absolute_move,
            "RelativeMove": self._handle_relative_move,
            "ContinuousMove": self._handle_continuous_move,
            "Stop": self._handle_stop,
            "SendAuxiliaryCommand": self._handle_send_auxiliary_command,
            "GetStatus": self._handle_get_status,
        }

        handler = handlers.get(operation)
        if handler is None:
            logger.warning(f"Unhandled PTZ operation: {operation}")
            return self.responder.build_error_response(
                request_message_id=request.message_id,
                action=request.action,
                code="tptz:ActionNotSupported",
                message=f"Operation {operation} is not supported",
            )

        try:
            return handler(request)
        except Exception as e:
            logger.error(f"Error handling {operation}: {e}", exc_info=True)
            return self.responder.build_error_response(
                request_message_id=request.message_id,
                action=request.action,
                code="tptz:InternalServerError",
                message=str(e),
            )

    def _handle_get_configurations(self, request: ONVIFRequest) -> bytes:
        """Handle GetConfigurations request."""
        from .xsd_types import build_ptz_configuration, build_ptz_node

        node = build_ptz_node(
            token="ptz-node-0",
            name=self.camera_config.get("ptz_node_name", "PTZNode"),
        )

        config = build_ptz_configuration(
            token="ptz-config-0",
            name=self.camera_config.get("ptz_config_name", "PTZConfig"),
            node_token="ptz-node-0",
            default_preset_token="preset0",
        )

        resp = make_element("GetConfigurationsResponse", ONVIF_PTZ_NS)
        resp.append(config)

        return self.responder.build_response(request.message_id, "http://www.onvif.org/ver10/ptz/wsdl/GetConfigurations", resp)

    def _handle_get_configuration_options(self, request: ONVIFRequest) -> bytes:
        """Handle GetConfigurationOptions request."""
        action = "http://www.onvif.org/ver10/ptz/wsdl/GetConfigurationOptions"

        resp = make_element("GetConfigurationOptionsResponse", ONVIF_PTZ_NS)

        options = make_element("PTZConfigurationOptions", ONVIF_NS)
        options.set("XSI_type", "tptz:PTZConfigurationOptions")

        # Coordinate spaces
        spaces = make_element("AbsolutePTZSpeedSpace", ONVIF_NS)
        range_elem = make_element("Range", ONVIF_NS)
        range_elem.append(make_element("Min", ONVIF_NS, "0.0"))
        range_elem.append(make_element("Max", ONVIF_NS, "1.0"))
        spaces.append(range_elem)
        options.append(spaces)

        resp.append(options)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_get_node(self, request: ONVIFRequest) -> bytes:
        """Handle GetNode request."""
        return self.responder.build_ptz_node_response(
            request_message_id=request.message_id,
        )

    def _handle_get_nodes(self, request: ONVIFRequest) -> bytes:
        """Handle GetNodes request."""
        action = "http://www.onvif.org/ver10/ptz/wsdl/GetNodes"

        from .xsd_types import build_ptz_node

        node = build_ptz_node(token="ptz-node-0", name="PTZNode")

        resp = make_element("GetNodesResponse", ONVIF_PTZ_NS)
        resp.append(node)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_get_presets(self, request: ONVIFRequest) -> bytes:
        """Handle GetPresets request."""
        return self.responder.build_ptz_presets_response(
            request_message_id=request.message_id,
        )

    def _handle_get_preset(self, request: ONVIFRequest) -> bytes:
        """Handle GetPreset request."""
        action = "http://www.onvif.org/ver10/ptz/wsdl/GetPreset"

        preset_token = request.parameters.get("preset_token", "preset0")
        preset = self._presets.get(preset_token)

        if preset is None:
            return self.responder.build_error_response(
                request_message_id=request.message_id,
                action=request.action,
                code="tt:UnknownPreset",
                message=f"Preset {preset_token} does not exist",
            )

        from .xsd_types import build_preset

        preset_elem = build_preset(
            token=preset["token"],
            name=preset["name"],
            pan_tilt_x=preset["pan_tilt_x"],
            pan_tilt_y=preset["pan_tilt_y"],
            zoom=preset["zoom"],
        )

        resp = make_element("GetPresetResponse", ONVIF_PTZ_NS)
        resp.append(preset_elem)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_set_preset(self, request: ONVIFRequest) -> bytes:
        """Handle SetPreset request - save current PTZ position as a preset."""
        action = "http://www.onvif.org/ver10/ptz/wsdl/SetPreset"

        preset_token = request.parameters.get("preset_token", "preset_new")

        # Save current position as preset
        self._presets[preset_token] = {
            "token": preset_token,
            "name": f"Preset_{preset_token}",
            "pan_tilt_x": self._ptz_position["pan"],
            "pan_tilt_y": self._ptz_position["tilt"],
            "zoom": self._ptz_position["zoom"],
        }

        logger.info(f"PTZ preset set: {preset_token} at position {self._ptz_position}")

        return self.responder.build_preset_response(
            request_message_id=request.message_id,
            operation="SetPreset",
        )

    def _handle_remove_preset(self, request: ONVIFRequest) -> bytes:
        """Handle RemovePreset request."""
        action = "http://www.onvif.org/ver10/ptz/wsdl/RemovePreset"

        preset_token = request.parameters.get("preset_token", "preset0")

        if preset_token in self._presets:
            del self._presets[preset_token]
            logger.info(f"PTZ preset removed: {preset_token}")

        return self.responder.build_preset_response(
            request_message_id=request.message_id,
            operation="RemovePreset",
        )

    def _handle_goto_preset(self, request: ONVIFRequest) -> bytes:
        """Handle GotoPreset request - move PTZ to a saved preset position."""
        action = "http://www.onvif.org/ver10/ptz/wsdl/GotoPreset"

        preset_token = request.parameters.get("preset_token", "preset0")
        preset = self._presets.get(preset_token)

        if preset is None:
            return self.responder.build_error_response(
                request_message_id=request.message_id,
                action=request.action,
                code="tt:UnknownPreset",
                message=f"Preset {preset_token} does not exist",
            )

        # Update current position
        self._ptz_position["pan"] = preset["pan_tilt_x"]
        self._ptz_position["tilt"] = preset["pan_tilt_y"]
        self._ptz_position["zoom"] = preset["zoom"]

        logger.info(f"PTZ moved to preset '{preset['name']}' ({preset_token})")

        return self.responder.build_ptz_move_response(
            request_message_id=request.message_id,
            operation="GotoPreset",
        )

    def _handle_goto_preset_style(self, request: ONVIFRequest) -> bytes:
        """Handle GotoPresetStyle request."""
        action = "http://www.onvif.org/ver20/ptz/wsdl/GotoPresetStyle"

        resp = make_element("GotoPresetStyleResponse", ONVIF_PTZ_NS)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_get_dynamic_presets(self, request: ONVIFRequest) -> bytes:
        """Handle GetDynamicPresets request."""
        action = "http://www.onvif.org/ver20/ptz/wsdl/GetDynamicPresets"

        resp = make_element("GetDynamicPresetsResponse", ONVIF_PTZ_NS)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_absolute_move(self, request: ONVIFRequest) -> bytes:
        """Handle AbsoluteMove request - move PTZ to absolute coordinates."""
        action = "http://www.onvif.org/ver10/ptz/wsdl/AbsoluteMove"

        pan_x = request.parameters.get("pan_tilt_x", 0.0)
        pan_y = request.parameters.get("pan_tilt_y", 0.0)
        zoom = request.parameters.get("zoom", 0.0)

        self._ptz_position["pan"] = pan_x
        self._ptz_position["tilt"] = pan_y
        self._ptz_position["zoom"] = zoom

        logger.info(f"PTZ absolute move: pan={pan_x}, tilt={pan_y}, zoom={zoom}")

        return self.responder.build_ptz_move_response(
            request_message_id=request.message_id,
            operation="AbsoluteMove",
        )

    def _handle_relative_move(self, request: ONVIFRequest) -> bytes:
        """Handle RelativeMove request - move PTZ relative to current position."""
        action = "http://www.onvif.org/ver10/ptz/wsdl/RelativeMove"

        pan_x = request.parameters.get("pan_tilt_x", 0.0)
        pan_y = request.parameters.get("pan_tilt_y", 0.0)
        zoom = request.parameters.get("zoom", 0.0)

        self._ptz_position["pan"] += pan_x
        self._ptz_position["tilt"] += pan_y
        self._ptz_position["zoom"] += zoom

        # Clamp values to ONVIF range [-1.0, 1.0] for pan/tilt
        self._ptz_position["pan"] = max(-1.0, min(1.0, self._ptz_position["pan"]))
        self._ptz_position["tilt"] = max(-1.0, min(1.0, self._ptz_position["tilt"]))

        logger.info(f"PTZ relative move: pan_delta={pan_x}, tilt_delta={pan_y}, zoom_delta={zoom}")

        return self.responder.build_ptz_move_response(
            request_message_id=request.message_id,
            operation="RelativeMove",
        )

    def _handle_continuous_move(self, request: ONVIFRequest) -> bytes:
        """Handle ContinuousMove request - start continuous PTZ movement."""
        action = "http://www.onvif.org/ver10/ptz/wsdl/ContinuousMove"

        pan_x = request.parameters.get("pan_tilt_x", 0.0)
        pan_y = request.parameters.get("pan_tilt_y", 0.0)
        zoom = request.parameters.get("zoom", 0.0)

        self._is_moving = True

        logger.info(f"PTZ continuous move started: pan_vel={pan_x}, tilt_vel={pan_y}, zoom_vel={zoom}")

        resp = make_element("ContinuousMoveResponse", ONVIF_PTZ_NS)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_stop(self, request: ONVIFRequest) -> bytes:
        """Handle Stop request - stop PTZ movement."""
        action = "http://www.onvif.org/ver10/ptz/wsdl/Stop"

        self._is_moving = False

        logger.info("PTZ movement stopped")

        resp = make_element("StopResponse", ONVIF_PTZ_NS)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_send_auxiliary_command(self, request: ONVIFRequest) -> bytes:
        """Handle SendAuxiliaryCommand request - send PTZ auxiliary commands."""
        action = "http://www.onvif.org/ver10/ptz/wsdl/SendAuxiliaryCommand"

        # Extract auxiliary commands (IR cut, lens control, etc.)
        aux_data = request.parameters.get("auxiliary", {})

        logger.info(f"PTZ auxiliary command received: {aux_data}")

        resp = make_element("SendAuxiliaryCommandResponse", ONVIF_PTZ_NS)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_get_status(self, request: ONVIFRequest) -> bytes:
        """Handle GetStatus request - return current PTZ position."""
        return self.responder.build_ptz_status_response(
            request_message_id=request.message_id,
        )

    def get_current_position(self) -> Dict[str, float]:
        """Return the current PTZ position."""
        return self._ptz_position.copy()

    def is_moving(self) -> bool:
        """Check if PTZ is currently moving."""
        return self._is_moving

    def get_presets_list(self) -> List[Dict[str, Any]]:
        """Return list of all presets."""
        return list(self._presets.values())
