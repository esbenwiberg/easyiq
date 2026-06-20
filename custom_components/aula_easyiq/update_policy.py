"""Update interval policy helpers for the EasyIQ coordinator."""
from __future__ import annotations

from datetime import datetime
from typing import Mapping


def should_update_data_type(
    data_type: str,
    update_intervals: Mapping[str, int],
    last_updates: Mapping[str, datetime | None],
    now: datetime | None = None,
) -> bool:
    """Return whether a data type is due for refresh."""
    if data_type not in update_intervals:
        return True

    last_update = last_updates.get(data_type)
    if last_update is None:
        return True

    interval = update_intervals[data_type]
    if interval <= 0:
        return True

    current_time = now or datetime.now()
    return (current_time - last_update).total_seconds() >= interval
