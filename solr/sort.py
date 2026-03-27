"""Sort builder for Solr sort parameter.

Provides a structured way to build sort clauses including
field sorts and function sorts.
"""
from __future__ import annotations


class Sort:
    """A single sort clause for the ``sort`` parameter.

    Example::

        from solr import Sort

        sort = [
            Sort('category', 'asc'),
            Sort('price', 'desc'),
            Sort.func('geodist()', 'asc'),
        ]
    """

    def __init__(self, field: str, direction: str = 'asc') -> None:
        """Create a sort clause.

        :param field: Field name to sort by.
        :param direction: Sort direction (``'asc'`` or ``'desc'``).
        """
        self._field = field
        self._direction = direction

    def __str__(self) -> str:
        """Convert to Solr sort string."""
        return '%s %s' % (self._field, self._direction)

    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        return "Sort(%r, %r)" % (self._field, self._direction)

    @classmethod
    def func(cls, expr: str, direction: str = 'asc') -> Sort:
        """Create a function-based sort clause.

        :param expr: Function expression (e.g. ``'geodist()'``).
        :param direction: Sort direction (``'asc'`` or ``'desc'``).
        """
        return cls(expr, direction)
