"""What every announcement carries at the very least: the primary key of the
row it talks about, and whatever free JSON the caller chose to attach to it.

A publisher may know the whole row or only its key, and both are announcements;
what none of them may be is anonymous. A consumer holding its own copy of the
table needs to know WHICH row changed, and `id` is the only field that answers
that. So the identity is required and everything else is a bonus.

Accepted, from the richest form to the barest:

    {"folder": {"id": 630, "city": "..."}}   the row as written
    {"folder": 630}                          the key alone
    {"id": 630}                              the row, unwrapped
    630                                      the key alone, unwrapped

The key may be a number or a string, as the source database spells it. Missing
or empty, it raises ValueError, which the bus answers 400: an announcement
without identity names no row.

`extra` is the free part: any JSON the caller wants carried alongside the row,
under its own key so it can never be mistaken for a column of the table. It
travels untouched and stays `{}` when nobody sends anything.

Helpers start with "_" and are never registered as a namespace."""


def row_of(event, key):
    wrapped = isinstance(event, dict) and key in event
    subject = event[key] if wrapped else event
    if isinstance(subject, dict):
        row = dict(subject)
        if not wrapped:
            row.pop("extra", None)
    elif isinstance(subject, (int, str)) and not isinstance(subject, bool):
        row = {"id": subject}
    else:
        row = {}
    identifier = row.pop("pk", None) if row.get("id") is None else row.get("id")
    if identifier is None or identifier == "":
        raise ValueError(f'expected at least the row id, e.g. {{"{key}": {{"id": 630}}}}')
    row["id"] = identifier
    return row


def extra_of(event):
    value = event.get("extra") if isinstance(event, dict) else None
    return {} if value is None else value
