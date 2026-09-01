"""The etat des lieux de sortie has been deposited, announced to whoever holds
a copy or a cache of the table.

In GP1 the EDL de sortie is a field, not a record: `edl_sortie` on the DG model
(app/models.py, table app_dg), filled at step 3 of edit_rendu_dg together with
the EDL d'entree, then saved on the DG row (app/views.py, the only live write
of that field in the whole application). The folder name and the namespace take
GP1's own route slug, /rendu_dg/<pk>, and the verb is PATCH because the row
already exists: what happens is one field being filled.

app_folder carries an `edl_sortie` column too, but nothing writes it any more:
the copy onto the folder is commented out in the same view. The DG row is the
truth today, so it is what this announcement describes.

The document itself travels as the storage path already held by the row, the
way the honoraires_edl announcement carries its `facture` path; `files` stays
empty because a file reference in this contract needs a URL pointing at whoever
serves the document, and the bus serves none.

The message is the ecosystem's write-event contract ({method, table, persist,
data, files}). The data-provider consuming it on gp1-data-provider.queue reads
`table` and purges that table's cache; test.queue receives the same event for
the test app."""

from publishers._event import extra_of, row_of

NAMESPACE = "rendu_dg:PATCH"

QUEUES = ["gp1-data-provider.queue", "test.queue"]

ARGS = {"rendu_dg": {"id": 1}}


def run(event):
    return {
        "method": "PATCH",
        "table": "app_dg",
        "persist": False,
        "data": [row_of(event, "rendu_dg")],
        "files": [],
        "extra": extra_of(event),
    }
