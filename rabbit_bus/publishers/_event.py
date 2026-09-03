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
