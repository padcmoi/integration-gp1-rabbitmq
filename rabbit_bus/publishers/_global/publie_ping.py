"""Minimal publisher: one queue, a static payload.

Send {"namespace": "publie_ping"} to the bus and test.queue receives the pong;
the caller is answered 202 with the queues and the correlationId. The pair
with publie_exemple mirrors ping / fais_moi_le_cafe on the consumer side:
the minimal shape, then the one that carries args."""

import time

NAMESPACE = "publie_ping"
QUEUES = ["test.queue"]


def run(args):
    return {"pong": True, "at": int(time.time() * 1000)}
