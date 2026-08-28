"""The full content of one app_folder row, by id, read through the
application's own ORM: {"numero": 4121} answers that folder's whole line."""

import logging

from consumers._django import json_safe, setup_django
from consumers._errors import NotFound

logger = logging.getLogger("bus.dossier_interne")

NAMESPACE = "dossier_interne"
ARGS = {"numero": 4121}


def run(args):
    numero = args.get("numero") if isinstance(args, dict) else None
    if numero is None:
        raise ValueError('expected an argument "numero", e.g. {"numero": 4121}')

    setup_django()
    from app.models import Folder

    row = Folder.objects.filter(pk=numero).values().first()
    if row is None:
        raise NotFound(f"dossier {numero} not found")

    dossier = json_safe(row)
    logger.info("dossier interne: id=%s (%d colonnes)", dossier.get("id"), len(dossier))
    return {"numero": dossier.get("id"), "dossier": dossier}
