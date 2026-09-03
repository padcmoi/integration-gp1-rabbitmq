"""rendu_dg:PUT announcement, not implemented yet."""

NAMESPACE = "rendu_dg:PUT"
QUEUES = ["gp1-data-provider.queue", "test.queue"]
ARGS = {"pk": 1, "extra": {}}


def run(event):
    raise NotImplementedError("rendu_dg:PUT announcement is not implemented yet")
