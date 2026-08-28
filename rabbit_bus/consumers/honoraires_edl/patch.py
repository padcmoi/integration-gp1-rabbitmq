"""honoraires_edl:PATCH writes the given fields of one row:
{"pk": 425, "data": {"step": 4}}.

Thin on purpose: what may change and what a value may be lives in business/.
The write goes through the model instance, full_clean() on the patched fields,
then save(), so the application's own declared rules apply as well."""

import logging

from consumers._django import json_safe, setup_django
from consumers._errors import Conflict, NotFound
from consumers.honoraires_edl.business import validate_patch

logger = logging.getLogger("bus.honoraires_edl.patch")

NAMESPACE = "honoraires_edl:PATCH"
ARGS = {"pk": 425, "data": {"step": 4}}


def run(args):
    pk = args.get("pk") if isinstance(args, dict) else None
    data = args.get("data") if isinstance(args, dict) else None
    if pk is None or not isinstance(data, dict) or not data:
        raise ValueError('expected {"pk": 425, "data": {"field": "value"}}')

    validate_patch(data)

    setup_django()
    from app.models import HonorairesEDL

    instance = HonorairesEDL.objects.filter(pk=pk).first()
    if instance is None:
        raise NotFound(f"honoraires_edl {pk} not found")

    unchanged = [name for name in data if getattr(instance, name) == data[name]]
    if unchanged:
        raise Conflict("; ".join(f"{name}: already {getattr(instance, name)!r}" for name in unchanged))

    for name, value in data.items():
        setattr(instance, name, value)
    untouched = [field.name for field in HonorairesEDL._meta.concrete_fields if field.attname not in data]
    instance.full_clean(exclude=untouched, validate_unique=False)
    instance.save(update_fields=list(data))

    row = json_safe(HonorairesEDL.objects.filter(pk=pk).values().first())
    logger.info("honoraires_edl PATCH: id=%s fields=%s", pk, sorted(data))
    return {"id": row.get("id"), "patched": sorted(data), "honoraires_edl": row}
