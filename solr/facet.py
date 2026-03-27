"""Facet builder for Solr traditional faceting parameters.

Provides a structured way to build facet.field, facet.range,
facet.query, and facet.pivot parameters.
"""
from __future__ import annotations

from typing import Any


class Facet:
    """Builder for traditional Solr facet parameters.

    Use the class methods to create specific facet types.
    Each facet converts to Solr query parameters via ``to_params()``.

    Example::

        from solr import Facet

        facets = [
            Facet.field('category', mincount=1, limit=10),
            Facet.range('price', start=0, end=100, gap=10),
            Facet.query('cheap', 'price:[0 TO 50]'),
            Facet.pivot('category', 'author'),
        ]
    """

    def __init__(self, params: dict[str, Any]) -> None:
        """Create a facet from raw parameters. Use class methods instead."""
        self._params = params

    def to_params(self) -> dict[str, str]:
        """Convert to Solr query parameter dict."""
        return dict(self._params)

    @classmethod
    def field(cls, name: str, **opts: Any) -> Facet:
        """Create a field facet.

        :param name: Field name to facet on.
        :param opts: Per-field options (mincount, limit, sort, prefix,
            missing, offset, etc.).
        :returns: A Facet object.
        """
        params: dict[str, str] = {
            'facet': 'true',
            'facet.field': name,
        }
        for key, value in opts.items():
            params['f.%s.facet.%s' % (name, key)] = str(value)
        return cls(params)

    @classmethod
    def range(cls, name: str, start: Any, end: Any, gap: Any,
              **opts: Any) -> Facet:
        """Create a range facet.

        :param name: Field name to facet on.
        :param start: Range start value.
        :param end: Range end value.
        :param gap: Range gap (interval size).
        :param opts: Additional options (hardend, include, etc.).
        :returns: A Facet object.
        """
        params: dict[str, str] = {
            'facet': 'true',
            'facet.range': name,
            'f.%s.facet.range.start' % name: str(start),
            'f.%s.facet.range.end' % name: str(end),
            'f.%s.facet.range.gap' % name: str(gap),
        }
        for key, value in opts.items():
            params['f.%s.facet.range.%s' % (name, key)] = str(value)
        return cls(params)

    @classmethod
    def query(cls, name: str, q: str) -> Facet:
        """Create a query facet.

        :param name: Label for this facet query.
        :param q: Solr query string for this facet.
        :returns: A Facet object.
        """
        return cls({
            'facet': 'true',
            'facet.query': q,
        })

    @classmethod
    def pivot(cls, *fields: str, mincount: int | None = None) -> Facet:
        """Create a pivot facet.

        :param fields: Two or more field names to pivot on.
        :param mincount: Minimum count threshold.
        :returns: A Facet object.
        """
        params: dict[str, str] = {
            'facet': 'true',
            'facet.pivot': ','.join(fields),
        }
        if mincount is not None:
            params['facet.pivot.mincount'] = str(mincount)
        return cls(params)
