from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .core import SearchHandler


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

    def cursor_next(self) -> Response | None:
        """Follow cursor-based pagination (Solr 4.7+).

        Returns the next page of results using cursorMark, or None if
        there are no more results (nextCursorMark == cursorMark) or if
        the original query did not use cursorMark.
        """
        current_cursor = self._params.get('cursorMark')
        if current_cursor is None:
            return None

        next_cursor = getattr(self, 'nextCursorMark', None)
        if next_cursor is None or next_cursor == current_cursor:
            return None

        # Version check via the SearchHandler's conn
        query = self._query
        conn = getattr(query, 'conn', None)
        conn_version = getattr(self, '_conn_version', None) or (
            conn.server_version if conn else None)
        if conn_version and conn_version < (4, 7):
            from .exceptions import SolrVersionError
            raise SolrVersionError("cursor_next", (4, 7), conn_version)

        params = dict(self._params)
        params['cursorMark'] = next_cursor
        q = params.pop('q', '')
        result: Response | None = self._query(q, **params)
        return result

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
