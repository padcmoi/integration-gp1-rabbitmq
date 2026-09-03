"""folder:PUT announcement, not implemented yet."""

NAMESPACE = "folder:PUT"
QUEUES = ["gp1-data-provider.queue", "test.queue"]
ARGS = {"pk": 630, "extra": {}}


def run(event):
    raise NotImplementedError("folder:PUT announcement is not implemented yet")
