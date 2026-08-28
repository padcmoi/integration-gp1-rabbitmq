"""One random app_folder row, read through the application's own ORM."""

import logging

from consumers._django import json_safe, setup_django

logger = logging.getLogger("bus.dossier_aleatoire")

NAMESPACE = "dossier_aleatoire"


def run(args):
    setup_django()
    from app.models import Folder

    row = Folder.objects.order_by("?").values().first()
    if row is None:
        return {"numero": None, "dossier": None, "error": "app_folder is empty"}
    dossier = json_safe(row)
    logger.info("dossier aleatoire: id=%s (%d colonnes)", dossier.get("id"), len(dossier))
    return {"numero": dossier.get("id"), "dossier": dossier}
