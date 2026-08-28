"""Business logic of honoraires_edl, one concern per module.

WRITABLE_FIELDS is the whole write contract of PATCH: a field absent here is
not writable over the bus, a field present is checked by its validator.
Adding a writable field is one line here (plus its rule module if it has one).
"""

from consumers.honoraires_edl.business.steps import validate_step

WRITABLE_FIELDS = {
    "step": validate_step,
}


def validate_patch(patch):
    errors = []
    for name, value in patch.items():
        validator = WRITABLE_FIELDS.get(name)
        if validator is None:
            errors.append(f"{name}: field not writable")
            continue
        try:
            validator(value)
        except ValueError as error:
            errors.append(str(error))
    if errors:
        raise ValueError("; ".join(errors))
