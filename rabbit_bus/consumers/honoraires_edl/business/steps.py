"""The step system of honoraires EDL: which values exist and what they mean."""

ALLOWED_STEPS = (1, 3, 4, 7)


def validate_step(value):
    if isinstance(value, bool) or not isinstance(value, int) or value not in ALLOWED_STEPS:
        raise ValueError(f"step: value {value!r} refused, expected {', '.join(map(str, ALLOWED_STEPS))}")
