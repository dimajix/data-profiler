"""Tests of the layout of a diagram: where a table and the tables connected to it lie."""

from itertools import combinations

import pytest

from data_profiler.diagram import Box, lay_out

_MANY = {f"t{place:02}": False for place in range(22)}


def test_the_tables_that_refer_lie_on_the_left_and_those_referred_to_on_the_right() -> None:
    diagram = lay_out("c", {"a": False}, {"b": False}, None)
    (coming, going) = diagram.boxes
    assert (coming.text, going.text) == ("a", "b")
    assert coming.right < diagram.centre.x
    assert diagram.centre.right < going.x


def test_a_table_no_table_refers_to_stands_at_the_left_edge() -> None:
    assert lay_out("c", {}, {"b": False}, None).centre.x == 0


def test_the_boxes_lie_within_the_drawing_and_on_none_other() -> None:
    diagram = lay_out("c", {f"a{place}": False for place in range(5)}, {"b": False}, False)
    boxes = (diagram.centre, *diagram.boxes)
    assert all(box.x >= 0 and box.right <= diagram.width for box in boxes)
    assert all(box.y >= 0 and box.y + box.height <= diagram.height for box in boxes)

    def apart(one: Box, other: Box) -> bool:
        beside = one.right <= other.x or other.right <= one.x
        return beside or one.y + one.height <= other.y or other.y + other.height <= one.y

    assert all(apart(one, other) for one, other in combinations(boxes, 2))


def test_the_boxes_of_a_side_are_as_wide_as_its_longest_name_needs() -> None:
    long = "a_rather_long_name_of_a_table"
    (one, other) = lay_out("c", {long: False, "a": False}, {}, None).boxes
    assert one.width == other.width
    assert one.width > 7 * len(long), "a character of the font is about 7 wide"


def test_a_line_is_dashed_where_its_table_is_connected_by_candidates_alone() -> None:
    lines = lay_out("c", {"a": True}, {"b": False}, None).lines
    assert [line.dashed for line in lines] == [True, False]


@pytest.mark.parametrize("dashed", [False, True])
def test_a_table_connected_to_itself_has_a_loop_and_room_for_it(dashed: bool) -> None:
    plain = lay_out("c", {"a": False}, {}, None)
    looped = lay_out("c", {"a": False}, {}, dashed)
    assert len(looped.lines) == 2
    assert looped.lines[-1].dashed == dashed
    assert looped.height > plain.height
    assert looped.centre.y > plain.centre.y


def test_a_diagram_of_a_table_connected_to_itself_alone_has_its_box_and_its_loop() -> None:
    diagram = lay_out("c", {}, {}, False)
    assert diagram.boxes == ()
    assert len(diagram.lines) == 1


@pytest.mark.parametrize(("coming", "going"), [(_MANY, {}), ({}, _MANY)])
def test_a_side_shows_twenty_tables_and_the_number_of_the_others(
    coming: dict[str, bool], going: dict[str, bool]
) -> None:
    diagram = lay_out("c", coming, going, None)
    assert [box.text for box in diagram.boxes] == list(_MANY)[:20]
    assert [box.text for box in diagram.more] == ["+ 2 more"]
    assert len(diagram.lines) == 20, "none to the number of the others"


def test_a_side_of_twenty_tables_says_nothing_of_others() -> None:
    twenty = dict(list(_MANY.items())[:20])
    assert lay_out("c", twenty, {}, None).more == ()
