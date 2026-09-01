"""rendu_dg:POST announcement, not implemented yet."""

NAMESPACE = "rendu_dg:POST"
QUEUES = ["gp1-data-provider.queue", "test.queue"]
ARGS = {"rendu_dg": {"id": 1}}


def run(event):
    raise NotImplementedError("rendu_dg:POST announcement is not implemented yet")
