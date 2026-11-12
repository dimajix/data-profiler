"""The layout of a table and the tables connected to it, in pixels, for a drawing.

The table stands in the centre, the tables that refer to it on its left and those it refers to on
its right, a table of both on each, and a table connected to itself has a loop on its box. A line
is dashed where its table is connected by reference candidates alone. It computes where things lie
and writes nothing: whoever draws the layout escapes the names in it.
"""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

# The tables shown on one side of a diagram, before the number of the others: the tables of the
# report list every reference. They are cut here, not by `report.html` as the values of a column
# are, as the width of a side depends on what the number says.
_BOXES: Final = 20

# The measures of a diagram, in pixels. A name is in a font of fixed width, 12 pixels high, whose
# characters are about 7 wide, so that a box is wide enough for it without a browser to measure it.
_CHARACTER: Final = 8
_PADDING: Final = 10
_HEIGHT: Final = 28
_GAP: Final = 10
_SPAN: Final = 90
# The length and the half of the width of the head of an arrow.
_HEAD_LENGTH: Final = 8
_HEAD_HALF: Final = 4
# The room above the box of a table connected to itself, the half of the width of its loop, and how
# far the control points of the loop rise, of which the curve reaches three quarters.
_LOOP_ROOM: Final = 30
_LOOP_HALF: Final = 16
_LOOP_RISE: Final = 26


@dataclass(frozen=True)
class Box:
    """A box of a diagram, with what it says.

    Attributes:
        text: What it says.
        x: Its left edge.
        y: Its top edge.
        width: Its width.
    """

    text: str
    x: int
    y: int
    width: int

    @property
    def height(self) -> int:
        """Its height, of every box the same."""
        return _HEIGHT

    @property
    def right(self) -> int:
        """Its right edge."""
        return self.x + self.width

    @property
    def centre(self) -> int:
        """The middle of its width."""
        return self.x + self.width // 2

    @property
    def middle(self) -> int:
        """The middle of its height."""
        return self.y + _HEIGHT // 2


@dataclass(frozen=True)
class Line:
    """An arrow of a diagram.

    Attributes:
        path: The path of the line.
        head: The path of its head.
        dashed: Whether it stands for reference candidates alone.
    """

    path: str
    head: str
    dashed: bool


@dataclass(frozen=True)
class Diagram:
    """The tables connected to one table, drawn with it in the centre.

    Attributes:
        width: The width of the drawing.
        height: The height of the drawing.
        centre: The box of the table.
        boxes: The boxes of the tables connected to it, each with a section of the report.
        more: The boxes that say how many tables of a side are not shown, one of each such side.
        lines: The arrows: from the tables that refer, to the tables referred to, and the loop of a
            table connected to itself.
    """

    width: int
    height: int
    centre: Box
    boxes: tuple[Box, ...]
    more: tuple[Box, ...]
    lines: tuple[Line, ...]


def lay_out(
    name: str, coming: Mapping[str, bool], going: Mapping[str, bool], itself: bool | None
) -> Diagram:
    """The diagram of the table `name` and the tables connected to it.

    Args:
        name: The name of the table in the centre.
        coming: The tables that refer to it, each with whether by reference candidates alone.
        going: The tables it refers to, each with whether by reference candidates alone.
        itself: Whether it is connected to itself by reference candidates alone, or None where it
            is not connected to itself.

    Returns:
        The diagram, the tables of a side in the order given.
    """
    top = 0 if itself is None else _LOOP_ROOM
    body = _extent(max(_rows(coming), _rows(going), 1))
    lefts, more_left = _side(list(coming), 0, top, body)
    (centre,) = _column([name], lefts[0].right + _SPAN if lefts else 0, top, body)
    rights, more_right = _side(list(going), centre.right + _SPAN, top, body)
    lines = [
        *(
            _arrow((box.right, box.middle), (centre.x, centre.middle), dashed=coming[box.text])
            for box in lefts
        ),
        *(
            _arrow((centre.right, centre.middle), (box.x, box.middle), dashed=going[box.text])
            for box in rights
        ),
        *(() if itself is None else (_loop(centre, dashed=itself),)),
    ]
    return Diagram(
        width=max(box.right for box in (*lefts, centre, *rights)),
        height=top + body,
        centre=centre,
        boxes=(*lefts, *rights),
        more=(*more_left, *more_right),
        lines=tuple(lines),
    )


def _rows(connected: Collection[str]) -> int:
    """How many boxes a side of `connected` has: the tables shown, and one for the others."""
    return min(len(connected), _BOXES + 1)


def _side(names: Sequence[str], x: int, top: int, height: int) -> tuple[list[Box], list[Box]]:
    """The boxes of the first `_BOXES` of `names`, and the one of how many others there are, if any.

    Args:
        names: The names of the tables of the side.
        x: The left edge of the side.
        top: The top of the drawing below the room of a loop.
        height: The height the boxes are centred in.

    Returns:
        The boxes of the tables shown, and a list of the box of the number of the others, or none.
    """
    others = len(names) - _BOXES
    number = [f"+ {others} more"] if others > 0 else []
    boxes = _column([*names[:_BOXES], *number], x, top, height)
    return boxes[:_BOXES], boxes[_BOXES:]


def _extent(boxes: int) -> int:
    """The height of `boxes` boxes one below the other."""
    return boxes * _HEIGHT + (boxes - 1) * _GAP


def _column(texts: Sequence[str], x: int, top: int, height: int) -> list[Box]:
    """Boxes of `texts` of one width at `x`, one below the other, centred in `height` from `top`."""
    width = max((len(text) for text in texts), default=0) * _CHARACTER + 2 * _PADDING
    first = top + (height - _extent(len(texts))) // 2
    return [
        Box(text, x, first + place * (_HEIGHT + _GAP), width) for place, text in enumerate(texts)
    ]


def _arrow(start: tuple[int, int], end: tuple[int, int], *, dashed: bool) -> Line:
    """An arrow from `start`, to the right, to `end`, curving between them."""
    (x1, y1), (x2, y2) = start, end
    half = (x1 + x2) // 2
    path = f"M {x1} {y1} C {half} {y1}, {half} {y2}, {x2} {y2}"
    back = x2 - _HEAD_LENGTH
    head = f"M {back} {y2 - _HEAD_HALF} L {x2} {y2} L {back} {y2 + _HEAD_HALF} Z"
    return Line(path, head, dashed)


def _loop(box: Box, *, dashed: bool) -> Line:
    """An arrow from the top of `box` back to it."""
    left, right, top = box.centre - _LOOP_HALF, box.centre + _LOOP_HALF, box.y
    rise = top - _LOOP_RISE
    path = f"M {left} {top} C {left} {rise}, {right} {rise}, {right} {top}"
    back = top - _HEAD_LENGTH
    head = f"M {right - _HEAD_HALF} {back} L {right} {top} L {right + _HEAD_HALF} {back} Z"
    return Line(path, head, dashed)
