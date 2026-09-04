"""The one line that fires a publisher.

A publisher file only builds a message. Nothing calls it on its own: an
announcement happens because someone said it happened. This is that someone,
written where the write it announces has just been done:

    from rabbit_bus.emit import AmqpPublish

    message = AmqpPublish("folder:POST")
    message.pk = 630
    message.execute()

The publisher runs right here, in the calling process, and its write-event goes
straight to the QUEUES its file declares. No round trip through the bus inbox:
that mailbox is where consumers are spoken to, and an announcement does not
depend on a daemon listening to it. The event is stamped with replyTo on that
inbox and a correlationId, so a recipient that answers still reaches the bus,
which records the answer in publish.txt.

Fire-and-forget by construction: an unknown namespace, a missing pk, a
publisher without an announcement yet, a broker that is down, a queue that
refuses, all answer False and are logged. An announcement can never fail the
write that produced it, which is why nothing raises out of here."""

import json
import logging
import ssl
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("bus.emit")

BASE_DIR = Path(__file__).resolve().parent
CONNECT_TIMEOUT = 3


def _utc_now():
    """When a message left, in UTC, Zulu notation: 2026-09-04T09:35:12.345Z.
    Read the same way whatever the timezone of who receives it."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _env():
    values = {}
    for line in (BASE_DIR / ".env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def _publishers():
    """The publishers package, imported the way main.py sees it: `publishers`
    is a top-level package from inside rabbit_bus/, and the caller's process
    knows nothing of that directory until told."""
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    import publishers

    return publishers


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


def _columns(subject):
    """A model instance as a plain dict of its columns, or None if it is not
    one. Handing a model to an attribute is the obvious way to say "carry the
    whole row", and stringifying it would answer "Folder object (3890)", which
    says nothing to whoever reads the message."""
    fields = getattr(getattr(subject, "_meta", None), "concrete_fields", None)
    if fields is None:
        return None
    return {field.attname: getattr(subject, field.attname, None) for field in fields}


def _jsonable(value):
    """Any value, made safe to send: a model instance becomes its columns, and
    anything else goes through json with str() as the fallback, which is what
    turns a date or a FieldFile into something a broker accepts."""
    columns = _columns(value)
    return json.loads(json.dumps(value if columns is None else columns, default=str))


def _extra(extra):
    """Free JSON. A string is taken as JSON already dumped and parsed back, so
    it travels as an object and not as text."""
    if extra is None:
        return {}
    if isinstance(extra, str):
        try:
            return json.loads(extra)
        except ValueError:
            return extra
    return _jsonable(extra)


class AmqpPublish:
    """An announcement being written, one attribute at a time.

        message = AmqpPublish("folder:POST")
        message.pk = 630
        message.extra = {"origine": "create_folder", "par": request.user.pk}
        message.files = []
        message.execute()

    `pk` is the only thing required: it names the row the announcement talks
    about, and without it nothing leaves. `extra` and `files` are optional and
    start empty.

    Any other attribute set here joins the envelope of the message under its
    own name, which is how this stays open without a new release of the bus
    every time a recipient wants one more field:

        message.source = "back-office"

    `args` is the one name that cannot be taken: it carries `pk` and `extra`,
    it is what every reader of the bus relies on, and it is rebuilt at
    publication time whatever a publisher returned."""

    RESERVED = ("namespace", "pk", "extra", "args")

    def __init__(self, namespace):
        self.namespace = namespace
        self.pk = None
        self.extra = None
        self.files = []

    def execute(self):
        """Run the publisher and send its message to every queue it declares.
        True when it left, False when it did not, and never an exception."""
        try:
            return self._execute()
        except Exception as error:
            logger.warning("emit namespace=%s failed (%s: %s)", self.namespace, type(error).__name__, error)
            return False

    def _attributes(self):
        """What the caller added, ready for the envelope. `files` is here too:
        it is a plain attribute that happens to exist by default."""
        return {
            name: _jsonable(value)
            for name, value in vars(self).items()
            if name not in self.RESERVED and not name.startswith("_")
        }

    def _execute(self):
        from kombu import Connection, Producer

        registry = _publishers()
        entry = registry.REGISTRY.get(self.namespace)
        if entry is None:
            logger.warning("emit namespace=%s unknown, nothing sent", self.namespace)
            return False

        pk = _pk(self.pk)
        if isinstance(pk, bool) or not isinstance(pk, (int, str)) or pk == "":
            logger.warning("emit namespace=%s has no pk, nothing sent", self.namespace)
            return False

        event = {"pk": pk, "extra": _extra(self.extra)}
        payload = registry.normalize(entry["run"](event), event)
        if not isinstance(payload, dict):
            payload = {"data": payload}
        payload.update(self._attributes())

        env = _env()
        inbox = f"{env['RABBITMQ_NAMESPACE']}.queue"
        correlation_id = str(uuid.uuid4())
        payload.setdefault("replyTo", inbox)
        payload.setdefault("correlationId", correlation_id)
        payload.setdefault("publishedAt", _utc_now())
        # Read last because it is the deepest: the envelope of the announcement
        # stays scannable above it.
        if "args" in payload:
            payload["args"] = payload.pop("args")

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
                logger.info("emitted namespace=%s queue=%s correlationId=%s", self.namespace, queue, correlation_id)
        return True


def emit(namespace, subject, extra=None):
    """The same announcement written in one line, for the calls that have
    nothing to customise. Kept because GP1 already speaks this form."""
    message = AmqpPublish(namespace)
    message.pk = subject
    message.extra = extra
    return message.execute()
