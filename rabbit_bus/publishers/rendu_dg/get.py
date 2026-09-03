"""rendu_dg:GET announcement, not implemented yet."""

NAMESPACE = "rendu_dg:GET"
QUEUES = ["gp1-data-provider.queue", "test.queue"]
ARGS = {"pk": 1, "extra": {}}


def run(event):
    raise NotImplementedError("rendu_dg:GET announcement is not implemented yet")
