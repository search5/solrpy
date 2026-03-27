"""Compatibility wrapper that exposes a pysolr-like API on top of solrpy.

This module provides :class:`PysolrCompat`, a thin shim that subclasses
:class:`~solr.core.Solr` and adds method aliases matching the pysolr library.
Users migrating from pysolr can switch to solrpy with minimal code changes::

    # Before (pysolr)
    # import pysolr
    # conn = pysolr.Solr('http://localhost:8983/solr/core0')

    # After (solrpy)
    from solr import PysolrCompat
    conn = PysolrCompat('http://localhost:8983/solr/core0')

    # These pysolr-style calls now work:
    results = conn.search('field:value', rows=10)
    conn.add([{'id': '1', 'title': 'Hello'}])
    conn.delete(id='1')
    conn.delete(q='title:Hello')
    conn.commit()
    conn.ping()
"""
from __future__ import annotations

from typing import Any, IO

from .core import Solr
from .extract import Extract


class PysolrCompat(Solr):
    """A pysolr-compatible wrapper around :class:`~solr.core.Solr`.

    Subclasses ``Solr`` so all native solrpy features remain available.
    Overrides or adds methods to match pysolr's public API, allowing
    drop-in migration from pysolr with minimal code changes.
    """

    def search(self, q: str, **kwargs: Any) -> Any:
        """Search for documents (pysolr-compatible alias for ``select``).

        :param q: The query string.
        :param kwargs: Additional Solr parameters (e.g. ``rows``, ``fq``).
        :returns: A :class:`~solr.response.Response` instance.
        """
        return self.select(q, **kwargs)

    def add(self, docs: list[dict[str, Any]] | dict[str, Any],  # type: ignore[override]
            commit: bool = True, **kwargs: Any) -> Any:
        """Add one or more documents (pysolr-compatible).

        Unlike native solrpy (which takes a single dict), this method
        accepts either a list of dicts or a single dict, matching pysolr
        behavior.

        :param docs: A list of document dicts, or a single document dict.
        :param commit: Whether to auto-commit after adding. Defaults to
            ``True`` to match pysolr convention.
        """
        if isinstance(docs, list):
            self.add_many(docs)
        else:
            # Single dict — delegate to parent Solr.add()
            super().add(docs)
        if commit:
            self.commit()

    def delete(self, id: Any = None, q: str | None = None,  # type: ignore[override]
               commit: bool = True, **kwargs: Any) -> None:
        """Delete documents by id and/or query (pysolr-compatible).

        :param id: Document id to delete.
        :param q: Query string; all matching documents will be deleted.
        :param commit: Whether to auto-commit after deleting. Defaults to
            ``True`` to match pysolr convention.
        """
        if id is not None:
            super().delete(id=id)
        if q is not None:
            self.delete_query(q)
        if commit:
            self.commit()

    def extract(self, file_obj: IO[bytes], **kwargs: Any) -> Any:  # type: ignore[override]
        """Extract/index a rich document via Solr Cell (pysolr-compatible).

        Creates an :class:`~solr.extract.Extract` companion on-the-fly and
        delegates. All keyword arguments are forwarded.

        :param file_obj: A file-like object containing the document bytes.
        :returns: The extraction result.
        """
        ext = Extract(self)
        return ext(file_obj, **kwargs)
