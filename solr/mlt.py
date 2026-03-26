"""MoreLikeThis handler wrapper for Solr 4.0+."""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .core import SearchHandler
from .response import Response

if TYPE_CHECKING:
    from .core import Solr


class MoreLikeThis:
    """Find similar documents using Solr's MoreLikeThis handler.

    Example::

        from solr import Solr, MoreLikeThis

        conn = Solr('http://localhost:8983/solr/mycore')
        mlt = MoreLikeThis(conn)
        response = mlt('interesting text', fl='title,body')
    """

    def __init__(self, conn: Solr) -> None:
        self._handler = SearchHandler(conn, '/mlt')

    def __call__(self, q: str | None = None, **params: Any) -> Response | None:
        """Query the MLT handler."""
        return self._handler(q, **params)

    def raw(self, **params: Any) -> str:
        """Issue a raw MLT query."""
        return self._handler.raw(**params)
