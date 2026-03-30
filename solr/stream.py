"""Streaming Expressions builder and executor for Solr 5.0+.

Provides Python functions that map 1:1 to Solr streaming expression
functions, with pipe (``|``) operator for chaining.

Example::

    from solr.stream import search, rollup, top, count, sum

    expr = (search('logs', q='*:*', fl='host,bytes', sort='host asc')
            | rollup(over='host', total=sum('bytes'))
            | top(n=5, sort='total desc'))

    for doc in conn.stream(expr):
        print(doc)
"""
from __future__ import annotations

from typing import Any


class StreamExpression:
    """A Solr streaming expression node.

    Renders to a Solr expression string via ``str()``.
    Supports the ``|`` (pipe) operator for chaining.
    """

    def __init__(self, func_name: str, *args: Any, **kwargs: Any) -> None:
        """Initialize a streaming expression node.

        :param func_name: The Solr streaming function name (e.g. ``"search"``).
        :param args: Positional arguments (collection names, sub-expressions).
        :param kwargs: Named parameters rendered as ``key=value`` pairs.
        """
        self._func = func_name
        self._args: list[Any] = list(args)
        self._kwargs: dict[str, Any] = kwargs

    def __str__(self) -> str:
        """Render as a Solr streaming expression string."""
        parts: list[str] = []
        for arg in self._args:
            parts.append(str(arg))
        for key, value in self._kwargs.items():
            val_str = str(value)
            # Quote string values that contain spaces (sort clauses, queries)
            # Don't quote simple identifiers, numbers, or sub-expressions
            if isinstance(value, str) and ' ' in value:
                val_str = '"%s"' % value
            parts.append('%s=%s' % (key, val_str))
        return '%s(%s)' % (self._func, ','.join(parts))

    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        return 'StreamExpression(%r)' % str(self)

    def __or__(self, other: StreamExpression) -> StreamExpression:
        """Pipe operator: pass this expression as the first arg of *other*."""
        result = StreamExpression(other._func, *other._args, **other._kwargs)
        result._args.insert(0, self)
        return result


class AggregateExpression:
    """An aggregate function (count, sum, avg, min, max) for use in rollup/stats."""

    def __init__(self, func_name: str, field: str) -> None:
        """Initialize an aggregate expression.

        :param func_name: The aggregate function name (e.g. ``"sum"``).
        :param field: The Solr field to aggregate over.
        """
        self._func = func_name
        self._field = field

    def __str__(self) -> str:
        """Render as ``func(field)``."""
        return '%s(%s)' % (self._func, self._field)

    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        return str(self)


# ===================================================================
# Source expressions
# ===================================================================

def search(collection: str, **kwargs: Any) -> StreamExpression:
    """Build a ``search()`` streaming expression.

    :param collection: Solr collection name.
    :param kwargs: Query parameters (q, fl, sort, rows, etc.).
    """
    return StreamExpression('search', collection, **kwargs)


def facet(collection: str, **kwargs: Any) -> StreamExpression:
    """Build a ``facet()`` streaming expression.

    :param collection: Solr collection name.
    :param kwargs: Facet parameters (q, buckets, bucketSorts, etc.).
    """
    return StreamExpression('facet', collection, **kwargs)


def topic(collection: str, **kwargs: Any) -> StreamExpression:
    """Build a ``topic()`` streaming expression.

    :param collection: Solr collection name.
    :param kwargs: Topic parameters (q, fl, id, checkpointEvery, etc.).
    """
    return StreamExpression('topic', collection, **kwargs)


# ===================================================================
# Transform expressions
# ===================================================================

def unique(*args: Any, **kwargs: Any) -> StreamExpression:
    """Build a ``unique()`` streaming expression.

    :param args: Positional arguments (sub-expressions, field names).
    :param kwargs: Named parameters (over, etc.).
    """
    return StreamExpression('unique', *args, **kwargs)


def top(*args: Any, **kwargs: Any) -> StreamExpression:
    """Build a ``top()`` streaming expression.

    :param args: Positional arguments (sub-expressions).
    :param kwargs: Named parameters (n, sort, etc.).
    """
    return StreamExpression('top', *args, **kwargs)


def sort(*args: Any, **kwargs: Any) -> StreamExpression:
    """Build a ``sort()`` streaming expression.

    :param args: Positional arguments (sub-expressions).
    :param kwargs: Named parameters (by, etc.).
    """
    return StreamExpression('sort', *args, **kwargs)


def select(*args: Any, **kwargs: Any) -> StreamExpression:
    """Build a ``select()`` streaming expression.

    :param args: Positional arguments (sub-expressions, field names).
    :param kwargs: Named parameters (field aliases, etc.).
    """
    return StreamExpression('select', *args, **kwargs)


def rollup(*args: Any, **kwargs: Any) -> StreamExpression:
    """Build a ``rollup()`` streaming expression.

    :param args: Positional arguments (sub-expressions).
    :param kwargs: Named parameters (over, aggregate functions, etc.).
    """
    return StreamExpression('rollup', *args, **kwargs)


def reduce(*args: Any, **kwargs: Any) -> StreamExpression:
    """Build a ``reduce()`` streaming expression.

    :param args: Positional arguments (sub-expressions).
    :param kwargs: Named parameters (by, etc.).
    """
    return StreamExpression('reduce', *args, **kwargs)


# ===================================================================
# Join expressions
# ===================================================================

def merge(*args: Any, **kwargs: Any) -> StreamExpression:
    """Build a ``merge()`` streaming expression.

    :param args: Positional arguments (two or more sub-expressions to merge).
    :param kwargs: Named parameters (on, etc.).
    """
    return StreamExpression('merge', *args, **kwargs)


def innerJoin(*args: Any, **kwargs: Any) -> StreamExpression:
    """Build an ``innerJoin()`` streaming expression.

    :param args: Positional arguments (two sub-expressions to join).
    :param kwargs: Named parameters (on, etc.).
    """
    return StreamExpression('innerJoin', *args, **kwargs)


def leftOuterJoin(*args: Any, **kwargs: Any) -> StreamExpression:
    """Build a ``leftOuterJoin()`` streaming expression.

    :param args: Positional arguments (two sub-expressions to join).
    :param kwargs: Named parameters (on, etc.).
    """
    return StreamExpression('leftOuterJoin', *args, **kwargs)


def hashJoin(*args: Any, **kwargs: Any) -> StreamExpression:
    """Build a ``hashJoin()`` streaming expression.

    :param args: Positional arguments (two sub-expressions to join).
    :param kwargs: Named parameters (on, hashed, etc.).
    """
    return StreamExpression('hashJoin', *args, **kwargs)


def intersect(*args: Any, **kwargs: Any) -> StreamExpression:
    """Build an ``intersect()`` streaming expression.

    :param args: Positional arguments (two sub-expressions).
    :param kwargs: Named parameters (on, etc.).
    """
    return StreamExpression('intersect', *args, **kwargs)


def complement(*args: Any, **kwargs: Any) -> StreamExpression:
    """Build a ``complement()`` streaming expression.

    :param args: Positional arguments (two sub-expressions).
    :param kwargs: Named parameters (on, etc.).
    """
    return StreamExpression('complement', *args, **kwargs)


# ===================================================================
# Aggregate functions
# ===================================================================

def count(field: str) -> AggregateExpression:
    """Aggregate: ``count(field)``.

    :param field: The Solr field to count.
    """
    return AggregateExpression('count', field)


def sum(field: str) -> AggregateExpression:
    """Aggregate: ``sum(field)``.

    :param field: The Solr field to sum.
    """
    return AggregateExpression('sum', field)


def avg(field: str) -> AggregateExpression:
    """Aggregate: ``avg(field)``.

    :param field: The Solr field to average.
    """
    return AggregateExpression('avg', field)


def min(field: str) -> AggregateExpression:
    """Aggregate: ``min(field)``.

    :param field: The Solr field to find the minimum of.
    """
    return AggregateExpression('min', field)


def max(field: str) -> AggregateExpression:
    """Aggregate: ``max(field)``.

    :param field: The Solr field to find the maximum of.
    """
    return AggregateExpression('max', field)


# ===================================================================
# Control expressions
# ===================================================================

def fetch(*args: Any, **kwargs: Any) -> StreamExpression:
    """Build a ``fetch()`` streaming expression.

    :param args: Positional arguments (collection, sub-expression).
    :param kwargs: Named parameters (fl, on, etc.).
    """
    return StreamExpression('fetch', *args, **kwargs)


def parallel(*args: Any, **kwargs: Any) -> StreamExpression:
    """Build a ``parallel()`` streaming expression.

    :param args: Positional arguments (collection, sub-expression).
    :param kwargs: Named parameters (workers, sort, etc.).
    """
    return StreamExpression('parallel', *args, **kwargs)


def daemon(*args: Any, **kwargs: Any) -> StreamExpression:
    """Build a ``daemon()`` streaming expression.

    :param args: Positional arguments (sub-expression).
    :param kwargs: Named parameters (id, runInterval, queueSize, etc.).
    """
    return StreamExpression('daemon', *args, **kwargs)


def update(*args: Any, **kwargs: Any) -> StreamExpression:
    """Build an ``update()`` streaming expression.

    :param args: Positional arguments (collection, sub-expression).
    :param kwargs: Named parameters (batchSize, etc.).
    """
    return StreamExpression('update', *args, **kwargs)


def commit(*args: Any, **kwargs: Any) -> StreamExpression:
    """Build a ``commit()`` streaming expression.

    :param args: Positional arguments (collection, sub-expression).
    :param kwargs: Named parameters passed to the Solr commit expression.
    """
    return StreamExpression('commit', *args, **kwargs)
