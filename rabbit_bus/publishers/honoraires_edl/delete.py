"""honoraires_edl:DELETE announcement, not implemented yet."""

NAMESPACE = "honoraires_edl:DELETE"
QUEUES = ["gp1-data-provider.queue", "test.queue"]
ARGS = {"pk": 425, "extra": {}}


def run(event):
    raise NotImplementedError("honoraires_edl:DELETE announcement is not implemented yet")
