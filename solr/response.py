from __future__ import annotations

from typing import Any


class Results(list[Any]):
    """Convenience class containing <result> items."""
    pass


class Response:
    """A container class for query results.

    A Response object will have the following properties:

          header -- a dict containing any responseHeader values

          results -- a list of matching documents. Each list item will
              be a dict.
    """
    def __init__(self, query: Any) -> None:
        self.header: dict[str, Any] = {}
        self.results: Any = []
        self._query: Any = query
        self._params: dict[str, Any] = {}

    def _set_numFound(self, value: int | str) -> None:
        self._numFound = int(value)

    def _get_numFound(self) -> int:
        return self._numFound

    def _del_numFound(self) -> None:
        del self._numFound

    numFound = property(_get_numFound, _set_numFound, _del_numFound)

    def _set_start(self, value: int | str) -> None:
        self._start = int(value)

    def _get_start(self) -> int:
        return self._start

    def _del_start(self) -> None:
        del self._start

    start = property(_get_start, _set_start, _del_start)

    def _set_maxScore(self, value: float | str) -> None:
        self._maxScore = float(value)

    def _get_maxScore(self) -> float:
        return self._maxScore

    def _del_maxScore(self) -> None:
        del self._maxScore

    maxScore = property(_get_maxScore, _set_maxScore, _del_maxScore)

    def __len__(self) -> int:
        return len(self.results)

    def __iter__(self) -> Any:
        return iter(self.results)

    def next_batch(self) -> Any:
        """Load the next set of matches."""
        try:
            start = int(self.results.start)
        except AttributeError:
            start = 0

        start += len(self.results)
        params = dict(self._params)
        params['start'] = start
        q = params.pop('q', '')
        return self._query(q, **params)

    def previous_batch(self) -> Any:
        """Return the previous set of matches."""
        try:
            start = int(self.results.start)
        except AttributeError:
            start = 0

        if not start:
            return None

        rows = int(self.header.get('rows', len(self.results)))
        start = max(0, start - rows)
        params = dict(self._params)
        params['start'] = start
        params['rows'] = rows
        q = params.pop('q', '')
        return self._query(q, **params)
