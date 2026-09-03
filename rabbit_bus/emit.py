"""The one line that fires a publisher.

A publisher file only builds a message. Nothing calls it on its own: an
announcement happens because someone said it happened. This is that someone,
called once, where the write it announces has just been done:

    from rabbit_bus.emit import emit

    emit("folder:POST", self)

The publisher runs right here, in the calling process, and its write-event goes
straight to the QUEUES its file declares. No round trip through the bus inbox:
that mailbox is where consumers are spoken to, and an announcement does not
depend on a daemon listening to it. The event is stamped with replyTo on that
inbox and a correlationId, so a recipient that answers still reaches the bus,
which records the answer in publish.txt.

Fire-and-forget by construction: an unknown namespace, a publisher without an
announcement yet, a broker that is down, a queue that refuses, all answer False
and are logged. An announcement can never fail the write that produced it,
which is why nothing raises out of here."""

import json
import logging
import ssl
import sys
import uuid
from pathlib import Path

logger = logging.getLogger("bus.emit")

BASE_DIR = Path(__file__).resolve().parent
CONNECT_TIMEOUT = 3


def _env():
    values = {}
    for line in (BASE_DIR / ".env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def _registry():
    """The publishers registry, imported the way main.py sees it: `publishers`
    is a top-level package from inside rabbit_bus/, and the caller's process
    knows nothing of that directory until told."""
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    import publishers

    return publishers.REGISTRY


def _pk(subject):
    """The primary key of what is announced, whatever it is handed.

    A model instance answers its own `pk`, a dict its "pk" or "id" key, a
    number or a string is already the key. The columns of a model are never
    read: the announcement carries an identity, not a copy of the row."""
    if isinstance(subject, dict):
        return subject.get("pk") if subject.get("pk") is not None else subject.get("id")
    if isinstance(subject, (int, str)) and not isinstance(subject, bool):
        return subject
    return getattr(subject, "pk", None)


def _extra(extra):
    """Free JSON, made safe to send. A string is taken as JSON already dumped
    and parsed back, so it travels as an object and not as text; anything else
    goes through json with str() as the fallback, which is what turns a date
    or a FieldFile into something a broker accepts."""
    if extra is None:
        return {}
    if isinstance(extra, str):
        try:
            return json.loads(extra)
        except ValueError:
            return extra
    return json.loads(json.dumps(extra, default=str))


def emit(namespace, subject, extra=None):
    """Fire the publisher of `namespace` for the row `subject` names.

    The publisher receives two keys and no others:

        {"pk": 207, "extra": {}}

    `subject` is the row, as an instance, a dict or the bare key; only its
    primary key travels. `extra` is optional and free: any JSON the caller
    wants carried with the announcement, never mixed with the identity."""
    try:
        from kombu import Connection, Producer

        entry = _registry().get(namespace)
        if entry is None:
            logger.warning("emit namespace=%s unknown, nothing sent", namespace)
            return False
        payload = entry["run"]({"pk": _pk(subject), "extra": _extra(extra)})
        if not isinstance(payload, dict):
            payload = {"data": payload}

        env = _env()
        inbox = f"{env['RABBITMQ_NAMESPACE']}.queue"
        correlation_id = str(uuid.uuid4())
        payload.setdefault("replyTo", inbox)
        payload.setdefault("correlationId", correlation_id)

        url = (
            f"{env['RABBITMQ_PROTOCOL']}://{env['RABBITMQ_USER']}:{env['RABBITMQ_PASSWORD']}"
            f"@{env['RABBITMQ_HOST']}:{env['RABBITMQ_PORT']}/{env['RABBITMQ_VHOST'].lstrip('/')}"
        )
        use_ssl = {"cert_reqs": ssl.CERT_REQUIRED} if env["RABBITMQ_PROTOCOL"] == "amqps" else False
        with Connection(url, ssl=use_ssl, connect_timeout=CONNECT_TIMEOUT) as connection:
            producer = Producer(connection.default_channel)
            for queue in entry["queues"]:
                producer.publish(
                    payload,
                    exchange="",
                    routing_key=queue,
                    serializer="json",
                    delivery_mode=2,
                    correlation_id=correlation_id,
                    reply_to=inbox,
                    retry=False,
                )
                logger.info("emitted namespace=%s queue=%s correlationId=%s", namespace, queue, correlation_id)
        return True
    except Exception as error:
        logger.warning("emit namespace=%s failed (%s: %s)", namespace, type(error).__name__, error)
        return False
