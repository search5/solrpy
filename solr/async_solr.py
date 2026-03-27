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
    committing, requires_version,
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
        self.conn: httpx.AsyncClient = httpx.AsyncClient(
            base_url=base_url, timeout=self.timeout, follow_redirects=True)

        # Version detection is sync during __init__; use sync client briefly
        self.server_version = self._detect_version_sync()

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
                        data = json.loads(rsp.text)
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
        await self.conn.aclose()

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
        rsp = await self.conn.get(path, headers=self._get_auth_headers())
        if rsp.status_code != 200:
            raise SolrException(rsp.status_code, rsp.reason_phrase, rsp.text)
        return rsp

    async def _post(self, url: str, body: str | bytes,
                    headers: dict[str, str],
                    timeout: float | None = None) -> httpx.Response:
        """Async POST with retry and exponential backoff."""
        import time
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
                rsp = await self.conn.post(url, **kwargs)
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
                time.sleep(delay)
        raise RuntimeError("Unreachable")

    async def _update(self, request: str, query: dict[str, str] | None = None,
                      timeout: float | None = None) -> str:
        """Send an update XML request."""
        selector = '%s/update%s' % (self.path, qs_from_items(query))  # type: ignore[arg-type]
        rsp = await self._post(selector, request, self.xmlheaders, timeout=timeout)
        return rsp.text

    async def select(self, q: str | None = None, **params: Any) -> Response | None:
        """Async search query."""
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
            timeout=params.pop('timeout', None) if 'timeout' in params else None)
        data = json.loads(rsp.text)
        return parse_json_response(data, params, self)

    async def add(self, doc: dict[str, Any], **kwargs: Any) -> Any:
        """Async add a document."""
        from xml.sax.saxutils import escape, quoteattr
        commit = kwargs.pop('commit', self.always_commit)
        timeout = kwargs.pop('timeout', None)
        lst = ['<add><doc>']
        for field, value in doc.items():
            if value is None:
                continue
            if isinstance(value, (list, tuple, set)):
                for v in value:
                    lst.append('<field name=%s>%s</field>' % (quoteattr(field), escape(str(v))))
            else:
                lst.append('<field name=%s>%s</field>' % (quoteattr(field), escape(str(value))))
        lst.append('</doc></add>')
        xml = ''.join(lst)
        query: dict[str, str] = {}
        if commit:
            query['commit'] = 'true'
        return await self._update(xml, query, timeout=timeout)

    async def add_many(self, docs: Iterable[dict[str, Any]], **kwargs: Any) -> Any:
        """Async add multiple documents."""
        from xml.sax.saxutils import escape, quoteattr
        commit = kwargs.pop('commit', self.always_commit)
        timeout = kwargs.pop('timeout', None)
        lst = ['<add>']
        for doc in docs:
            lst.append('<doc>')
            for field, value in doc.items():
                if value is None:
                    continue
                if isinstance(value, (list, tuple, set)):
                    for v in value:
                        lst.append('<field name=%s>%s</field>' % (quoteattr(field), escape(str(v))))
                else:
                    lst.append('<field name=%s>%s</field>' % (quoteattr(field), escape(str(value))))
            lst.append('</doc>')
        lst.append('</add>')
        xml = ''.join(lst)
        query: dict[str, str] = {}
        if commit:
            query['commit'] = 'true'
        return await self._update(xml, query, timeout=timeout)

    async def delete(self, id: Any = None, **kwargs: Any) -> Any:
        """Async delete by id."""
        from xml.sax.saxutils import escape
        commit = kwargs.pop('commit', self.always_commit)
        timeout = kwargs.pop('timeout', None)
        xml = '<delete><id>%s</id></delete>' % escape(str(id))
        query: dict[str, str] = {}
        if commit:
            query['commit'] = 'true'
        return await self._update(xml, query, timeout=timeout)

    async def delete_query(self, q: str, **kwargs: Any) -> Any:
        """Async delete by query."""
        from xml.sax.saxutils import escape
        commit = kwargs.pop('commit', self.always_commit)
        timeout = kwargs.pop('timeout', None)
        xml = '<delete><query>%s</query></delete>' % escape(q)
        query: dict[str, str] = {}
        if commit:
            query['commit'] = 'true'
        return await self._update(xml, query, timeout=timeout)

    async def commit(self, **kwargs: Any) -> str:
        """Async commit."""
        soft_commit = kwargs.pop('soft_commit', False)
        if soft_commit:
            return await self._update('<commit softCommit="true"/>')
        return await self._update('<commit />')

    async def get(self, id: str | None = None, ids: list[str] | None = None,
                  fields: list[str] | None = None,
                  model: type[Any] | None = None) -> Any:
        """Async Real-time Get."""
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
        data = json.loads(rsp.text)
        if id is not None:
            result = data.get('doc')
            if result is not None and model is not None:
                return model.model_validate(result)
            return result
        docs = data.get('response', {}).get('docs', [])
        if model is not None:
            return [model.model_validate(d) for d in docs]
        return docs
