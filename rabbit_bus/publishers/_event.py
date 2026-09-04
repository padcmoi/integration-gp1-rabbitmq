"""What an announcement carries: two keys, and only two.

    {"pk": 207, "extra": {}}

`pk` is the primary key of the row the announcement talks about. It is the
whole point: a consumer needs to know WHICH row changed, and reads the row from
the source when it wants its content. A table has three hundred columns, they
change without asking us, and copying them into every message would make the
announcement a second, slower, always slightly wrong version of the database.

`extra` is the deliberate part: any JSON the caller chose to attach, carried
under its own key, never mixed with the identity. What is not the key goes
there or does not travel.

`pk` may be a number or a string, as the source database spells it, and `id` is
accepted as its alias, which is how a mirror publisher reads the result of its
consumer. Missing or empty, it raises ValueError, which the bus answers 400: an
announcement without identity names no row.

Helpers start with "_" and are never registered as a namespace."""


def pk_of(event):
    if isinstance(event, dict):
        value = event.get("pk") if event.get("pk") is not None else event.get("id")
    else:
        value = event
    if isinstance(value, bool) or not isinstance(value, (int, str)) or value == "":
        raise ValueError('expected args {"pk": 630}')
    return value


def extra_of(event):
    value = event.get("extra") if isinstance(event, dict) else None
    return {} if value is None else value


def write_event(event, method, table, files=None):
    """The one shape an announcement takes. A verb file says which method and
    which table, and nothing else about the message: the shape is not its
    business, and a shape decided in fifteen places drifts in fifteen ways."""
    return {
        "method": method,
        "table": table,
        "persist": False,
        "args": {"pk": pk_of(event), "extra": extra_of(event)},
        "files": list(files or []),
    }


def normalize(payload, event):
    """Force what a publisher returned into that shape, at publication time.

    Whoever writes a verb file can forget the contract, return a stray key or
    build `args` by hand; the message that leaves carries the five keys and no
    others. That is what makes the format a guarantee for the reader rather
    than a convention the sender is asked to respect.

    A payload naming no table announces no write: the free publishers of
    `_global` are exactly that, and they pass through untouched."""
    if not isinstance(payload, dict) or not payload.get("table"):
        return payload
    given = payload.get("args") if isinstance(payload.get("args"), dict) else {}
    pk = given.get("pk")
    extra = given.get("extra")
    return {
        "method": payload.get("method", ""),
        "table": payload["table"],
        "persist": bool(payload.get("persist", False)),
        "args": {
            "pk": pk_of(event) if pk is None else pk,
            "extra": extra_of(event) if extra is None else extra,
        },
        "files": list(payload.get("files") or []),
    }
