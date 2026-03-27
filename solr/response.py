from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .core import SearchHandler


class Results(list[Any]):
    """Convenience class containing <result> items."""
    pass


class Group:
    """A single group within a Solr grouped response.

    Each group corresponds to one distinct value of the grouped field and
    contains the matching documents for that value.

    Attributes are accessed via :attr:`groupValue` and :attr:`doclist`.
    """

    def __init__(self, raw: dict[str, Any]) -> None:
        self._raw = raw

    @property
    def groupValue(self) -> Any:
        """The field value that defines this group, or ``None`` for the null group."""
        return self._raw.get('groupValue')

    @property
    def doclist(self) -> Results:
        """The matching documents in this group as a :class:`Results` list.

        ``doclist.numFound`` gives the total match count for this group;
        ``doclist.start`` gives the offset.
        """
        dl = self._raw.get('doclist', {})
        if isinstance(dl, Results):
            nf = getattr(dl, 'numFound', None)
            if nf is not None:
                try:
                    setattr(dl, 'numFound', int(nf))
                except (TypeError, ValueError):
                    setattr(dl, 'numFound', 0)
            st = getattr(dl, 'start', None)
            if st is not None:
                try:
                    setattr(dl, 'start', int(st))
                except (TypeError, ValueError):
                    setattr(dl, 'start', 0)
            return dl
        r = Results(dl.get('docs', []))
        setattr(r, 'numFound', int(dl.get('numFound', 0)))
        setattr(r, 'start', int(dl.get('start', 0)))
        return r

    def __repr__(self) -> str:
        return 'Group(groupValue=%r, numDocs=%d)' % (
            self.groupValue, len(self.doclist))


class GroupField:
    """The grouped results for a single field (or function/query).

    Returned as a value of :class:`GroupedResult` when subscripted by field
    name::

        resp.grouped['category'].matches   # total matches
        resp.grouped['category'].ngroups   # distinct group count (if requested)
        resp.grouped['category'].groups    # list of Group objects
    """

    def __init__(self, raw: dict[str, Any]) -> None:
        self._raw = raw

    @property
    def matches(self) -> int:
        """Total number of documents that match the query across all groups."""
        return int(self._raw.get('matches', 0))

    @property
    def ngroups(self) -> int | None:
        """Number of distinct groups, or ``None`` if ``group.ngroups`` was not requested."""
        val = self._raw.get('ngroups')
        return int(val) if val is not None else None

    @property
    def groups(self) -> list[Group]:
        """List of :class:`Group` objects for this field."""
        return [Group(g) for g in self._raw.get('groups', [])]

    def __repr__(self) -> str:
        return 'GroupField(matches=%d, ngroups=%r, groups=%d)' % (
            self.matches, self.ngroups, len(self.groups))


class GroupedResult:
    """Wrapper around a Solr grouped response component (Solr 3.3+).

    Provides access to grouped results returned by the GroupingComponent.
    Activate grouping by passing ``group=True`` and ``group_field='field'``
    to a query.  The result is then accessible via ``response.grouped``.

    Example::

        resp = conn.select('*:*', group=True, group_field='category',
                           group_limit=5, group_ngroups=True)
        for group in resp.grouped['category'].groups:
            print(group.groupValue, len(group.doclist))

    Supports ``in`` tests, iteration over field names, and ``len()``.
    """

    def __init__(self, raw: dict[str, Any]) -> None:
        self._raw = raw

    def __getitem__(self, field: str) -> GroupField:
        return GroupField(self._raw[field])

    def __iter__(self) -> Any:
        return iter(self._raw)

    def __contains__(self, field: object) -> bool:
        return field in self._raw

    def __len__(self) -> int:
        return len(self._raw)

    def __repr__(self) -> str:
        return 'GroupedResult(%r)' % list(self._raw.keys())


class SpellcheckResult:
    """Wrapper around a Solr spellcheck response component.

    Provides convenient accessors for the collation string and per-word
    suggestions returned by the SpellCheckComponent. Available in Solr 1.4+.

    Activate spellchecking by adding ``spellcheck=true`` (and optionally
    ``spellcheck_collate=true``) to a query. The result is then accessible
    via ``response.spellcheck``.

    Example::

        resp = conn.select('misspeled query', spellcheck='true',
                           spellcheck_collate='true',
                           spellcheck_count='5')
        if resp.spellcheck and not resp.spellcheck.correctly_spelled:
            print('Did you mean:', resp.spellcheck.collation)
            for entry in resp.spellcheck.suggestions:
                print(entry['original'], '->', entry.get('suggestion', []))
    """

    def __init__(self, raw: dict[str, Any]) -> None:
        self._raw = raw

    @property
    def correctly_spelled(self) -> bool:
        """True if all query terms were spelled correctly."""
        return bool(self._raw.get('correctlySpelled', True))

    @property
    def suggestions(self) -> list[dict[str, Any]]:
        """List of per-word suggestion entries.

        Each entry is a dict with at least an ``'original'`` key (the
        misspelled word) merged with the info dict returned by Solr
        (``'numFound'``, ``'startOffset'``, ``'endOffset'``,
        ``'suggestion'``, etc.).
        """
        raw_list = self._raw.get('suggestions', [])
        result: list[dict[str, Any]] = []
        i = 0
        while i < len(raw_list) - 1:
            orig = raw_list[i]
            info = raw_list[i + 1]
            if (isinstance(orig, str) and orig != 'collation'
                    and isinstance(info, dict)):
                result.append({'original': orig, **info})
                i += 2
            else:
                i += 1
        return result

    @property
    def collation(self) -> str | None:
        """The collation string (best-guess corrected full query), or None.

        Checks both the top-level ``'collation'`` key (modern JSON responses)
        and the inline ``'collation'`` marker inside the ``'suggestions'``
        list (older Solr XML-derived responses).
        """
        if 'collation' in self._raw:
            val = self._raw['collation']
            return str(val) if val is not None else None
        raw_list = self._raw.get('suggestions', [])
        for i, item in enumerate(raw_list):
            if item == 'collation' and i + 1 < len(raw_list):
                return str(raw_list[i + 1])
        return None

    def __repr__(self) -> str:
        return 'SpellcheckResult(%r)' % self._raw


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
        self._spellcheck_raw: dict[str, Any] | None = None

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

    def _get_spellcheck(self) -> SpellcheckResult | None:
        if self._spellcheck_raw is None:
            return None
        return SpellcheckResult(self._spellcheck_raw)

    def _set_spellcheck(self, value: dict[str, Any] | None) -> None:
        self._spellcheck_raw = value

    spellcheck = property(_get_spellcheck, _set_spellcheck,
                          doc="SpellcheckResult for this response, or None.")

    def as_models(self, model: type[Any]) -> list[Any]:
        """Convert result documents to Pydantic model instances.

        Requires ``pydantic`` to be installed (``pip install solrpy[pydantic]``).

        :param model: A Pydantic ``BaseModel`` subclass.
        :returns: List of model instances.
        :raises ImportError: If pydantic is not installed.
        """
        try:
            from pydantic import BaseModel as _BM
        except ImportError:
            raise ImportError(
                "pydantic is required for model support. "
                "Install with: pip install solrpy[pydantic]")
        return [model.model_validate(doc) for doc in self.results]

    def __len__(self) -> int:
        """Return the number of matching documents contained in this set."""
        return len(self.results)

    def __iter__(self) -> Any:
        """Return an iterator of matching documents."""
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
