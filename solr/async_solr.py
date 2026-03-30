"""Async Solr client built on httpx.AsyncClient.

Provides the same API as :class:`~solr.core.Solr` but with
``async``/``await`` methods.

Example::

    from solr import AsyncSolr

    async with AsyncSolr('http://localhost:8983/solr/mycore') as conn:
        response = await conn.select('*:*')
        for doc in response.results:
            print(doc['id'])
"""
from __future__ import annotations

import re
import json
import logging
import warnings
import base64
import urllib.parse as urlparse
import httpx
from io import StringIO
from typing import Any, Iterable, Iterator

from .exceptions import SolrException, SolrVersionError
from .utils import (
    UTC, utc_to_string, qs_from_items, strify,
    committing, requires_version, serialize_value, solr_json_default,
)
from .response import Response, Results
from .parsers import parse_json_response, parse_query_response


class AsyncSolr:
    """Async Solr client with the same API as :class:`~solr.core.Solr`.

    Use as an async context manager::

        async with AsyncSolr('http://localhost:8983/solr/mycore') as conn:
            response = await conn.select('*:*')
    """

    def __init__(self, url: str,
                 timeout: float | None = None,
                 http_user: str | None = None,
                 http_pass: str | None = None,
                 post_headers: dict[str, str] | None = None,
                 max_retries: int = 3,
                 retry_delay: float = 0.1,
                 always_commit: bool = False,
                 response_format: str = 'json',
                 auth_token: str | None = None,
                 auth: Any = None,
                 debug: bool = False) -> None:
        """Create an async Solr connection.

        Same parameters as :class:`~solr.core.Solr`.

        :param url: URI pointing to the Solr instance, e.g.
            ``'http://localhost:8983/solr/mycore'``.
        :param timeout: Timeout in seconds for server responses.
        :param http_user: Username for HTTP Basic authentication.
        :param http_pass: Password for HTTP Basic authentication.
        :param post_headers: Extra headers included in all requests.
        :param max_retries: Max automatic retries on connection errors.
        :param retry_delay: Base delay in seconds between retries (exponential backoff).
        :param always_commit: Auto-commit on every update method call.
        :param response_format: ``'json'`` (default) or ``'xml'``.
        :param auth_token: Bearer token string for authentication.
        :param auth: Callable returning a ``dict[str, str]`` of auth headers per request.
        :param debug: Log all requests and responses.
        """
        self.scheme, self.host, self.path = urlparse.urlparse(url, 'http')[:3]
        self.url = url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.always_commit = always_commit
        self.response_format = response_format
        self.response_version = 2.2
        self.debug = debug
        self._auth_callable = auth

        if post_headers is None:
            post_headers = {}

        self.xmlheaders: dict[str, str] = {
            'Content-Type': 'text/xml; charset=utf-8',
        }
        self.xmlheaders.update(post_headers)
        self.form_headers: dict[str, str] = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
        }
        self.form_headers.update(post_headers)

        if auth is not None:
            self.auth_headers: dict[str, str] = {}
        elif auth_token is not None:
            self.auth_headers = {'Authorization': 'Bearer ' + auth_token}
        elif http_user is not None and http_pass is not None:
            cred = base64.b64encode(
                (http_user + ':' + http_pass).encode('utf-8')
            ).decode('utf-8').strip()
            self.auth_headers = {'Authorization': 'Basic ' + cred}
        else:
            self.auth_headers = {}

        base_url = '%s://%s' % (self.scheme, self.host)
        self._client: httpx.AsyncClient = httpx.AsyncClient(
            base_url=base_url, timeout=self.timeout, follow_redirects=True)

        self._server_version: tuple[int, ...] | None = None

    @property
    def server_version(self) -> tuple[int, ...]:
        """Lazily detect and cache the Solr server version."""
        if self._server_version is None:
            self._server_version = self._detect_version_sync()
        return self._server_version

    @server_version.setter
    def server_version(self, value: tuple[int, ...]) -> None:
        self._server_version = value

    def _detect_version_sync(self) -> tuple[int, ...]:
        """Detect Solr version synchronously (used during __init__)."""
        base_url = '%s://%s' % (self.scheme, self.host)
        with httpx.Client(base_url=base_url, timeout=self.timeout) as client:
            base_paths = [self.path]
            parent = self.path.rsplit('/', 1)[0]
            if parent and parent != self.path:
                base_paths.append(parent)
            for base in base_paths:
                try:
                    rsp = client.get(base + '/admin/info/system?wt=json',
                                     headers=self.auth_headers)
                    if rsp.status_code == 200:
                        data = json.loads(rsp.content)
                        ver_str = data['lucene']['solr-spec-version']
                        return tuple(int(x) for x in ver_str.split('.')[:3])
                except Exception:
                    pass
        logging.warning("solrpy: could not detect Solr version, assuming 1.2.0")
        return (1, 2, 0)

    async def __aenter__(self) -> AsyncSolr:
        """Enter async context manager."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit async context manager."""
        await self.close()

    async def close(self) -> None:
        """Close the underlying httpx.AsyncClient."""
        await self._client.aclose()

    def _get_auth_headers(self) -> dict[str, str]:
        """Return auth headers."""
        if self._auth_callable is not None:
            result: dict[str, str] = self._auth_callable()
            return result
        return self.auth_headers.copy()

    def ping(self) -> bool:
        """Ping Solr (sync, uses a temporary client)."""
        base_url = '%s://%s' % (self.scheme, self.host)
        with httpx.Client(base_url=base_url, timeout=self.timeout) as client:
            base_paths = [self.path]
            parent = self.path.rsplit('/', 1)[0]
            if parent and parent != self.path:
                base_paths.append(parent)
            for base in base_paths:
                try:
                    rsp = client.get(base + '/admin/ping?wt=json',
                                     headers=self._get_auth_headers())
                    if rsp.status_code == 200 and '"OK"' in rsp.text:
                        return True
                except Exception:
                    pass
        return False

    async def _get(self, path: str) -> httpx.Response:
        """Async GET request."""
        rsp = await self._client.get(path, headers=self._get_auth_headers())
        if rsp.status_code != 200:
            raise SolrException(rsp.status_code, rsp.reason_phrase, rsp.text)
        return rsp

    async def _post(self, url: str, body: str | bytes,
                    headers: dict[str, str],
                    timeout: float | None = None) -> httpx.Response:
        """Async POST with retry and exponential backoff."""
        import asyncio
        _logger = logging.getLogger('solr')
        _headers = self._get_auth_headers()
        _headers.update(headers)
        raw_body = body if isinstance(body, bytes) else body.encode('utf-8')
        attempts = self.max_retries + 1
        retry_num = 0
        while attempts > 0:
            try:
                kwargs: dict[str, Any] = {'headers': _headers, 'content': raw_body}
                if timeout is not None:
                    kwargs['timeout'] = timeout
                rsp = await self._client.post(url, **kwargs)
                if rsp.status_code != 200:
                    raise SolrException(rsp.status_code, rsp.reason_phrase, rsp.text)
                return rsp
            except (httpx.ConnectError, httpx.ReadError, httpx.WriteError):
                attempts -= 1
                if attempts <= 0:
                    raise
                retry_num += 1
                delay = self.retry_delay * (2 ** (retry_num - 1))
                _logger.warning("Retry %d/%d for %s (delay=%.2fs)",
                                retry_num, self.max_retries, url, delay)
                await asyncio.sleep(delay)
        raise RuntimeError("Unreachable")

    @property
    def _use_json_updates(self) -> bool:
        """Use JSON update path when Solr 4.0+ is detected."""
        return self.server_version >= (4, 0)

    async def _update(self, request: str, query: dict[str, str] | None = None,
                      timeout: float | None = None) -> str:
        """Send an update XML request."""
        selector = '%s/update%s' % (self.path, qs_from_items(query))  # type: ignore[arg-type]
        rsp = await self._post(selector, request, self.xmlheaders, timeout=timeout)
        return rsp.text

    async def _json_update(self, body: Any, query: dict[str, str] | None = None,
                           timeout: float | None = None) -> str:
        """Send a JSON update request."""
        selector = '%s/update%s' % (self.path, qs_from_items(query))  # type: ignore[arg-type]
        payload = json.dumps(body, default=solr_json_default)
        headers = {'Content-Type': 'application/json; charset=utf-8'}
        rsp = await self._post(selector, payload, headers, timeout=timeout)
        return rsp.text

    async def select(self, q: str | None = None, **params: Any) -> Response | None:
        """Async search query.

        :param q: Query string, e.g. ``'*:*'`` or ``'title:foo'``.
        :param params: Additional Solr query parameters passed as keyword
            arguments.  Underscores in keys are converted to dots, so
            ``facet_field='category'`` becomes ``facet.field=category``.
        :param model: Optional Pydantic model class. When provided,
            ``response.results`` will contain model instances instead of dicts.
        """
        model = params.pop('model', None)
        timeout = params.pop('timeout', None)
        if q is not None:
            params['q'] = q
        if 'fl' not in params:
            params['fl'] = '*,score'
        params['wt'] = 'json'
        import urllib.parse
        request = urllib.parse.urlencode(
            [(k.replace('_', '.'), strify(v)) for k, v in params.items()],
            doseq=True)
        rsp = await self._post(
            self.path + '/select', request, self.form_headers,
            timeout=timeout)
        data = json.loads(rsp.content)
        resp = parse_json_response(data, params, self)
        if model is not None and resp is not None:
            resp.results = resp.as_models(model)
        return resp

    async def add(self, doc: dict[str, Any], **kwargs: Any) -> Any:
        """Async add a document.

        :param doc: Dictionary mapping field names to values.
        :param kwargs: Optional keyword arguments.  ``commit`` (bool) forces an
            immediate commit; ``timeout`` (float) overrides the request timeout.
        """
        commit = kwargs.pop('commit', self.always_commit)
        timeout = kwargs.pop('timeout', None)
        query: dict[str, str] = {}
        if commit:
            query['commit'] = 'true'
        if self._use_json_updates:
            body = [{k: v for k, v in doc.items() if v is not None}]
            return await self._json_update(body, query, timeout=timeout)
        from xml.sax.saxutils import escape, quoteattr
        lst = ['<add><doc>']
        for field, value in doc.items():
            if not isinstance(value, (list, tuple, set)):
                values: list[Any] = [value]
            else:
                values = list(value)
            for v in values:
                serialized = serialize_value(v)
                if serialized is None:
                    continue
                lst.append('<field name=%s>%s</field>' % (
                    quoteattr(field), escape(serialized)))
        lst.append('</doc></add>')
        return await self._update(''.join(lst), query, timeout=timeout)

    async def add_many(self, docs: Iterable[dict[str, Any]], **kwargs: Any) -> Any:
        """Async add multiple documents.

        :param docs: Iterable of dictionaries, each mapping field names to values.
        :param kwargs: Optional keyword arguments.  ``commit`` (bool) forces an
            immediate commit; ``timeout`` (float) overrides the request timeout.
        """
        commit = kwargs.pop('commit', self.always_commit)
        timeout = kwargs.pop('timeout', None)
        query: dict[str, str] = {}
        if commit:
            query['commit'] = 'true'
        if self._use_json_updates:
            body = [{k: v for k, v in d.items() if v is not None} for d in docs]
            return await self._json_update(body, query, timeout=timeout)
        from xml.sax.saxutils import escape, quoteattr
        lst = ['<add>']
        for doc in docs:
            lst.append('<doc>')
            for field, value in doc.items():
                if not isinstance(value, (list, tuple, set)):
                    values = [value]
                else:
                    values = list(value)
                for v in values:
                    serialized = serialize_value(v)
                    if serialized is None:
                        continue
                    lst.append('<field name=%s>%s</field>' % (
                        quoteattr(field), escape(serialized)))
            lst.append('</doc>')
        lst.append('</add>')
        return await self._update(''.join(lst), query, timeout=timeout)

    async def delete(self, id: Any = None, **kwargs: Any) -> Any:
        """Async delete by id.

        :param id: Unique identifier of the document to delete.
        :param kwargs: Optional keyword arguments.  ``commit`` (bool) forces an
            immediate commit; ``timeout`` (float) overrides the request timeout.
        """
        from xml.sax.saxutils import escape
        commit = kwargs.pop('commit', self.always_commit)
        timeout = kwargs.pop('timeout', None)
        xml = '<delete><id>%s</id></delete>' % escape(str(id))
        query: dict[str, str] = {}
        if commit:
            query['commit'] = 'true'
        return await self._update(xml, query, timeout=timeout)

    async def delete_query(self, q: str, **kwargs: Any) -> Any:
        """Async delete by query.

        :param q: Solr query string identifying documents to delete.
        :param kwargs: Optional keyword arguments.  ``commit`` (bool) forces an
            immediate commit; ``timeout`` (float) overrides the request timeout.
        """
        from xml.sax.saxutils import escape
        commit = kwargs.pop('commit', self.always_commit)
        timeout = kwargs.pop('timeout', None)
        xml = '<delete><query>%s</query></delete>' % escape(q)
        query: dict[str, str] = {}
        if commit:
            query['commit'] = 'true'
        return await self._update(xml, query, timeout=timeout)

    async def commit(self, **kwargs: Any) -> str:
        """Async commit.

        :param kwargs: Optional keyword arguments.  ``soft_commit`` (bool)
            performs a soft commit instead of a hard commit when set to ``True``.
        """
        soft_commit = kwargs.pop('soft_commit', False)
        if soft_commit:
            return await self._update('<commit softCommit="true"/>')
        return await self._update('<commit />')

    async def get(self, id: str | None = None, ids: list[str] | None = None,
                  fields: list[str] | None = None,
                  model: type[Any] | None = None) -> Any:
        """Async Real-time Get.

        :param id: Unique identifier of a single document to retrieve.
        :param ids: List of document identifiers to retrieve in bulk.
        :param fields: List of field names to return (passed as ``fl``).
        :param model: Optional Pydantic model class.  When provided, results
            are returned as model instances instead of plain dicts.
        """
        if id is None and ids is None:
            raise ValueError("Either id or ids must be specified.")
        import urllib.parse
        params: dict[str, str] = {'wt': 'json'}
        if id is not None:
            params['id'] = str(id)
        elif ids is not None:
            params['ids'] = ','.join(str(i) for i in ids)
        if fields:
            params['fl'] = ','.join(fields)
        qs = urllib.parse.urlencode(params)
        rsp = await self._get('%s/get?%s' % (self.path, qs))
        data = json.loads(rsp.content)
        if id is not None:
            result = data.get('doc')
            if result is not None and model is not None:
                return model.model_validate(result)
            return result
        docs = data.get('response', {}).get('docs', [])
        if model is not None:
            return [model.model_validate(d) for d in docs]
        return docs

    async def stream(self, expr: Any,
                     model: type[Any] | None = None) -> Any:
        """Execute a streaming expression via the ``/stream`` handler (Solr 5.0+).

        Returns an async generator of tuple dicts. Skips the final EOF marker.

        Usage::

            async for doc in await conn.stream(expr):
                print(doc)

        :param expr: A :class:`~solr.stream.StreamExpression` or string.
        :param model: Optional Pydantic model for automatic conversion.
        :returns: Async generator of result dicts (or model instances).
        """
        if self.server_version < (5, 0):
            raise SolrVersionError("stream", (5, 0), self.server_version)

        import urllib.parse
        qs = urllib.parse.urlencode({'expr': str(expr)})
        selector = '%s/stream?%s' % (self.path, qs)
        rsp = await self._get(selector)
        data = json.loads(rsp.content)

        docs = data.get('result-set', {}).get('docs', [])

        async def _iter() -> Any:
            for doc in docs:
                if 'EOF' in doc:
                    return
                if model is not None:
                    yield model.model_validate(doc)
                else:
                    yield doc

        return _iter()
