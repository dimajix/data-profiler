"""Values of the database, as the tool takes them: a count as a number, any value as text.

A value comes from a query, or from a sample of the workspace, which a query took. A count is what
a query has counted, and is a number where the dialect that wrote the query made sure of it. A
value is held in the profile, and shown, as text, as the database writes it: a truth value as
`true` or `false`, any other as Python writes it.
"""


def counted(value: object, where: str) -> int:
    """`value`, which a query has counted of `where`, as a number.

    Raises:
        TypeError: The value is no number, which the dialect that wrote the query would have to
            make sure of.
    """
    if not isinstance(value, int):
        raise TypeError(f"the query counted something of {where} that is no number")
    return value


def as_text(value: object) -> str:
    """`value`, which a query has read of the database, as text, as the database writes it.

    A truth value is written `true` or `false`; any other, as Python writes it.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
