"""
ONVIF Event Service Handler

Handles all ONVIF Event service operations.
Manages event subscriptions, topic namespaces, and event notifications.
"""

import logging
import threading
import time
from typing import Optional, Dict, Any, List, Set
from lxml import etree

from .parser import ONVIFRequest
from .responder import ONVIFResponder
from .xsd_types import (
    ONVIF_EVENTS_NS,
    ONVIF_NS,
    make_element,
    make_complex_element,
)

logger = logging.getLogger(__name__)


class EventSubscription:
    """Represents an active ONVIF event subscription."""

    def __init__(
        self,
        subscription_id: str,
        consumer_endpoint: str,
        topic_namespace: str,
        message_expiry: float = 600.0,  # 10 minutes default
    ):
        self.subscription_id = subscription_id
        self.consumer_endpoint = consumer_endpoint
        self.topic_namespace = topic_namespace
        self.message_expiry = message_expiry
        self.created_at = time.time()
        self.last_renewed = time.time()
        self.is_active = True


class EventServiceHandler:
    """
    Handles ONVIF Event service operations.

    Supported operations:
    - Subscribe
    - Unsubscribe
    - Renew
    - GetEventProperties
    - PullMessages
    - UnpullMessages
    - Notify
    """

    def __init__(self, responder: ONVIFResponder, camera_config: Optional[Dict[str, Any]] = None):
        self.responder = responder
        self.camera_config = camera_config or {}
        self._subscriptions: Dict[str, EventSubscription] = {}
        self._message_queue: List[Dict[str, Any]] = []
        self._queue_lock = threading.Lock()
        self._subscription_counter = 0
        self._event_handler = None
        self._cleanup_thread = None
        self._start_cleanup_thread()

    def _start_cleanup_thread(self) -> None:
        """Start a background thread to clean up expired subscriptions."""
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_expired,
            daemon=True,
            name="onvif-event-cleanup",
        )
        self._cleanup_thread.start()

    def _cleanup_expired(self) -> None:
        """Periodically clean up expired subscriptions."""
        while True:
            time.sleep(30)
            now = time.time()
            expired = []
            for sub_id, sub in self._subscriptions.items():
                if now - sub.last_renewed > sub.message_expiry:
                    expired.append(sub_id)
            for sub_id in expired:
                logger.info(f"Cleaning up expired subscription: {sub_id}")
                with self._queue_lock:
                    del self._subscriptions[sub_id]

    def set_event_handler(self, handler) -> None:
        """
        Set a custom event handler for processing incoming events.

        Args:
            handler: Callable that receives event data dicts
        """
        self._event_handler = handler

    def handle(self, request: ONVIFRequest) -> bytes:
        """
        Route and handle an Event service request.

        Args:
            request: Parsed ONVIF request

        Returns:
            SOAP response bytes
        """
        operation = request.operation

        handlers = {
            "Subscribe": self._handle_subscribe,
            "Unsubscribe": self._handle_unsubscribe,
            "Renew": self._handle_renew,
            "GetEventProperties": self._handle_get_event_properties,
            "PullMessages": self._handle_pull_messages,
            "UnpullMessages": self._handle_unpull_messages,
        }

        handler = handlers.get(operation)
        if handler is None:
            logger.warning(f"Unhandled Event operation: {operation}")
            return self.responder.build_error_response(
                request_message_id=request.message_id,
                action=request.action,
                code="tev:ActionNotSupported",
                message=f"Operation {operation} is not supported",
            )

        try:
            return handler(request)
        except Exception as e:
            logger.error(f"Error handling {operation}: {e}", exc_info=True)
            return self.responder.build_error_response(
                request_message_id=request.message_id,
                action=request.action,
                code="tev:InternalServerError",
                message=str(e),
            )

    def _handle_subscribe(self, request: ONVIFRequest) -> bytes:
        """Handle Subscribe request - create a new event subscription."""
        action = "http://www.onvif.org/ver10/events/wsdl/EventPortType/SubscribeRequest"

        # Extract consumer endpoint from request
        consumer_endpoint = request.parameters.get(
            "consumer_endpoint",
            "http://localhost:8080/events/pull",
        )

        # Generate subscription ID
        self._subscription_counter += 1
        subscription_id = f"onvif-sub-{self._subscription_counter}"

        # Determine topic namespace
        topic_namespace = request.parameters.get(
            "topic_namespace",
            "http://www.onvif.org/ver10/topic/wsdl",
        )

        # Create subscription
        subscription = EventSubscription(
            subscription_id=subscription_id,
            consumer_endpoint=consumer_endpoint,
            topic_namespace=topic_namespace,
            message_expiry=600.0,
        )

        with self._queue_lock:
            self._subscriptions[subscription_id] = subscription

        logger.info(
            f"Event subscription created: {subscription_id} -> {consumer_endpoint}"
        )

        return self.responder.build_subscribe_response(
            request_message_id=request.message_id,
            subscription_id=subscription_id,
            notification_endpoint=consumer_endpoint,
        )

    def _handle_unsubscribe(self, request: ONVIFRequest) -> bytes:
        """Handle Unsubscribe request - terminate an event subscription."""
        action = "http://www.onvif.org/ver10/events/wsdl/EventPortType/UnsubscribeRequest"

        subscription_id = request.parameters.get("subscription_id")

        if subscription_id:
            with self._queue_lock:
                if subscription_id in self._subscriptions:
                    self._subscriptions[subscription_id].is_active = False
                    del self._subscriptions[subscription_id]
                    logger.info(f"Event subscription removed: {subscription_id}")

        resp = make_element("UnsubscribeResponse", ONVIF_EVENTS_NS)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_renew(self, request: ONVIFRequest) -> bytes:
        """Handle Renew request - extend subscription lifetime."""
        action = "http://www.onvif.org/ver10/events/wsdl/EventPortType/RenewRequest"

        subscription_id = request.parameters.get("subscription_id")

        if subscription_id and subscription_id in self._subscriptions:
            with self._queue_lock:
                self._subscriptions[subscription_id].last_renewed = time.time()
                logger.info(f"Event subscription renewed: {subscription_id}")
        else:
            logger.warning(f"Renew requested for unknown subscription: {subscription_id}")

        resp = make_element("RenewResponse", ONVIF_EVENTS_NS)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_get_event_properties(self, request: ONVIFRequest) -> bytes:
        """Handle GetEventProperties request."""
        action = "http://www.onvif.org/ver10/events/wsdl/EventPortType/GetEventPropertiesRequest"

        resp = make_element("GetEventPropertiesResponse", ONVIF_EVENTS_NS)

        # Topic namespace tree
        topics = make_element("TopicNamespace", ONVIF_NS)
        topics.set("Location", "Topic")

        # Video analytics topics
        video_topic = make_element(
            "Topic",
            ONVIF_NS,
            "http://www.onvif.org/ver10/topic/wsdl/VideoSource/MotionDetection",
        )
        video_topic.set("Definition", "true")
        topics.append(video_topic)

        # PTZ topics
        ptz_topic = make_element(
            "Topic",
            ONVIF_NS,
            "http://www.onvif.org/ver10/topic/wsdl/PTZ/PanTilt",
        )
        topics.append(ptz_topic)

        # Device topics
        device_topic = make_element(
            "Topic",
            ONVIF_NS,
            "http://www.onvif.org/ver10/topic/wsdl/Device/ConnectionStatus",
        )
        topics.append(device_topic)

        resp.append(topics)

        return self.responder.build_response(request.message_id, action, resp)

    def _handle_pull_messages(self, request: ONVIFRequest) -> bytes:
        """Handle PullMessages request - retrieve queued event notifications."""
        action = "http://www.onvif.org/ver10/events/wsdl/EventPortType/PullMessagesRequest"

        # Extract timeout
        timeout = request.parameters.get("timeout", 10)
        try:
            timeout = int(timeout)
        except (ValueError, TypeError):
            timeout = 10

        # Collect available messages
        messages = []
        with self._queue_lock:
            messages = self._message_queue.copy()
            self._message_queue.clear()

        # If no messages, return empty response (NVR will retry after timeout)
        resp = self.responder.build_pull_messages_response(
            request_message_id=request.message_id,
            messages=messages if messages else [],
        )

        if not messages:
            logger.debug("PullMessages returned no messages (timeout or empty)")

        return resp

    def _handle_unpull_messages(self, request: ONVIFRequest) -> bytes:
        """Handle UnpullMessages request."""
        action = "http://www.onvif.org/ver10/events/wsdl/EventPortType/UnpullMessagesRequest"

        resp = make_element("UnpullMessagesResponse", ONVIF_EVENTS_NS)

        return self.responder.build_response(request.message_id, action, resp)

    def add_event_message(self, message_data: Dict[str, Any]) -> None:
        """
        Add an event message to the notification queue.

        This is called by the middleware's event processing logic when
        an event is detected from the camera.

        Args:
            message_data: Dictionary containing event data
        """
        message = make_element("NotificationMessage", ONVIF_EVENTS_NS)

        topic = make_element("Topic", ONVIF_EVENTS_NS)
        topic.text = message_data.get(
            "topic",
            "http://www.onvif.org/ver10/topic/wsdl/VideoSource/MotionDetection/True",
        )
        message.append(topic)

        if "data" in message_data:
            data = make_element("Data", ONVIF_EVENTS_NS)
            for key, value in message_data["data"].items():
                item = make_element("SimpleItem", ONVIF_EVENTS_NS, Name=key, Value=str(value))
                data.append(item)
            message.append(data)

        with self._queue_lock:
            self._message_queue.append(message)

        logger.debug(f"Event message queued: {message_data.get('topic', 'unknown')}")

    def get_active_subscriptions(self) -> List[EventSubscription]:
        """Return list of active subscriptions."""
        with self._queue_lock:
            return [s for s in self._subscriptions.values() if s.is_active]

    def get_subscription_count(self) -> int:
        """Return count of active subscriptions."""
        with self._queue_lock:
            return len([s for s in self._subscriptions.values() if s.is_active])
