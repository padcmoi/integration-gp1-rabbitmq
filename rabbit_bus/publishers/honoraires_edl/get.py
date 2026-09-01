"""honoraires_edl:GET announcement, not implemented yet."""

NAMESPACE = "honoraires_edl:GET"
QUEUES = ["gp1-data-provider.queue", "test.queue"]
ARGS = {"honoraires_edl": {"id": 425}}


def run(event):
    raise NotImplementedError("honoraires_edl:GET announcement is not implemented yet")
