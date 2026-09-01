"""folder:DELETE announcement, not implemented yet."""

NAMESPACE = "folder:DELETE"
QUEUES = ["gp1-data-provider.queue", "test.queue"]
ARGS = {"folder": {"id": 630}}


def run(event):
    raise NotImplementedError("folder:DELETE announcement is not implemented yet")
