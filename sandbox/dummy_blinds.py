#!/usr/bin/env python3
"""Dummy blinds device that listens on MQTT topic `home/blinds` and replies with an ack

Usage:
  python sandbox/dummy_blinds.py --host localhost --port 1883

This script subscribes to `home/blinds`, parses incoming JSON payloads, and
publishes an ack message to `home/blinds/ack` with the same `message_id` so the
server-side `scarlet.core.mqtt.await_ack` can detect it.
"""
import argparse
import json
import time
import uuid
import random
import logging

import paho.mqtt.client as mqtt

LOG = logging.getLogger("dummy_blinds")
logging.basicConfig(level=logging.INFO)


def on_connect(client, userdata, flags, rc):
    LOG.info(f"Connected to MQTT broker with rc={rc}")
    client.subscribe("home/blinds")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except Exception as e:
        LOG.error("Failed to decode message: %s", e)
        return

    LOG.info(f"Received blinds command: {payload}")

    # Extract message_id so we can ack it
    message_id = payload.get("message_id") or str(uuid.uuid4())

    # Simulate performing the action (sleep a little to mimic hardware)
    simulate_time = random.uniform(0.05, 0.5)
    LOG.info(f"Simulating blinds action for {simulate_time:.2f}s")
    time.sleep(simulate_time)

    # Build ack payload. Include status and echo any positions sent.
    ack = {
        "message_id": message_id,
        "status": "ok",
    }
    # Echo optional fields if present
    for k in ("left_blind", "right_blind"):
        if k in payload:
            ack[k] = payload[k]

    client.publish("home/blinds/ack", json.dumps(ack))
    LOG.info(f"Published ack: {ack}")


def build_parser():
    p = argparse.ArgumentParser(description="Dummy blinds MQTT client")
    p.add_argument("--host", default="localhost", help="MQTT broker host")
    p.add_argument("--port", default=1883, type=int, help="MQTT broker port")
    p.add_argument("--client-id", default=None, help="MQTT client id")
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    client_id = args.client_id or f"dummy-blinds-{uuid.uuid4().hex[:8]}"
    client = mqtt.Client(client_id=client_id)
    client.on_connect = on_connect
    client.on_message = on_message

    LOG.info(f"Connecting to MQTT broker {args.host}:{args.port} as {client_id}")
    try:
        client.connect(args.host, args.port, 60)
    except Exception as e:
        LOG.error(f"Failed to connect to MQTT broker: {e}")
        return 1

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        LOG.info("Interrupted, disconnecting")
        client.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
