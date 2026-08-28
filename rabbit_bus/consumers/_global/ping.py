import time

NAMESPACE = "ping"


def run(args):
    return {"pong": True, "at": int(time.time() * 1000), "args_recus": args}
