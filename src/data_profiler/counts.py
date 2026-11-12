"""Counts of the database, as the tool takes them: as numbers.

A count is what a query has counted, and is a number where the dialect that wrote the query made
sure of it.
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
