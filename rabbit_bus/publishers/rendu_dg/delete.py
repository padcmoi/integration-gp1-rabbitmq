"""rendu_dg:DELETE announcement, not implemented yet."""

NAMESPACE = "rendu_dg:DELETE"
QUEUES = [
    "gp1-data-provider.queue",
    "test.queue",
    "gp1-test.witness-1.queue",
    "gp1-test.witness-2.queue",
    "gp1-test.witness-3.queue",
]
ARGS = {"pk": 1, "extra": {}}


def run(event):
    raise NotImplementedError("rendu_dg:DELETE announcement is not implemented yet")
