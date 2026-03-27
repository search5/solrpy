"""Field builder for Solr fl (field list) parameter.

Provides a structured way to build field list expressions including
aliases, functions, document transformers, and score.
"""
from __future__ import annotations

from typing import Any


class Field:
    """A single field expression for the ``fl`` parameter.

    Supports simple fields, aliases, functions, and document transformers.

    Example::

        from solr import Field

        fields = [
            Field('id'),
            Field('price', alias='price_usd'),   # → price_usd:price
            Field.func('sum', 'price', 'tax'),    # → sum(price,tax)
            Field.transformer('explain'),          # → [explain]
            Field.score(),                         # → score
        ]
    """

    def __init__(self, name: str, alias: str | None = None) -> None:
        """Create a simple field, optionally with an alias.

        :param name: Solr field name.
        :param alias: Return alias (``alias:name`` in Solr fl syntax).
        """
        self._name = name
        self._alias = alias

    def __str__(self) -> str:
        """Convert to Solr fl string."""
        if self._alias:
            return '%s:%s' % (self._alias, self._name)
        return self._name

    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        if self._alias:
            return "Field(%r, alias=%r)" % (self._name, self._alias)
        return "Field(%r)" % self._name

    @classmethod
    def func(cls, name: str, *args: str) -> Field:
        """Create a function field expression.

        :param name: Function name (e.g. ``'sum'``, ``'geodist'``).
        :param args: Function arguments (field names or literals).
        :returns: A Field that renders as ``name(arg1,arg2,...)``.
        """
        expr = '%s(%s)' % (name, ','.join(args))
        return cls(expr)

    @classmethod
    def transformer(cls, name: str, **params: Any) -> Field:
        """Create a document transformer field expression.

        :param name: Transformer name (e.g. ``'explain'``, ``'child'``).
        :param params: Transformer parameters.
        :returns: A Field that renders as ``[name param=val ...]``.
        """
        if params:
            param_str = ' '.join('%s=%s' % (k, v) for k, v in params.items())
            expr = '[%s %s]' % (name, param_str)
        else:
            expr = '[%s]' % name
        return cls(expr)

    @classmethod
    def score(cls) -> Field:
        """Create a score pseudo-field.

        :returns: A Field that renders as ``score``.
        """
        return cls('score')
