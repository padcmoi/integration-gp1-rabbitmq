"""folder:PUT announcement, not implemented yet."""

NAMESPACE = "folder:PUT"
QUEUES = ["gp1-data-provider.queue", "test.queue"]
ARGS = {"folder": {"id": 630}}


def run(event):
    raise NotImplementedError("folder:PUT announcement is not implemented yet")
