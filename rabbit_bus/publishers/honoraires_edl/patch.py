"""Mirror of consumers/honoraires_edl/patch.py: a field written by the bus is
announced to whoever holds a copy or a cache of the table.

The message is the ecosystem's write-event contract ({method, table, persist,
data, files}). The data-provider consuming it on gp1-data-provider.queue reads
`table` and purges that table's cache, so its API keys stop serving rows this
write just made stale; test.queue receives the same event for the test app."""

from publishers._event import extra_of, pk_of

NAMESPACE = "honoraires_edl:PATCH"

QUEUES = [
    "gp1-data-provider.queue",
    "test.queue",
    "gp1-test.witness-1.queue",
    "gp1-test.witness-2.queue",
    "gp1-test.witness-3.queue",
]

ARGS = {"pk": 425, "extra": {}}


def run(event):
    return {
        "method": "PATCH",
        "table": "app_honorairesedl",
        "persist": False,
        "args": {"pk": pk_of(event), "extra": extra_of(event)},
        "files": [],
    }
