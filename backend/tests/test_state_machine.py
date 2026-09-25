import itertools

import pytest

from app.domain import TRANSITIONS, InvalidTransitionError, Status, check_transition

VALID = {
    (Status.open, Status.in_progress),
    (Status.open, Status.rejected),
    (Status.in_progress, Status.resolved),
    (Status.in_progress, Status.rejected),
}


@pytest.mark.parametrize("cur,new", list(itertools.product(Status, Status)))
def test_every_pair_matches_the_spec(cur, new):
    if (cur, new) in VALID:
        check_transition(cur, new)
    else:
        with pytest.raises(InvalidTransitionError):
            check_transition(cur, new)


def test_terminal_states_have_no_exits():
    assert TRANSITIONS[Status.resolved] == frozenset() == TRANSITIONS[Status.rejected]


def test_error_message_names_the_attempted_transition():
    with pytest.raises(InvalidTransitionError) as exc:
        check_transition(Status.resolved, Status.open)
    assert str(exc.value) == "Invalid status transition: resolved -> open"
