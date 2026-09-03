"""rendu_dg:DELETE announcement, not implemented yet."""

NAMESPACE = "rendu_dg:DELETE"
QUEUES = ["gp1-data-provider.queue", "test.queue"]
ARGS = {"pk": 1, "extra": {}}


def run(event):
    raise NotImplementedError("rendu_dg:DELETE announcement is not implemented yet")
