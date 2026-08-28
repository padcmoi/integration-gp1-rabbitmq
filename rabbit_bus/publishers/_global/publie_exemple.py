import logging
import time

logger = logging.getLogger("bus.publie_exemple")

NAMESPACE = "publie_exemple"

# 1..N destination queues, direct mode: the message is addressed to each queue
# by its exact name, nothing else receives it. The bus stamps replyTo and
# correlationId on the way out, so these queues can answer; answers come back
# on gp1-test.queue and are written to publish.txt.
QUEUES = ["test.queue"]


def run(args):
    logger.info("args: %r", args)
    return {"de": "gp1_test", "exemple": True, "envoye_a": int(time.time() * 1000), "args_recus": args}
