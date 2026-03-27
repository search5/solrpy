"""Async versions of companion classes for use with AsyncSolr.

Each class mirrors its sync counterpart but uses ``AsyncTransport``
for all HTTP operations.
"""
from __future__ import annotations

import json
import urllib.parse as urllib
from typing import Any, Sequence, IO, TYPE_CHECKING

from .exceptions import SolrVersionError
from .transport import AsyncTransport
from .response import Response

if TYPE_CHECKING:
    from .async_solr import AsyncSolr


class AsyncSchemaAPI:
    """Async Schema API client (Solr 4.2+).

    Example::

        async with AsyncSolr(url) as conn:
            schema = AsyncSchemaAPI(conn)
            fields = await schema.fields()
    """

    _MIN_VERSION = (4, 2)

    def __init__(self, conn: AsyncSolr) -> None:
        self._transport = AsyncTransport(conn)

    def _check_version(self) -> None:
        """Raise SolrVersionError if server is too old."""
        if self._transport.server_version < self._MIN_VERSION:
            raise SolrVersionError("schema", self._MIN_VERSION,
                                   self._transport.server_version)

    async def fields(self) -> list[dict[str, Any]]:
        """List all fields."""
        self._check_version()
        data = await self._transport.get_json('/schema/fields')
        result: list[dict[str, Any]] = data.get('fields', [])
        return result

    async def add_field(self, name: str, field_type: str, **opts: Any) -> dict[str, Any]:
        """Add a new field."""
        self._check_version()
        return await self._transport.post_json('/schema', {'add-field': {'name': name, 'type': field_type, **opts}})

    async def replace_field(self, name: str, field_type: str, **opts: Any) -> dict[str, Any]:
        """Replace an existing field."""
        self._check_version()
        return await self._transport.post_json('/schema', {'replace-field': {'name': name, 'type': field_type, **opts}})

    async def delete_field(self, name: str) -> dict[str, Any]:
        """Delete a field."""
        self._check_version()
        return await self._transport.post_json('/schema', {'delete-field': {'name': name}})

    async def field_types(self) -> list[dict[str, Any]]:
        """List all field types."""
        self._check_version()
        data = await self._transport.get_json('/schema/fieldtypes')
        result: list[dict[str, Any]] = data.get('fieldTypes', [])
        return result

    async def get_schema(self) -> dict[str, Any]:
        """Return the full schema definition."""
        self._check_version()
        data = await self._transport.get_json('/schema')
        result: dict[str, Any] = data.get('schema', data)
        return result


class AsyncKNN:
    """Async KNN / Dense Vector Search (Solr 9.0+).

    Example::

        async with AsyncSolr(url) as conn:
            knn = AsyncKNN(conn)
            response = await knn.search([0.1, 0.2, 0.3], field='embedding', top_k=10)
    """

    _MIN_VERSION = (9, 0)

    def __init__(self, conn: AsyncSolr) -> None:
        self._conn = conn

    def _check_version(self) -> None:
        """Raise SolrVersionError if server is too old."""
        if self._conn.server_version < self._MIN_VERSION:
            raise SolrVersionError("knn_search", self._MIN_VERSION,
                                   self._conn.server_version)

    def build_knn_query(self, vector: Sequence[float], field: str, top_k: int = 10,
                        **kwargs: Any) -> str:
        """Build a {!knn} query string (sync, no await needed)."""
        from .knn import KNN
        # Reuse sync KNN's build method
        dummy = KNN.__new__(KNN)
        dummy._conn = self._conn  # type: ignore[assignment]
        return dummy.build_knn_query(vector, field, top_k, **kwargs)

    async def search(self, vector: Sequence[float], field: str, top_k: int = 10,
                     filters: str | None = None, **params: Any) -> Response | None:
        """Async KNN search."""
        self._check_version()
        q = self.build_knn_query(vector, field, top_k)
        if filters is not None:
            params['fq'] = filters
        return await self._conn.select(q, **params)

    async def similarity(self, vector: Sequence[float], field: str,
                         min_return: float, **params: Any) -> Response | None:
        """Async vectorSimilarity search."""
        self._check_version()
        from .knn import KNN
        dummy = KNN.__new__(KNN)
        dummy._conn = self._conn  # type: ignore[assignment]
        q = dummy.build_similarity_query(vector, field, min_return)
        return await self._conn.select(q, **params)


class AsyncMoreLikeThis:
    """Async MoreLikeThis (Solr 4.0+).

    Example::

        async with AsyncSolr(url) as conn:
            mlt = AsyncMoreLikeThis(conn)
            response = await mlt('interesting text', fl='title,body')
    """

    def __init__(self, conn: AsyncSolr) -> None:
        self._conn = conn

    async def __call__(self, q: str | None = None, **params: Any) -> Response | None:
        """Query the MLT handler."""
        # Build params and post to /mlt
        if q is not None:
            params['q'] = q
        params['wt'] = 'json'
        import urllib.parse
        request = urllib.parse.urlencode(
            [(k.replace('_', '.'), str(v)) for k, v in params.items()],
            doseq=True)
        rsp = await self._conn._post(
            self._conn.path + '/mlt', request, self._conn.form_headers)
        from .parsers import parse_json_response
        data = json.loads(rsp.text)
        return parse_json_response(data, params, self)


class AsyncSuggest:
    """Async Suggest (Solr 4.7+).

    Example::

        async with AsyncSolr(url) as conn:
            suggest = AsyncSuggest(conn)
            results = await suggest('que', dictionary='mySuggester')
    """

    _MIN_VERSION = (4, 7)

    def __init__(self, conn: AsyncSolr) -> None:
        self._conn = conn

    async def __call__(self, q: str, dictionary: str | None = None,
                       count: int = 10, **params: Any) -> list[dict[str, Any]]:
        """Return suggestions for a query term."""
        if self._conn.server_version < self._MIN_VERSION:
            raise SolrVersionError("suggest", self._MIN_VERSION,
                                   self._conn.server_version)
        query_params: dict[str, str] = {
            'suggest': 'true', 'suggest.q': q,
            'suggest.count': str(count), 'wt': 'json',
        }
        if dictionary is not None:
            query_params['suggest.dictionary'] = dictionary
        query_params.update({k: str(v) for k, v in params.items()})
        qs = urllib.urlencode(query_params)
        rsp = await self._conn._get('%s/suggest?%s' % (self._conn.path, qs))
        data: dict[str, Any] = json.loads(rsp.text)
        results: list[dict[str, Any]] = []
        for suggester in data.get('suggest', {}).values():
            for term_data in suggester.values():
                if isinstance(term_data, dict):
                    results.extend(term_data.get('suggestions', []))
        return results


class AsyncExtract:
    """Async Solr Extract / Rich Documents (Solr 1.4+).

    Example::

        async with AsyncSolr(url) as conn:
            extract = AsyncExtract(conn)
            with open('report.pdf', 'rb') as f:
                await extract(f, content_type='application/pdf', commit=True)
    """

    def __init__(self, conn: AsyncSolr) -> None:
        self._conn = conn

    async def __call__(self, file_obj: IO[bytes],
                       content_type: str = 'application/octet-stream',
                       commit: bool = False,
                       **params: Any) -> dict[str, Any]:
        """Index a rich document via /update/extract."""
        query_parts: list[tuple[str, str]] = [('wt', 'json')]
        if commit:
            query_parts.append(('commit', 'true'))
        for key, value in params.items():
            query_parts.append((key.replace('_', '.', 1), str(value)))
        qs = urllib.urlencode(query_parts)
        body = file_obj.read()
        headers: dict[str, str] = {'Content-Type': content_type}
        rsp = await self._conn._post(
            self._conn.path + '/update/extract?' + qs, body, headers)
        result: dict[str, Any] = json.loads(rsp.text)
        return result
