"""The one line that fires a publisher.

A publisher file only builds a message. Nothing calls it on its own: an
announcement happens because someone said it happened. This is that someone,
called once, where the write it announces has just been done:

    from rabbit_bus.emit import emit

    emit("folder:POST", self)

The event is handed to the bus queue and the call returns. The bus runs the
publisher of that namespace and addresses its message to the queues that
publisher declares.

Fire-and-forget by construction: a broker that is down, a queue that refuses,
a row that will not serialize, all answer False and are logged. An announcement
can never fail the write that produced it, which is why nothing raises out of
here."""

import logging
import ssl
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


def _row(subject):
    """A model instance as a JSON-safe row. A dict is already one and passes
    through untouched, so a caller holding something else than a model keeps
    the last word on what it announces. A bare key is the minimum an
    announcement can carry, and it is enough: {"id": <the key>}."""
    if isinstance(subject, dict):
        return subject
    if isinstance(subject, (int, str)) and not isinstance(subject, bool):
        return {"id": subject}
    fields = getattr(getattr(subject, "_meta", None), "concrete_fields", None)
    if fields is None:
        return {"value": str(subject)}
    row = {}
    for field in fields:
        value = getattr(subject, field.attname, None)
        row[field.attname] = value if isinstance(value, (str, int, float, bool)) or value is None else str(value)
    return row


def emit(namespace, subject=None, extra=None):
    """Fire the publisher of `namespace` with `subject` as its event.

    The args key is the business folder, read from the namespace itself:
    "folder:POST" hands its row over as {"folder": {...}}, which is exactly
    what publishers/folder/post.py reads.

    `extra` is optional and free: any JSON the caller wants carried with the
    announcement travels under its own key, never mixed into the row."""
    try:
        from kombu import Connection, Producer

        env = _env()
        url = (
            f"{env['RABBITMQ_PROTOCOL']}://{env['RABBITMQ_USER']}:{env['RABBITMQ_PASSWORD']}"
            f"@{env['RABBITMQ_HOST']}:{env['RABBITMQ_PORT']}/{env['RABBITMQ_VHOST'].lstrip('/')}"
        )
        use_ssl = {"cert_reqs": ssl.CERT_REQUIRED} if env["RABBITMQ_PROTOCOL"] == "amqps" else False
        args = {} if subject is None else {namespace.split(":")[0]: _row(subject)}
        if extra is not None:
            args["extra"] = extra
        message = {"namespace": namespace, "args": args}
        with Connection(url, ssl=use_ssl, connect_timeout=CONNECT_TIMEOUT) as connection:
            Producer(connection.default_channel).publish(
                message,
                exchange="",
                routing_key=f"{env['RABBITMQ_NAMESPACE']}.queue",
                serializer="json",
                delivery_mode=2,
                retry=False,
            )
        logger.info("emitted namespace=%s", namespace)
        return True
    except Exception as error:
        logger.warning("emit namespace=%s failed (%s: %s)", namespace, type(error).__name__, error)
        return False
