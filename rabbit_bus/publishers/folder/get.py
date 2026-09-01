"""folder:GET announcement, not implemented yet."""

NAMESPACE = "folder:GET"
QUEUES = ["gp1-data-provider.queue", "test.queue"]
ARGS = {"folder": {"id": 630}}


def run(event):
    raise NotImplementedError("folder:GET announcement is not implemented yet")
