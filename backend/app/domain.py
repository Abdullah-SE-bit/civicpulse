from enum import StrEnum


class Category(StrEnum):
    water = "water"
    electricity = "electricity"
    sanitation = "sanitation"
    roads = "roads"
    streetlights = "streetlights"
    other = "other"


class Priority(StrEnum):
    high = "high"
    normal = "normal"
    low = "low"


class Status(StrEnum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    rejected = "rejected"


TRANSITIONS: dict[Status, frozenset[Status]] = {
    Status.open: frozenset({Status.in_progress, Status.rejected}),
    Status.in_progress: frozenset({Status.resolved, Status.rejected}),
    Status.resolved: frozenset(),
    Status.rejected: frozenset(),
}


class InvalidTransitionError(Exception):
    def __init__(self, current: Status, target: Status) -> None:
        self.current, self.target = current, target
        super().__init__(f"Invalid status transition: {current.value} -> {target.value}")


def check_transition(current: Status, target: Status) -> None:
    if target not in TRANSITIONS[current]:
        raise InvalidTransitionError(current, target)
