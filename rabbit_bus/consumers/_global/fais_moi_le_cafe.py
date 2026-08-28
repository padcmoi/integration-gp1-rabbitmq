import logging

logger = logging.getLogger("bus.fais_moi_le_cafe")

NAMESPACE = "fais_moi_le_cafe"
ARGS = {"sucre": 2}


def run(args):
    logger.info("args: %r", args)
    return {"cafe": "pret", "args_recus": args}
