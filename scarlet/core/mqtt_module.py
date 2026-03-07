import json
import threading
import paho.mqtt.client as mqtt
import scarlet.core.log as log_

log = log_.service.logger("mqtt")

mqtt_client = mqtt.Client()

# Use a condition to coordinate await_ack and on_ack across threads.
PENDING_ACKS: set[str] = set()
_pending_condition = threading.Condition()
SUBSCRIPTIONS_ON_CONNECT: list[tuple[str, object]] = list()


def setup_mqtt(on_connect=None, on_message=None):
    def _wrapped_on_connect(client, userdata, flags, rc):
        if on_connect:
            try:
                on_connect(client, userdata, flags, rc)
            except Exception:
                log.exception("error in user on_connect")

        # apply queued subscriptions and message callbacks
        log.debug(f"Applying {len(SUBSCRIPTIONS_ON_CONNECT)} queued subscriptions on connect")
        for topic, cb in SUBSCRIPTIONS_ON_CONNECT:
            try:
                client.subscribe(topic)
                log.debug(f"subscribed to {topic}")
                if cb:
                    client.message_callback_add(topic, cb)
                    log.debug(f"added message callback for {topic}: {cb}")
            except Exception:
                log.exception(f"failed to (re)subscribe to {topic}")

    mqtt_client.on_connect = _wrapped_on_connect
    if on_message:
        mqtt_client.on_message = on_message
    return mqtt_client


def register_subscription(topic: str, callback=None):
    """Register a (topic, callback) pair to be applied when the client connects.

    This ensures subscriptions and message callbacks are (re-)applied after a
    network reconnect. Call this from services during initialization.
    """
    SUBSCRIPTIONS_ON_CONNECT.append((topic, callback))

def on_ack(_client, _userdata, msg):
    try:
        ack_data = json.loads(msg.payload.decode())
    except Exception:
        log.exception("failed to parse ack payload")
        return

    log.debug("Acknowledged on topic=%s: %s", getattr(msg, 'topic', None), ack_data)
    message_id = ack_data.get("message_id")
    if not message_id:
        return

    with _pending_condition:
        if message_id in PENDING_ACKS:
            PENDING_ACKS.remove(message_id)
            _pending_condition.notify_all()


def await_ack(message_id, timeout=5):
    with _pending_condition:
        PENDING_ACKS.add(message_id)
        waited = _pending_condition.wait_for(lambda: message_id not in PENDING_ACKS, timeout=timeout)
        if waited:
            log.debug("acknowledge received")
            return True
        else:
            log.warning("acknowledge timeout for %s", message_id)
            return False
