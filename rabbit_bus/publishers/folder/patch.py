"""folder:PATCH announcement, not implemented yet."""

NAMESPACE = "folder:PATCH"
QUEUES = ["gp1-data-provider.queue", "test.queue"]
ARGS = {"folder": {"id": 630}}


def run(event):
    raise NotImplementedError("folder:PATCH announcement is not implemented yet")
