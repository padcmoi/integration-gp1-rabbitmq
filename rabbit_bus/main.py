"""Standalone RabbitMQ bus for GP1 test.

Listens on `<namespace>.queue`. A message naming a registered CONSUMER runs
that function with its args and the return value is answered to replyTo. A
message naming a registered PUBLISHER builds a payload and publishes it to the
1..N queues that publisher declares, in direct mode (default exchange "",
routing key = queue name); those queues may answer, and their answers are
matched back by correlationId.

With BUS_DEBUG=true, everything consumed is appended to consume.txt and every
publication and its answers to publish.txt, next to this file.
"""

import json
import logging
from http import HTTPStatus
import signal
import socket
import ssl
import sys
import time
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path

from kombu import Connection, Consumer, Producer, Queue

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = Path("/var/log/gp1-test-bus")
TRACE_MAX_BYTES = 5_000_000
TRACKED_MAX = 200

logger = logging.getLogger("bus")


def load_env():
    values = {}
    env_file = BASE_DIR / ".env"
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def setup_logging():
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handlers = [logging.StreamHandler(sys.stdout)]
    try:
        handlers.append(RotatingFileHandler(LOG_DIR / "bus.log", maxBytes=5_000_000, backupCount=3))
    except OSError:
        pass
    for handler in handlers:
        handler.setFormatter(formatter)
        logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO)


# Logging first, then the registries: a file the registry refuses is reported
# in the journal instead of disappearing silently.
setup_logging()

import consumers  # noqa: E402
import publishers  # noqa: E402

from consumers._errors import BusError  # noqa: E402


def success_status(namespace):
    # POST creates; everything else answers what it did. A publisher trigger is
    # 202: the message is dispatched, its processing happens elsewhere.
    return 201 if namespace.endswith(":POST") else 200


def error_status(error):
    if isinstance(error, BusError):
        return error.status
    if isinstance(error, ValueError) or type(error).__name__ == "ValidationError":
        return 400
    if isinstance(error, NotImplementedError):
        return 501
    return 500


def status_fields(code):
    return {"HTTP_CODE": code, "reason": HTTPStatus(code).phrase}


def unwrap(body, message):
    """Extract (namespace, args, reply_to, correlation_id, signer) from a message.

    Two accepted shapes:
    - plain: {"namespace": ..., "replyTo": ..., "correlationId": ..., "args": {...}}
    - naskot broker envelope: {"meta": {"keyId": ...}, "payload": {"type": ...,
      "data": "<json>"}} where replyTo/correlationId travel inside data. The
      signature is NOT verified here; the mailbox is the authorization, the
      keyId is logged for the trace.
    """
    if isinstance(body.get("meta"), dict) and isinstance(body.get("payload"), dict):
        payload = body["payload"]
        namespace = payload.get("type")
        data = payload.get("data")
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except ValueError:
                data = {}
        args = data if isinstance(data, dict) else {}
        reply_to = args.get("replyTo")
        correlation_id = args.get("correlationId")
        signer = body["meta"].get("keyId")
        return namespace, args, reply_to, correlation_id, signer

    namespace = body.get("namespace") or body.get("type")
    args = body.get("args", {})
    properties = message.properties or {}
    reply_to = body.get("replyTo") or body.get("reply_to") or body.get("reply-to") or properties.get("reply_to")
    correlation_id = body.get("correlationId") or body.get("correlation_id") or properties.get("correlation_id")
    return namespace, args, reply_to, correlation_id, None


class Bus:
    def __init__(self, env):
        self.env = env
        self.namespace = env["RABBITMQ_NAMESPACE"]
        self.queue_name = f"{self.namespace}.queue"
        self.retry_delay = int(env.get("RABBITMQ_UNKNOWN_TYPE_RETRY_DELAY_MS", "3000")) / 1000
        self.url = (
            f"{env['RABBITMQ_PROTOCOL']}://{env['RABBITMQ_USER']}:{env['RABBITMQ_PASSWORD']}"
            f"@{env['RABBITMQ_HOST']}:{env['RABBITMQ_PORT']}/{env['RABBITMQ_VHOST'].lstrip('/')}"
        )
        self.heartbeat = int(env.get("RABBITMQ_HEARTBEAT", "30"))
        self.debug = env.get("BUS_DEBUG", "").lower() in ("1", "true", "yes")
        self.connection = None
        # correlationId -> what was published under it, so an answer coming back
        # on our queue is recognized as an answer and never read as a command.
        self.tracked = {}

    def trace(self, filename, record):
        if not self.debug:
            return
        path = BASE_DIR / filename
        try:
            if path.exists() and path.stat().st_size > TRACE_MAX_BYTES:
                path.replace(path.with_name(filename + ".old"))
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"at": time.strftime("%Y-%m-%d %H:%M:%S"), **record}, ensure_ascii=False, default=str) + "\n")
        except OSError:
            pass

    def publish(self, queue, payload, correlation_id=None, reply_to=None):
        producer = Producer(self.connection.default_channel)
        producer.publish(
            payload,
            exchange="",
            routing_key=queue,
            serializer="json",
            delivery_mode=2,
            correlation_id=correlation_id or None,
            reply_to=reply_to or None,
            retry=True,
        )

    def run_publisher(self, namespace, args):
        entry = publishers.REGISTRY[namespace]
        payload = entry["run"](args)
        if not isinstance(payload, dict):
            payload = {"data": payload}
        correlation_id = str(uuid.uuid4())
        # The recipients may answer: the payload and the AMQP properties both
        # carry where and under which id, whichever the recipient reads.
        payload.setdefault("replyTo", self.queue_name)
        payload.setdefault("correlationId", correlation_id)
        for queue in entry["queues"]:
            self.publish(queue, payload, correlation_id, self.queue_name)
            logger.info("-> published namespace=%s queue=%s correlationId=%s", namespace, queue, correlation_id)
            self.trace("publish.txt", {"type": "publication", "namespace": namespace, "queue": queue, "correlationId": correlation_id, "payload": payload})
        self.tracked[correlation_id] = {"namespace": namespace, "queues": list(entry["queues"])}
        while len(self.tracked) > TRACKED_MAX:
            self.tracked.pop(next(iter(self.tracked)))
        return {"queues": list(entry["queues"]), "correlationId": correlation_id}

    def on_message(self, body, message):
        if isinstance(body, bytes):
            body = body.decode("utf-8", errors="replace")
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except ValueError:
                logger.warning("<- unreadable body, acked: %.500r", body)
                self.trace("consume.txt", {"type": "illisible", "body": body[:2000]})
                message.ack()
                return
        if not isinstance(body, dict):
            logger.warning("<- non-object body, acked: %.500r", body)
            self.trace("consume.txt", {"type": "non-objet", "body": body})
            message.ack()
            return

        namespace, args, reply_to, correlation_id, signer = unwrap(body, message)

        # An answer to something a publisher sent: recorded, never dispatched.
        if correlation_id in self.tracked:
            publication = self.tracked[correlation_id]
            logger.info("<- answer for publication namespace=%s correlationId=%s: %.1000s", publication["namespace"], correlation_id, json.dumps(body, default=str))
            self.trace("publish.txt", {"type": "reponse", "namespace": publication["namespace"], "correlationId": correlation_id, "body": body})
            self.trace("consume.txt", {"type": "reponse-publication", "correlationId": correlation_id, "body": body})
            message.ack()
            return

        if not namespace:
            # The data provider's write events land here too; they carry no
            # namespace and are a trace, not an order.
            logger.info("<- no namespace, logged and acked: %.1000s", json.dumps(body, default=str))
            self.trace("consume.txt", {"type": "sans-namespace", "body": body})
            message.ack()
            return

        logger.info(
            "<- namespace=%s replyTo=%s correlationId=%s signer=%s args=%.1000s",
            namespace, reply_to, correlation_id, signer, json.dumps(args, default=str),
        )

        answer = {"namespace": namespace, "correlationId": correlation_id or None}
        consumer = consumers.REGISTRY.get(namespace)
        if consumer is not None:
            self.trace("consume.txt", {"type": "consumer", "namespace": namespace, "correlationId": correlation_id, "body": body})
            try:
                answer.update(ok=True, **status_fields(success_status(namespace)), result=consumer(args))
            except Exception as error:  # a failure is an answer, never a redelivery loop
                status = error_status(error)
                log = logger.exception if status >= 500 else logger.warning
                log("namespace=%s answered %s: %s", namespace, status, error)
                answer.update(ok=False, **status_fields(status), error=f"{type(error).__name__}: {error}")
        elif namespace in publishers.REGISTRY:
            self.trace("consume.txt", {"type": "publisher", "namespace": namespace, "correlationId": correlation_id, "body": body})
            try:
                answer.update(ok=True, **status_fields(202), published=self.run_publisher(namespace, args))
            except Exception as error:
                status = error_status(error)
                log = logger.exception if status >= 500 else logger.warning
                log("publisher namespace=%s answered %s: %s", namespace, status, error)
                answer.update(ok=False, **status_fields(status), error=f"{type(error).__name__}: {error}")
        else:
            self.trace("consume.txt", {"type": "namespace-inconnu", "namespace": namespace, "body": body})
            answer.update(ok=False, **status_fields(404), error=f"unknown namespace '{namespace}'", known=sorted(consumers.REGISTRY), known_publishers=sorted(publishers.REGISTRY))
            logger.warning("no consumer nor publisher for namespace=%s", namespace)

        if reply_to:
            try:
                self.publish(reply_to, answer, correlation_id)
                logger.info("-> replied to %s: %.1000s", reply_to, json.dumps(answer, default=str))
            except Exception:
                logger.exception("reply to %s failed", reply_to)
        else:
            logger.info("no replyTo, nothing to answer to: %.1000s", json.dumps(answer, default=str))

        message.ack()

    def run_forever(self):
        while True:
            try:
                with Connection(self.url, ssl={"cert_reqs": ssl.CERT_REQUIRED}, heartbeat=self.heartbeat) as conn:
                    self.connection = conn
                    queue = Queue(self.queue_name, durable=True)
                    with Consumer(conn, queues=[queue], callbacks=[self.on_message], prefetch_count=1, accept=["json"]):
                        logger.info(
                            "consuming %s on %s debug=%s consumers=%s publishers=%s",
                            self.queue_name, self.env["RABBITMQ_HOST"], self.debug, sorted(consumers.REGISTRY), sorted(publishers.REGISTRY),
                        )
                        while True:
                            try:
                                conn.drain_events(timeout=1)
                            except socket.timeout:
                                conn.heartbeat_check()
            except (SystemExit, KeyboardInterrupt):
                logger.info("stopping")
                return
            except Exception as error:
                logger.warning("connection lost (%s: %s), retry in %ss", type(error).__name__, error, self.retry_delay)
                time.sleep(self.retry_delay)


def main():
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    Bus(load_env()).run_forever()


if __name__ == "__main__":
    main()
