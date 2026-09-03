"""honoraires_edl:PUT announcement, not implemented yet."""

NAMESPACE = "honoraires_edl:PUT"
QUEUES = ["gp1-data-provider.queue", "test.queue"]
ARGS = {"pk": 425, "extra": {}}


def run(event):
    raise NotImplementedError("honoraires_edl:PUT announcement is not implemented yet")
