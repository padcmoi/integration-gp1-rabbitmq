"""A dossier proprietaire has been created, announced to whoever holds a copy
or a cache of the table.

The dossier proprietaire is GP1's Folder (app/models.py, table app_folder):
the owner is carried by the row itself (owner_last_name, owner_first_name,
owner_email) and by its `owner` foreign key to authentication.Owner. The folder
name and the namespace take GP1's own route slug, /folder/<pk>.

GP1 creates a Folder from about twenty call sites in app/form.py, never from a
view; announcing from each of them would mean twenty places to keep in sync,
which is why the application developer points at the model instead, right after
Folder.save() (app/models.py, the save() override): one place that no creation
path can bypass.

The message is the ecosystem's write-event contract ({method, table, persist,
data, files}), where `data` holds the key of the created folder and nothing
else. The data-provider consuming it on gp1-data-provider.queue reads `table`
and purges that table's cache, so its API keys stop serving a folder list this
creation just made stale; test.queue receives the same event for the test app."""

from publishers._event import extra_of, pk_of

NAMESPACE = "folder:POST"

QUEUES = [
    "gp1-data-provider.queue",
    "test.queue",
    "gp1-test.witness-1.queue",
    "gp1-test.witness-2.queue",
    "gp1-test.witness-3.queue",
]

ARGS = {"pk": 630, "extra": {}}


def run(event):
    return {
        "method": "POST",
        "table": "app_folder",
        "persist": False,
        "data": [{"id": pk_of(event)}],
        "files": [],
        "extra": extra_of(event),
    }
