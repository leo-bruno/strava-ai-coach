"""Shared arithmetic for percentage changes of nonnegative volume values."""


def _percentage_change(previous_value: int | float, current_value: int | float) -> float | None:
    """Return an unrounded percentage; None means the base is zero.

    A result of 10.0 means 10 percent, not a fraction of 0.10.
    """
    if previous_value == 0:
        return None
    return 100 * (current_value - previous_value) / previous_value
