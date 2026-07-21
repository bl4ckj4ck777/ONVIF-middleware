"""
ONVIF Imaging Service Handler

Handles all ONVIF Imaging service operations (timg namespace).
Manages camera imaging settings like focus, iris, white balance, brightness, etc.
"""

import logging
from typing import Optional, Dict, Any
from lxml import etree

from .parser import ONVIFRequest
from .responder import ONVIFResponder
from .xsd_types import (
    ONVIF_IMAGING_NS,
    ONVIF_NS,
    make_element,
    make_complex_element,
)

logger = logging.getLogger(__name__)


class ImagingServiceHandler:
    """
    Handles ONVIF Imaging service operations.

    Supported operations:
    - GetOptions
    - GetStatus
    - GetImagingSettings
    - SetImagingSettings
    - GetMovieMode
    - SetMovieMode
    """

    def __init__(self, responder: ONVIFResponder, camera_config: Optional[Dict[str, Any]] = None):
        self.responder = responder
        self.camera_config = camera_config or {}
        self._imaging_settings = self._initialize_settings()

    def _initialize_settings(self) -> Dict[str, Any]:
        """Initialize default imaging settings."""
        config = self.camera_config

        return {
            "focus": {
                "mode": config.get("focus_mode", "Auto"),
                "absolute": {"position": 0.0, "distance": 0.0},
                "relative": {"direction": "0", "distance": "0", "duration": "PT0S"},
                "continuous": {"speed": 0.0},
            },
            "iris": {
                "mode": config.get("iris_mode", "Auto"),
                "absolute": {"iris": 0.0},
            },
            "white_balance": {
                "mode": config.get("white_balance_mode", "Auto"),
                "manual": {"red": 0.5, "green": 0.5, "blue": 0.5},
            },
            "brightness": config.get("brightness", 50),
            "contrast": config.get("contrast", 50),
            "saturation": config.get("saturation", 50),
            "sharpness": config.get("sharpness", 50),
            "backlight_compensation": config.get("backlight_compensation", False),
            "light_mode": config.get("light_mode", "Auto"),
            "wdr": config.get("wdr", False),
            "noise_reduction": config.get("noise_reduction", 0.5),
        }

    def handle(self, request: ONVIFRequest) -> bytes:
        """
        Route and handle an Imaging service request.

        Args:
            request: Parsed ONVIF request

        Returns:
            SOAP response bytes
        """
        operation = request.operation

        handlers = {
            "GetOptions": self._handle_get_options,
            "GetStatus": self._handle_get_status,
            "GetImagingSettings": self._handle_get_imaging_settings,
            "SetImagingSettings": self._handle_set_imaging_settings,
            "GetMovieMode": self._handle_get_movie_mode,
            "SetMovieMode": self._handle_set_movie_mode,
        }

        handler = handlers.get(operation)
        if handler is None:
            logger.warning(f"Unhandled Imaging operation: {operation}")
            return self.responder.build_error_response(
                request_message_id=request.message_id,
                action=request.action,
                code="timg:ActionNotSupported",
                message=f"Operation {operation} is not supported",
            )

        try:
            return handler(request)
        except Exception as e:
            logger.error(f"Error handling {operation}: {e}", exc_info=True)
            return self.responder.build_error_response(
                request_message_id=request.message_id,
                action=request.action,
                code="timg:InternalServerError",
                message=str(e),
            )

    def _handle_get_options(self, request: ONVIFRequest) -> bytes:
        """Handle GetImagingOptions request."""
        action = "http://www.onvif.org/ver20/imaging/wsdl/GetImagingOptions"

        resp = make_element("GetImagingOptionsResponse", ONVIF_IMAGING_NS)

        options = make_element("ImagingOptions", ONVIF_NS)
        options.set("XSI_type", "timg:ImagingOptions")

        # Focus options
        focus = make_element("Focus", ONVIF_NS)
        focus_range = make_element("Absolute", ONVIF_NS)
        focus_range.append(make_element("PositionRange", ONVIF_NS))
        pos_range = focus_range.find(".//PositionRange") or focus_range
        pos_range.append(make_element("Min", ONVIF_NS, "0.0"))
        pos_range.append(make_element("Max", ONVIF_NS, "1.0"))
        focus.append(focus_range)
        options.append(focus)

        # Iris options
        iris = make_element("Iris", ONVIF_NS)
        iris_range = make_element("Absolute", ONVIF_NS)
        iris_range.append(make_element("IrisRange", ONVIF_NS))
        iris_range.find(".//IrisRange") or iris_range
        iris.append(iris_range)
        options.append(iris)

        resp.append(options)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_get_status(self, request: ONVIFRequest) -> bytes:
        """Handle GetImagingStatus request."""
        action = "http://www.onvif.org/ver20/imaging/wsdl/GetStatus"

        resp = make_element("GetImagingStatusResponse", ONVIF_IMAGING_NS)

        status = make_element("ImagingStatus", ONVIF_NS)
        video_source_token = make_element("VideoSourceToken", ONVIF_NS, "video-source-0")
        status.append(video_source_token)

        resp.append(status)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_get_imaging_settings(self, request: ONVIFRequest) -> bytes:
        """Handle GetImagingSettings request."""
        action = "http://www.onvif.org/ver20/imaging/wsdl/GetImagingSettings"

        resp = make_element("GetImagingSettingsResponse", ONVIF_IMAGING_NS)

        settings = make_element("ImagingSettings", ONVIF_NS)
        settings.append(make_element("VideoSourceToken", ONVIF_NS, "video-source-0"))

        # Build imaging settings from current state
        settings.append(self._build_focus_element())
        settings.append(self._build_iris_element())
        settings.append(self._build_white_balance_element())
        settings.append(self._build_brightness_element())
        settings.append(self._build_contrast_element())
        settings.append(self._build_saturation_element())
        settings.append(self._build_sharpness_element())
        settings.append(self._build_backlight_element())
        settings.append(self._build_light_mode_element())
        settings.append(self._build_wdr_element())

        resp.append(settings)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_set_imaging_settings(self, request: ONVIFRequest) -> bytes:
        """Handle SetImagingSettings request."""
        action = "http://www.onvif.org/ver20/imaging/wsdl/SetImagingSettings"

        # Update internal settings based on request
        params = request.parameters
        for key, value in params.items():
            if key in self._imaging_settings:
                self._imaging_settings[key] = value

        logger.info(f"Imaging settings updated: {params}")

        resp = make_element("SetImagingSettingsResponse", ONVIF_IMAGING_NS)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_get_movie_mode(self, request: ONVIFRequest) -> bytes:
        """Handle GetMovieMode request."""
        action = "http://www.onvif.org/ver20/imaging/wsdl/GetMovieMode"

        resp = make_element("GetMovieModeResponse", ONVIF_IMAGING_NS)

        movie_mode = make_element("MovieMode", ONVIF_NS)
        movie_mode.set("XSI_type", "timg:MovieMode")
        movie_mode.append(make_element("Active", ONVIF_NS, "false"))

        resp.append(movie_mode)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_set_movie_mode(self, request: ONVIFRequest) -> bytes:
        """Handle SetMovieMode request."""
        action = "http://www.onvif.org/ver20/imaging/wsdl/SetMovieMode"

        resp = make_element("SetMovieModeResponse", ONVIF_IMAGING_NS)

        return self.responder.build_response(request.message_id, action, resp)

    # ============================================================
    # Helper methods for building imaging setting elements
    # ============================================================

    def _build_focus_element(self) -> etree._Element:
        """Build Focus element from current settings."""
        focus = make_element("Focus", ONVIF_NS)

        mode = make_element("Mode", ONVIF_NS, self._imaging_settings["focus"]["mode"])
        focus.append(mode)

        if self._imaging_settings["focus"]["mode"] == "Manual":
            absolute = make_element("Absolute", ONVIF_NS)
            absolute.append(make_element("Position", ONVIF_NS, str(self._imaging_settings["focus"]["absolute"]["position"])))
            absolute.append(make_element("Distance", ONVIF_NS, str(self._imaging_settings["focus"]["absolute"]["distance"])))
            focus.append(absolute)

        return focus

    def _build_iris_element(self) -> etree._Element:
        """Build Iris element from current settings."""
        iris = make_element("Iris", ONVIF_NS)

        mode = make_element("Mode", ONVIF_NS, self._imaging_settings["iris"]["mode"])
        iris.append(mode)

        return iris

    def _build_white_balance_element(self) -> etree._Element:
        """Build WhiteBalance element from current settings."""
        wb = make_element("WhiteBalance", ONVIF_NS)

        mode = make_element("Mode", ONVIF_NS, self._imaging_settings["white_balance"]["mode"])
        wb.append(mode)

        if self._imaging_settings["white_balance"]["mode"] == "Manual":
            manual = make_element("Manual", ONVIF_NS)
            manual.append(make_element("Red", ONVIF_NS, str(self._imaging_settings["white_balance"]["manual"]["red"])))
            manual.append(make_element("Green", ONVIF_NS, str(self._imaging_settings["white_balance"]["manual"]["green"])))
            manual.append(make_element("Blue", ONVIF_NS, str(self._imaging_settings["white_balance"]["manual"]["blue"])))
            wb.append(manual)

        return wb

    def _build_brightness_element(self) -> etree._Element:
        """Build Brightness element."""
        brightness = make_element("Brightness", ONVIF_NS)
        brightness.append(make_element("Brightness", ONVIF_NS, str(self._imaging_settings["brightness"])))
        return brightness

    def _build_contrast_element(self) -> etree._Element:
        """Build Contrast element."""
        contrast = make_element("Contrast", ONVIF_NS)
        contrast.append(make_element("Contrast", ONVIF_NS, str(self._imaging_settings["contrast"])))
        return contrast

    def _build_saturation_element(self) -> etree._Element:
        """Build Saturation element."""
        saturation = make_element("Saturation", ONVIF_NS)
        saturation.append(make_element("Saturation", ONVIF_NS, str(self._imaging_settings["saturation"])))
        return saturation

    def _build_sharpness_element(self) -> etree._Element:
        """Build Sharpness element."""
        sharpness = make_element("Sharpness", ONVIF_NS)
        sharpness.append(make_element("Sharpness", ONVIF_NS, str(self._imaging_settings["sharpness"])))
        return sharpness

    def _build_backlight_element(self) -> etree._Element:
        """Build BacklightCompensation element."""
        backlight = make_element("BacklightCompensation", ONVIF_NS)
        backlight.append(make_element("Mode", ONVIF_NS, "On" if self._imaging_settings["backlight_compensation"] else "Off"))
        return backlight

    def _build_light_mode_element(self) -> etree._Element:
        """Build LightMode element."""
        light = make_element("LightMode", ONVIF_NS)
        light.append(make_element("Mode", ONVIF_NS, self._imaging_settings["light_mode"]))
        return light

    def _build_wdr_element(self) -> etree._Element:
        """Build WDR element."""
        wdr = make_element("WideDynamicRange", ONVIF_NS)
        wdr.append(make_element("Mode", ONVIF_NS, "On" if self._imaging_settings["wdr"] else "Off"))
        return wdr

    def get_current_settings(self) -> Dict[str, Any]:
        """Return current imaging settings."""
        return self._imaging_settings.copy()
