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


def emit(namespace, subject, extra=None):
    """Fire the publisher of `namespace` for the row `subject` names.

    Two keys leave here and no others:

        {"pk": 207, "extra": {}}

    `subject` is the row, as an instance, a dict or the bare key; only its
    primary key travels. `extra` is optional and free: any JSON the caller
    wants carried with the announcement, never mixed with the identity."""
    try:
        from kombu import Connection, Producer

        env = _env()
        url = (
            f"{env['RABBITMQ_PROTOCOL']}://{env['RABBITMQ_USER']}:{env['RABBITMQ_PASSWORD']}"
            f"@{env['RABBITMQ_HOST']}:{env['RABBITMQ_PORT']}/{env['RABBITMQ_VHOST'].lstrip('/')}"
        )
        use_ssl = {"cert_reqs": ssl.CERT_REQUIRED} if env["RABBITMQ_PROTOCOL"] == "amqps" else False
        message = {"namespace": namespace, "args": {"pk": _pk(subject), "extra": {} if extra is None else extra}}
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
