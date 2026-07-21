"""
ONVIF Media Service Handler

Handles all ONVIF Media service operations (trt namespace).
Manages video/audio streams, profiles, encoders, and stream URIs.
"""

import logging
from typing import Optional, Dict, Any
from lxml import etree

from .parser import ONVIFRequest
from .responder import ONVIFResponder
from .xsd_types import (
    ONVIF_MEDIA_NS,
    ONVIF_NS,
    make_element,
    make_complex_element,
)

logger = logging.getLogger(__name__)


class MediaServiceHandler:
    """
    Handles ONVIF Media service operations.

    Supported operations:
    - GetProfiles
    - GetProfile
    - CreateProfile
    - DeleteProfile
    - GetVideoSources
    - GetStreamUri
    - StartStreamUri
    - StopStreamUri
    - GetVideoEncoderConfiguration
    - SetVideoEncoderConfiguration
    - GetVideoEncoderConfigurationOptions
    - GetMetadataConfiguration
    - SetMetadataConfiguration
    - GetAudioEncoderConfiguration
    - GetAudioStreams
    """

    def __init__(self, responder: ONVIFResponder, camera_config: Optional[Dict[str, Any]] = None):
        self.responder = responder
        self.camera_config = camera_config or {}
        self._profiles = {}
        self._stream_uris = {}
        self._initialize_profiles()

    def _initialize_profiles(self) -> None:
        """Initialize default media profiles."""
        config = self.camera_config

        self._profiles = {
            "profile0": {
                "token": "profile0",
                "name": config.get("profile_name_main", "Main"),
                "video_source_token": "video-source-0",
                "video_encoder_token": "encoder0",
                "encoding": "H264",
                "width": config.get("width", 1920),
                "height": config.get("height", 1080),
                "framerate": config.get("framerate", 30),
                "rtsp_port": config.get("rtsp_port", 554),
                "ptz_token": "ptz-node-0",
            },
            "profile1": {
                "token": "profile1",
                "name": config.get("profile_name_sub", "Sub"),
                "video_source_token": "video-source-0",
                "video_encoder_token": "encoder1",
                "encoding": "H264",
                "width": config.get("sub_width", 640),
                "height": config.get("sub_height", 480),
                "framerate": config.get("sub_framerate", 15),
                "rtsp_port": config.get("rtsp_port", 554),
            },
        }

    def handle(self, request: ONVIFRequest) -> bytes:
        """
        Route and handle a Media service request.

        Args:
            request: Parsed ONVIF request

        Returns:
            SOAP response bytes
        """
        operation = request.operation

        handlers = {
            "GetProfiles": self._handle_get_profiles,
            "GetProfile": self._handle_get_profile,
            "CreateProfile": self._handle_create_profile,
            "DeleteProfile": self._handle_delete_profile,
            "GetVideoSources": self._handle_get_video_sources,
            "GetStreamUri": self._handle_get_stream_uri,
            "StartStreamUri": self._handle_start_stream_uri,
            "StopStreamUri": self._handle_stop_stream_uri,
            "GetVideoEncoderConfiguration": self._handle_get_video_encoder_config,
            "SetVideoEncoderConfiguration": self._handle_set_video_encoder_config,
            "GetVideoEncoderConfigurationOptions": self._handle_get_video_encoder_config_options,
            "GetMetadataConfiguration": self._handle_get_metadata_config,
            "GetAudioEncoderConfiguration": self._handle_get_audio_encoder_config,
            "GetAudioStreams": self._handle_get_audio_streams,
        }

        handler = handlers.get(operation)
        if handler is None:
            logger.warning(f"Unhandled Media operation: {operation}")
            return self.responder.build_error_response(
                request_message_id=request.message_id,
                action=request.action,
                code="trt:ActionNotSupported",
                message=f"Operation {operation} is not supported",
            )

        try:
            return handler(request)
        except Exception as e:
            logger.error(f"Error handling {operation}: {e}", exc_info=True)
            return self.responder.build_error_response(
                request_message_id=request.message_id,
                action=request.action,
                code="trt:InternalServerError",
                message=str(e),
            )

    def _handle_get_profiles(self, request: ONVIFRequest) -> bytes:
        """Handle GetProfiles request."""
        from .xsd_types import build_media_profile

        profiles = [
            build_media_profile(
                token=p["token"],
                name=p["name"],
                video_source_token=p["video_source_token"],
                video_encoder_token=p["video_encoder_token"],
                ptz_token=p.get("ptz_token"),
            )
            for p in self._profiles.values()
        ]

        return self.responder.build_profiles_response(
            request_message_id=request.message_id,
            profiles=profiles,
        )

    def _handle_get_profile(self, request: ONVIFRequest) -> bytes:
        """Handle GetProfile request."""
        from .xsd_types import build_media_profile

        profile_token = request.parameters.get("profile_token", "profile0")
        profile = self._profiles.get(profile_token)

        if profile is None:
            return self.responder.build_error_response(
                request_message_id=request.message_id,
                action=request.action,
                code="tt:UnknownProfile",
                message=f"Profile {profile_token} does not exist",
            )

        profile_elem = build_media_profile(
            token=profile["token"],
            name=profile["name"],
            video_source_token=profile["video_source_token"],
            video_encoder_token=profile["video_encoder_token"],
            ptz_token=profile.get("ptz_token"),
        )

        resp = make_element("GetProfileResponse", ONVIF_MEDIA_NS)
        resp.append(profile_elem)

        action = "http://www.onvif.org/ver10/media/wsdl/GetProfile"
        return self.responder.build_response(request.message_id, action, resp)

    def _handle_create_profile(self, request: ONVIFRequest) -> bytes:
        """Handle CreateProfile request."""
        action = "http://www.onvif.org/ver10/media/wsdl/CreateProfile"

        name = request.parameters.get("name", f"Profile_{len(self._profiles)}")
        token = f"profile{len(self._profiles)}"

        self._profiles[token] = {
            "token": token,
            "name": name,
            "video_source_token": "video-source-0",
            "video_encoder_token": f"encoder{len(self._profiles)}",
            "encoding": "H264",
            "width": 1920,
            "height": 1080,
            "framerate": 30,
            "rtsp_port": 554,
        }

        resp = make_element("CreateProfileResponse", ONVIF_MEDIA_NS)
        resp.append(make_element("Profile", ONVIF_NS, token))

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_delete_profile(self, request: ONVIFRequest) -> bytes:
        """Handle DeleteProfile request."""
        action = "http://www.onvif.org/ver10/media/wsdl/DeleteProfile"

        profile_token = request.parameters.get("profile_token")
        if profile_token and profile_token in self._profiles:
            del self._profiles[profile_token]

        resp = make_element("DeleteProfileResponse", ONVIF_MEDIA_NS)
        return self.responder.build_response(request.message_id, action, resp)

    def _handle_get_video_sources(self, request: ONVIFRequest) -> bytes:
        """Handle GetVideoSources request."""
        return self.responder.build_video_sources_response(
            request_message_id=request.message_id,
        )

    def _handle_get_stream_uri(self, request: ONVIFRequest) -> bytes:
        """Handle GetStreamUri request."""
        profile_token = request.parameters.get("profile_token", "profile0")
        profile = self._profiles.get(profile_token)

        if profile is None:
            return self.responder.build_error_response(
                request_message_id=request.message_id,
                action=request.action,
                code="tt:UnknownProfile",
                message=f"Profile {profile_token} does not exist",
            )

        # Generate RTSP URI
        rtsp_host = self.camera_config.get("rtsp_host", "192.168.1.20")
        rtsp_port = profile.get("rtsp_port", 554)
        stream_path = self.camera_config.get(
            "stream_path",
            f"/cam/realmonitor?channel={profile_token.replace('profile', '')}&subtype=0"
            if "profile0" not in profile_token
            else "/cam/realmonitor?channel=1&subtype=0"
        )

        stream_uri = f"rtsp://{rtsp_host}:{rtsp_port}{stream_path}"

        # Cache the stream URI
        self._stream_uris[profile_token] = stream_uri

        return self.responder.build_stream_uri_response(
            request_message_id=request.message_id,
            stream_uri=stream_uri,
        )

    def _handle_start_stream_uri(self, request: ONVIFRequest) -> bytes:
        """Handle StartStreamUri request."""
        action = "http://www.onvif.org/ver10/media/wsdl/StartStreamUri"

        resp = make_element("StartStreamUriResponse", ONVIF_MEDIA_NS)
        resp.append(make_element("MediaUri", ONVIF_NS))

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_stop_stream_uri(self, request: ONVIFRequest) -> bytes:
        """Handle StopStreamUri request."""
        action = "http://www.onvif.org/ver10/media/wsdl/StopStreamUri"

        resp = make_element("StopStreamUriResponse", ONVIF_MEDIA_NS)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_get_video_encoder_config(self, request: ONVIFRequest) -> bytes:
        """Handle GetVideoEncoderConfiguration request."""
        action = "http://www.onvif.org/ver10/media/wsdl/GetVideoEncoderConfiguration"

        config_token = request.parameters.get("config_token", "encoder0")
        profile = self._profiles.get(config_token.replace("encoder", "profile"), {})

        resp = make_element("GetVideoEncoderConfigurationResponse", ONVIF_MEDIA_NS)

        config = make_element("VideoEncoderConfiguration", ONVIF_NS)
        config.append(make_element("Token", ONVIF_NS, config_token))
        config.append(make_element("Name", ONVIF_NS, f"Encoder_{config_token}"))
        config.append(make_element("UseCount", ONVIF_NS, "0"))
        config.append(make_element("Encoding", ONVIF_NS, "H264"))

        resolution = make_element("Resolution", ONVIF_NS)
        resolution.append(make_element("Width", ONVIF_NS, str(profile.get("width", 1920))))
        resolution.append(make_element("Height", ONVIF_NS, str(profile.get("height", 1080))))
        config.append(resolution)

        config.append(make_element("Quality", ONVIF_NS, "5.0"))

        resp.append(config)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_set_video_encoder_config(self, request: ONVIFRequest) -> bytes:
        """Handle SetVideoEncoderConfiguration request."""
        action = "http://www.onvif.org/ver10/media/wsdl/SetVideoEncoderConfiguration"

        logger.info(f"Video encoder configuration updated: {request.parameters}")

        resp = make_element("SetVideoEncoderConfigurationResponse", ONVIF_MEDIA_NS)
        return self.responder.build_response(request.message_id, action, resp)

    def _handle_get_video_encoder_config_options(self, request: ONVIFRequest) -> bytes:
        """Handle GetVideoEncoderConfigurationOptions request."""
        return self.responder.build_video_encoder_config_options_response(
            request_message_id=request.message_id,
        )

    def _handle_get_metadata_config(self, request: ONVIFRequest) -> bytes:
        """Handle GetMetadataConfiguration request."""
        action = "http://www.onvif.org/ver10/media/wsdl/GetMetadataConfiguration"

        resp = make_element("GetMetadataConfigurationResponse", ONVIF_MEDIA_NS)

        config = make_element("MetadataConfiguration", ONVIF_NS)
        config.append(make_element("Token", ONVIF_NS, "metadata-0"))
        config.append(make_element("Name", ONVIF_NS, "Metadata"))
        config.append(make_element("UseCount", ONVIF_NS, "0"))
        config.append(make_element("PTZConfiguration", ONVIF_NS))
        config.append(make_element("AudioConfiguration", ONVIF_NS))

        resp.append(config)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_get_audio_encoder_config(self, request: ONVIFRequest) -> bytes:
        """Handle GetAudioEncoderConfiguration request."""
        action = "http://www.onvif.org/ver10/media/wsdl/GetAudioEncoderConfiguration"

        resp = make_element("GetAudioEncoderConfigurationResponse", ONVIF_MEDIA_NS)

        config = make_element("AudioEncoderConfiguration", ONVIF_NS)
        config.append(make_element("Token", ONVIF_NS, "audio-encoder-0"))
        config.append(make_element("Name", ONVIF_NS, "AudioEncoder"))
        config.append(make_element("UseCount", ONVIF_NS, "0"))
        config.append(make_element("Encoding", ONVIF_NS, "AAC"))
        config.append(make_element("Bitrate", ONVIF_NS, "64000"))
        config.append(make_element("SampleRate", ONVIF_NS, "44100"))

        resp.append(config)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_get_audio_streams(self, request: ONVIFRequest) -> bytes:
        """Handle GetAudioStreams request."""
        action = "http://www.onvif.org/ver10/media/wsdl/GetAudioStreams"

        resp = make_element("GetAudioStreamsResponse", ONVIF_MEDIA_NS)

        # Return empty list if no audio
        # (add audio stream elements if audio is supported)

        return self.responder.build_response(request.message_id, action, resp)
