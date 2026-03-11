#!/usr/bin/env python3
"""Generic dummy MQTT devices for local testing.

Modes:
  blinds          - subscribes to `home/blinds`, replies to `home/blinds/ack` with an ack
  irrigation      - subscribes to `home/irrigation`, replies to `home/irrigation/ack` with an ack
  arduino_weather - publishes simulated weather messages to `home/weather` at a fixed interval

Usage examples:
  python sandbox/dummy_devices.py --mode blinds
  python sandbox/dummy_devices.py --mode irrigation
  python sandbox/dummy_devices.py --mode arduino_weather --interval 5
"""
import argparse
import json
import time
import uuid
import random
import logging
from datetime import datetime

import paho.mqtt.client as mqtt
import threading

LOG = logging.getLogger("dummy_mqtt")
logging.basicConfig(level=logging.INFO)


def on_connect_factory(sub_topics):
    def on_connect(client, userdata, flags, rc):
        LOG.info(f"Connected to MQTT broker with rc={rc}")
        for t in sub_topics:
            client.subscribe(t)
            LOG.info(f"Subscribed to {t}")

    return on_connect


def on_message_ack_factory(ack_topic, echo_fields=()):
    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
        except Exception as e:
            LOG.error("Failed to decode message: %s", e)
            return

        LOG.info(f"Received command on {msg.topic}: {payload}")

        message_id = payload.get("message_id") or str(uuid.uuid4())

        simulate_time = random.uniform(0.05, 0.5)
        LOG.info(f"Simulating action for {simulate_time:.2f}s")
        time.sleep(simulate_time)

        ack = {"message_id": message_id, "status": "ok"}
        for k in echo_fields:
            if k in payload:
                ack[k] = payload[k]

        client.publish(ack_topic, json.dumps(ack))
        LOG.info(f"Published ack to {ack_topic}: {ack}")

    return on_message


def run_arduino_publisher(client, interval):
    LOG.info(f"Starting arduino weather publisher every {interval}s")
    try:
        while True:
            payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "wind": 400,
                "raw_wind": 400,
                "light_1": 4000,
                "light_2": 4000,
                "rain": 0,
            }
            client.publish("home/weather", json.dumps(payload))
            LOG.info(f"Published weather: {payload}")
            time.sleep(interval)
    except KeyboardInterrupt:
        LOG.info("Arduino publisher interrupted, disconnecting")
        client.disconnect()


def build_parser():
    p = argparse.ArgumentParser(description="Dummy MQTT devices for testing")
    p.add_argument("--host", default="localhost", help="MQTT broker host")
    p.add_argument("--port", default=1883, type=int, help="MQTT broker port")
    p.add_argument("--client-id", default=None, help="MQTT client id")
    p.add_argument("--mode", default="all", choices=("all", "blinds", "irrigation", "arduino_weather"), help="Which dummy device to run; default is all")
    p.add_argument("--interval", default=10, type=int, help="Publish interval for arduino_weather (seconds)")
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    client_id = args.client_id or f"dummy-{args.mode}-{uuid.uuid4().hex[:8]}"
    client = mqtt.Client(client_id=client_id)
    # Configure handlers before connecting
    if args.mode == "blinds":
        client.on_connect = on_connect_factory(["home/blinds"])
        client.on_message = on_message_ack_factory("home/blinds/ack", echo_fields=("left_blind", "right_blind"))

    elif args.mode == "irrigation":
        client.on_connect = on_connect_factory(["home/irrigation"])
        client.on_message = on_message_ack_factory("home/irrigation/ack", echo_fields=("zone",))

    elif args.mode == "all":
        # Subscribe to both topics and attach per-topic callbacks
        client.on_connect = on_connect_factory(["home/blinds", "home/irrigation"])
        client.message_callback_add("home/blinds", on_message_ack_factory("home/blinds/ack", echo_fields=("left_blind", "right_blind")))
        client.message_callback_add("home/irrigation", on_message_ack_factory("home/irrigation/ack", echo_fields=("zone",)))

    # Connect once all handlers are in place
    LOG.info(f"Connecting to MQTT broker {args.host}:{args.port} as {client_id} (mode={args.mode})")
    try:
        client.connect(args.host, args.port, 60)
    except Exception as e:
        LOG.error(f"Failed to connect to MQTT broker: {e}")
        return 1

    # Run according to selected mode
    if args.mode == "arduino_weather":
        client.loop_start()
        try:
            run_arduino_publisher(client, args.interval)
        finally:
            client.loop_stop()
            client.disconnect()

    elif args.mode == "all":
        client.loop_start()
        pub_thread = threading.Thread(target=run_arduino_publisher, args=(client, args.interval), daemon=True)
        pub_thread.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            LOG.info("Interrupted, shutting down all dummy devices")
        finally:
            client.loop_stop()
            client.disconnect()

    else:
        try:
            client.loop_forever()
        except KeyboardInterrupt:
            LOG.info("Interrupted, disconnecting")
            client.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
