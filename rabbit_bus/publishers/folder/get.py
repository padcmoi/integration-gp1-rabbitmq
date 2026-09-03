"""folder:GET announcement, not implemented yet."""

NAMESPACE = "folder:GET"
QUEUES = ["gp1-data-provider.queue", "test.queue"]
ARGS = {"pk": 630, "extra": {}}


def run(event):
    raise NotImplementedError("folder:GET announcement is not implemented yet")
