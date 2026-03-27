"""MoreLikeThis handler wrapper for Solr 4.0+.

Since 2.0.4 this class accepts both :class:`~solr.core.Solr` and
:class:`~solr.async_solr.AsyncSolr`.
"""
from __future__ import annotations

import json
import urllib.parse
from typing import Any, TYPE_CHECKING

from .response import Response
from .transport import _is_async_conn

if TYPE_CHECKING:
    from .core import Solr


class MoreLikeThis:
    """Find similar documents using Solr's MoreLikeThis handler.

    Works with both ``Solr`` (sync) and ``AsyncSolr`` (async) connections.

    Example::

        from solr import Solr, MoreLikeThis

        conn = Solr('http://localhost:8983/solr/mycore')
        mlt = MoreLikeThis(conn)
        response = mlt('interesting text', fl='title,body')
    """

    def __init__(self, conn: Any) -> None:
        """Initialize a MoreLikeThis handler client.

        :param conn: A :class:`~solr.core.Solr` or :class:`~solr.async_solr.AsyncSolr` connection.
        """
        self._conn = conn
        self._is_async: bool = _is_async_conn(conn)
        if not self._is_async:
            from .core import SearchHandler
            self._handler = SearchHandler(conn, '/mlt')

    def __call__(self, q: str | None = None, **params: Any) -> Any:
        """Query the MLT handler.

        :param q: Query string to find similar documents for. If ``None``,
            the query must be supplied via ``params``.
        :param params: Additional Solr MLT parameters (e.g. ``fl``, ``mlt_fl``,
            ``mlt_mintf``).
        """
        if self._is_async:
            return self._call_async(q, **params)
        return self._handler(q, **params)

    async def _call_async(self, q: str | None = None, **params: Any) -> Response | None:
        """Async MLT query."""
        if q is not None:
            params['q'] = q
        params['wt'] = 'json'
        request = urllib.parse.urlencode(
            [(k.replace('_', '.'), str(v)) for k, v in params.items()],
            doseq=True)
        rsp = await self._conn._post(
            self._conn.path + '/mlt', request, self._conn.form_headers)
        from .parsers import parse_json_response
        data = json.loads(rsp.content)
        return parse_json_response(data, params, self)

    def raw(self, **params: Any) -> Any:
        """Issue a raw MLT query.

        :param params: Raw Solr parameters passed directly to the ``/mlt`` handler.
        """
        if self._is_async:
            raise NotImplementedError("raw() is not supported in async mode")
        return self._handler.raw(**params)
