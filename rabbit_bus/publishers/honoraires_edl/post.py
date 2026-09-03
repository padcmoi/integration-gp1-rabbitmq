"""honoraires_edl:POST announcement, not implemented yet."""

NAMESPACE = "honoraires_edl:POST"
QUEUES = ["gp1-data-provider.queue", "test.queue"]
ARGS = {"pk": 425, "extra": {}}


def run(event):
    raise NotImplementedError("honoraires_edl:POST announcement is not implemented yet")
