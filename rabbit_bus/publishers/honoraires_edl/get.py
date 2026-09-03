"""honoraires_edl:GET announcement, not implemented yet."""

NAMESPACE = "honoraires_edl:GET"
QUEUES = [
    "gp1-data-provider.queue",
    "test.queue",
    "gp1-test.witness-1.queue",
    "gp1-test.witness-2.queue",
    "gp1-test.witness-3.queue",
]
ARGS = {"pk": 425, "extra": {}}


def run(event):
    raise NotImplementedError("honoraires_edl:GET announcement is not implemented yet")
