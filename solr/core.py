from __future__ import annotations

import re
import json
import datetime
import logging
import warnings
import base64
import urllib.parse as urllib
import httpx
from io import StringIO
from typing import Any, Iterable, Iterator
from xml.sax.saxutils import escape, quoteattr

from .exceptions import SolrException, SolrVersionError
from .utils import (
    UTC, utc_to_string, utc_from_string, qs_from_items, strify,
    committing, requires_version, serialize_value, solr_json_default,
)
from .response import Response, Results
from .parsers import parse_json_response, parse_query_response

__version__ = "2.0.8a"

__all__ = ['SolrException', 'SolrVersionError', 'Solr',
           'Response', 'SearchHandler']


# ===================================================================
# Connection Objects
# ===================================================================

class Solr:
    """A connection to a Solr server.

    Provides CRUD operations, commit/optimize, version detection,
    and the ``select`` search handler.  Optional features (Schema API,
    MoreLikeThis, Suggest, Extract, etc.) are created externally via
    companion classes that accept a ``Solr`` instance.
    """

    def __init__(self, url: str,
                 persistent: bool = True,
                 timeout: float | None = None,
                 ssl_key: str | None = None,
                 ssl_cert: str | None = None,
                 http_user: str | None = None,
                 http_pass: str | None = None,
                 post_headers: dict[str, str] | None = None,
                 max_retries: int = 3,
                 retry_delay: float = 0.1,
                 always_commit: bool = False,
                 response_format: str = 'json',
                 auth_token: str | None = None,
                 auth: Any = None,
                 debug: bool = False,
                 solr_version: tuple[int, ...] | None = None) -> None:
        """
        Connect to the Solr instance at *url*.

        :param url: URI pointing to the Solr instance, e.g.
            ``http://localhost:8983/solr`` or
            ``http://localhost:8983/solr/mycore``.
        :param persistent: Keep a persistent HTTP connection open.
        :param timeout: Timeout in seconds for server responses.
        :param ssl_key: PEM key file for SSL client authentication.
        :param ssl_cert: PEM certificate file for SSL client authentication.
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
        :param solr_version: Override the detected Solr version, e.g. ``(9, 4, 1)``.
            Skips autodetection entirely.
        """

        self.scheme, self.host, self.path = urllib.urlparse(url, 'http')[:3]
        self.url = url

        assert self.scheme in ('http', 'https')

        # Validate URL path contains /solr
        path_parts = self.path.rstrip('/').split('/')
        if 'solr' not in path_parts:
            warnings.warn(
                "solrpy: URL '%s' does not contain '/solr' in its path. "
                "Expected format: http://host:port/solr or "
                "http://host:port/solr/<core>. "
                "Solr 10.0+ requires the URL to end with '/solr'."
                % url,
                UserWarning,
                stacklevel=2,
            )

        self.persistent = persistent
        self.reconnects = 0
        self.timeout = timeout
        self.ssl_key = ssl_key
        self.ssl_cert = ssl_cert
        self.max_retries = int(max_retries)
        self.retry_delay = retry_delay

        assert self.max_retries >= 0

        base_url = '%s://%s' % (self.scheme, self.host)
        self._client_kwargs: dict[str, Any] = {
            'base_url': base_url,
            'timeout': self.timeout,
            'follow_redirects': True,
        }
        if self.scheme == 'https' and (ssl_cert or ssl_key):
            if ssl_key and not ssl_cert:
                raise ValueError("ssl_cert is required when ssl_key is provided")
            self._client_kwargs['cert'] = (ssl_cert, ssl_key) if ssl_key else ssl_cert
        self.__client: httpx.Client | None = None

        self.response_version = 2.2

        if post_headers is None:
            post_headers = {}

        self.xmlheaders: dict[str, str] = {
            'Content-Type': 'text/xml; charset=utf-8',
            'Accept-Encoding': 'gzip',
        }
        self.xmlheaders.update(post_headers)
        if not self.persistent:
            self.xmlheaders['Connection'] = 'close'

        self.form_headers: dict[str, str] = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
            'Accept-Encoding': 'gzip',
        }
        self.form_headers.update(post_headers)

        self._auth_callable = auth

        if auth is not None:
            # Dynamic auth — headers resolved per-request via _get_auth_headers()
            self.auth_headers: dict[str, str] = {}
        elif auth_token is not None:
            self.auth_headers = {'Authorization': 'Bearer ' + auth_token}
        elif http_user is not None and http_pass is not None:
            http_auth = http_user + ':' + http_pass
            http_auth = 'Basic ' + base64.b64encode(http_auth.encode('utf-8')).decode('utf-8').strip()
            self.auth_headers = {'Authorization': http_auth}
        else:
            self.auth_headers = {}

        if not self.persistent:
            self.form_headers['Connection'] = 'close'

        if response_format not in ('xml', 'json'):
            raise ValueError("response_format must be 'xml' or 'json', got %r" % response_format)
        self.response_format = response_format
        self.always_commit = always_commit
        self.debug = debug
        self.select = SearchHandler(self, "/select")
        self._server_version: tuple[int, ...] | None = solr_version

    @property
    def _client(self) -> httpx.Client:
        """Lazily create the httpx.Client on first use."""
        if self.__client is None:
            self.__client = httpx.Client(**self._client_kwargs)
        return self.__client

    @_client.setter
    def _client(self, value: httpx.Client) -> None:
        self.__client = value

    @property
    def server_version(self) -> tuple[int, ...]:
        """Lazily detect and cache the Solr server version."""
        if self._server_version is None:
            self._server_version = self._detect_version()
        return self._server_version

    @server_version.setter
    def server_version(self, value: tuple[int, ...]) -> None:
        self._server_version = value

    def close(self) -> None:
        """Close the underlying HTTP(S) connection."""
        if self.__client is None:
            # Create a pre-closed client so _client.is_closed is True
            self.__client = httpx.Client(**self._client_kwargs)
        self.__client.close()

    def ping(self) -> bool:
        """Ping the Solr server. Returns True if reachable, False otherwise."""
        base_paths = [self.path]
        parent = self.path.rsplit('/', 1)[0]
        if parent and parent != self.path:
            base_paths.append(parent)
        for base in base_paths:
            try:
                rsp = self._get(base + '/admin/ping?wt=json')
                data = rsp.text
                return '"OK"' in data or '"status":"OK"' in data
            except Exception:
                pass
        return False

    def _get_auth_headers(self) -> dict[str, str]:
        """Return auth headers, calling the auth callable if set."""
        if self._auth_callable is not None:
            result: dict[str, str] = self._auth_callable()
            return result
        return self.auth_headers.copy()

    def _get(self, path: str) -> httpx.Response:
        """Issue a GET request and return the httpx response."""
        _headers = self._get_auth_headers()
        rsp = self._client.get(path, headers=_headers)
        if rsp.status_code != 200:
            from .exceptions import SolrException
            raise SolrException(rsp.status_code, rsp.reason_phrase, rsp.text)
        return rsp

    def _detect_version(self) -> tuple[int, ...]:
        """Detect the Solr server version. Returns a tuple, e.g. (9, 4, 1)."""
        base_paths = [self.path]
        parent = self.path.rsplit('/', 1)[0]
        if parent and parent != self.path:
            base_paths.append(parent)

        for base in base_paths:
            try:
                rsp = self._get(base + '/admin/info/system?wt=json')
                data = json.loads(rsp.text)
                ver_str = data['lucene']['solr-spec-version']
                return tuple(int(x) for x in ver_str.split('.')[:3])
            except Exception:
                pass

        for base in base_paths:
            try:
                rsp = self._get(base + '/admin/info/system?wt=xml')
                raw = rsp.text
                m = re.search(r'solr-spec-version[^>]*>([0-9.]+)', raw)
                if m:
                    return tuple(int(x) for x in m.group(1).split('.')[:3])
            except Exception:
                pass

        logging.warning("solrpy: could not detect Solr version, assuming 1.2.0")
        return (1, 2, 0)

    # Update interface.

    @committing
    def delete(self, id: Any = None, ids: list[Any] | None = None, queries: list[str] | None = None) -> str | None:
        """Delete documents by ids or queries."""
        return self._delete(id=id, ids=ids, queries=queries)

    @committing
    def delete_many(self, ids: list[Any]) -> str | None:
        """Delete documents using an iterable of ids."""
        return self._delete(ids=ids)

    @committing
    def delete_query(self, query: str) -> str | None:
        """Delete all documents identified by a query."""
        return self._delete(queries=[query])

    @committing
    def add(self, doc: dict[str, Any]) -> Any:
        """Add a document to the Solr server."""
        if self._use_json_updates:
            return [self.__doc_for_json(doc)]
        lst = ['<add>']
        self.__add(lst, doc)
        lst.append('</add>')
        return ''.join(lst)

    @committing
    def add_many(self, docs: Iterable[dict[str, Any]]) -> Any:
        """Add several documents to the Solr server."""
        if self._use_json_updates:
            return [self.__doc_for_json(d) for d in docs]
        lst = ['<add>']
        for doc in docs:
            self.__add(lst, doc)
        lst.append('</add>')
        return ''.join(lst)

    @committing
    @requires_version(4, 0)
    def atomic_update(self, doc: dict[str, Any]) -> Any:
        """Atomic (partial) update of a single document.

        Field values can be plain values (full replace) or dicts with a
        modifier key: ``set``, ``add``, ``remove``, ``removeregex``, ``inc``.
        Use ``{'set': None}`` to remove a field.

        Example::

            conn.atomic_update({
                'id': 'doc1',
                'title': {'set': 'New Title'},
                'count': {'inc': 1},
                'old_field': {'set': None},
            }, commit=True)
        """
        if self._use_json_updates:
            return [doc]
        lst = ['<add>']
        self.__atomic_update(lst, doc)
        lst.append('</add>')
        return ''.join(lst)

    @committing
    @requires_version(4, 0)
    def atomic_update_many(self, docs: Iterable[dict[str, Any]]) -> Any:
        """Atomic (partial) update of multiple documents."""
        if self._use_json_updates:
            return list(docs)
        lst = ['<add>']
        for doc in docs:
            self.__atomic_update(lst, doc)
        lst.append('</add>')
        return ''.join(lst)

    def __atomic_update(self, lst: list[str], fields: dict[str, Any]) -> None:
        """Append ``<doc>`` XML with atomic-update modifiers to *lst*."""
        lst.append('<doc>')
        for field, value in fields.items():
            if field == 'id':
                lst.append('<field name="id">%s</field>' % escape(str(value)))
                continue
            if isinstance(value, dict):
                modifier, mod_value = next(iter(value.items()))
                serialized = serialize_value(mod_value)
                if serialized is None:
                    lst.append('<field name=%s update=%s null="true"/>' % (
                        quoteattr(field), quoteattr(modifier)))
                else:
                    lst.append('<field name=%s update=%s>%s</field>' % (
                        quoteattr(field), quoteattr(modifier),
                        escape(serialized)))
            else:
                serialized = serialize_value(value)
                if serialized is not None:
                    lst.append('<field name=%s>%s</field>' % (
                        quoteattr(field), escape(serialized)))
        lst.append('</doc>')

    @requires_version(4, 0)
    def get(self, id: str | None = None, ids: list[str] | None = None,
            fields: list[str] | None = None,
            model: type[Any] | None = None) -> Any:
        """Real-time Get via the /get handler (Solr 4.0+).

        Returns a single doc dict for ``id``, a list for ``ids``,
        or ``None`` if a single doc is not found.

        :param model: Optional Pydantic model class. When provided, each
            returned document is converted via ``model.model_validate(doc)``.
        """
        if id is None and ids is None:
            raise ValueError("Either id or ids must be specified.")
        params: dict[str, str] = {'wt': 'json'}
        if id is not None:
            params['id'] = str(id)
        elif ids is not None:
            params['ids'] = ','.join(str(i) for i in ids)
        if fields:
            params['fl'] = ','.join(fields)

        import urllib.parse
        qs = urllib.parse.urlencode(params)
        selector = '%s/get?%s' % (self.path, qs)
        rsp = self._get(selector)
        data = json.loads(rsp.content)

        if id is not None:
            result: dict[str, Any] | None = data.get('doc')
            if result is not None and model is not None:
                return model.model_validate(result)
            return result
        docs: list[dict[str, Any]] = data.get('response', {}).get('docs', [])
        if model is not None:
            return [model.model_validate(d) for d in docs]
        return docs

    def stream(self, expr: Any, model: type[Any] | None = None) -> Iterator[dict[str, Any]]:
        """Execute a streaming expression via the ``/stream`` handler (Solr 5.0+).

        Returns an iterator of tuple dicts. Skips the final EOF marker.

        :param expr: A :class:`~solr.stream.StreamExpression` or string.
        :param model: Optional Pydantic model for automatic conversion.
        :returns: Iterator of result dicts (or model instances if model given).
        """
        if self.server_version < (5, 0):
            from .exceptions import SolrVersionError
            raise SolrVersionError("stream", (5, 0), self.server_version)

        import urllib.parse
        qs = urllib.parse.urlencode({'expr': str(expr)})
        selector = '%s/stream?%s' % (self.path, qs)
        rsp = self._get(selector)
        data = json.loads(rsp.content)

        docs = data.get('result-set', {}).get('docs', [])
        for doc in docs:
            if 'EOF' in doc:
                break
            if model is not None:
                yield model.model_validate(doc)
            else:
                yield doc

    def iter_cursor(self, q: str, sort: str | None = None,
                    rows: int = 100, **params: Any) -> Iterator[Response]:
        """Iterate through all results using cursor-based pagination.

        Yields Response objects for each batch. Requires ``sort`` to
        include a uniqueKey field.

        :param \\**params: Additional Solr query parameters forwarded to the
            ``select`` handler (e.g., ``fq``, ``fl``).

        Example::

            for batch in conn.iter_cursor('*:*', sort='id asc', rows=100):
                for doc in batch.results:
                    process(doc)
        """
        if not sort:
            raise ValueError("sort is required for cursor pagination "
                             "(must include uniqueKey field)")
        params['sort'] = sort
        params['rows'] = rows
        params['cursorMark'] = '*'
        first: Response | None = self.select(q, **params)
        if first is None:
            return
        yield first
        resp: Response | None = first
        while resp is not None:
            resp = resp.cursor_next()
            if resp is not None:
                yield resp

    def commit(self, wait_flush: bool = True, wait_searcher: bool = True,
               _optimize: bool = False, soft_commit: bool = False) -> str:
        """Issue a commit command to the Solr server.

        :param wait_flush: Block until index changes are flushed to disk.
        :param wait_searcher: Block until a new searcher is opened and
            registered as the main query searcher.
        :param _optimize: When ``True``, issue an optimize instead of a
            plain commit.
        :param soft_commit: Perform a soft commit (Solr 4.0+). Changes are
            visible in search but not yet persisted to disk.
        """
        if soft_commit:
            if self.server_version < (4, 0):
                raise SolrVersionError("soft_commit", (4, 0), self.server_version)
            return self._update('<commit softCommit="true"/>')
        verb = "optimize" if _optimize else "commit"
        return self._commit(verb, wait_flush, wait_searcher)

    def optimize(self, wait_flush: bool = True, wait_searcher: bool = True) -> str:
        """Issue an optimize command to the Solr server.

        :param wait_flush: Block until index changes are flushed to disk.
        :param wait_searcher: Block until a new searcher is opened and
            registered as the main query searcher.
        """
        return self._commit("optimize", wait_flush, wait_searcher)

    def _commit(self, verb: str, wait_flush: bool, wait_searcher: bool) -> str:
        """Build and send a commit/optimize XML command."""
        if not wait_searcher:
            if not wait_flush:
                options = 'waitFlush="false" waitSearcher="false"'
            else:
                options = 'waitSearcher="false"'
        else:
            options = ''
        xstr = '<%s %s/>' % (verb, options)
        return self._update(xstr)

    # Helper methods.

    @property
    def _use_json_updates(self) -> bool:
        """Use JSON update path when Solr 4.0+ is detected."""
        return self.server_version >= (4, 0)

    def _json_update(self, body: Any, query: dict[str, str] | None = None,
                     timeout: float | None = None) -> str:
        """Send a JSON update request to Solr and return the response body."""
        selector = '%s/update%s' % (self.path, qs_from_items(query))  # type: ignore[arg-type]
        payload = json.dumps(body, default=solr_json_default)
        headers = {'Content-Type': 'application/json; charset=utf-8'}
        try:
            rsp = self._post(selector, payload, headers, timeout=timeout)
            return rsp.text
        finally:
            if not self.persistent:
                self.close()

    def _update(self, request: str, query: dict[str, str] | None = None, timeout: float | None = None) -> str:
        """Send an update XML request to Solr and return the response body."""
        selector = '%s/update%s' % (self.path, qs_from_items(query))  # type: ignore[arg-type]
        try:
            rsp = self._post(selector, request, self.xmlheaders, timeout=timeout)
            data = rsp.text
        finally:
            if not self.persistent:
                self.close()

        starts = data.startswith
        if starts('<result status="') and not starts('<result status="0"'):
            from xml.dom.minidom import parseString
            parsed = parseString(data)
            doc_elem = parsed.documentElement
            status = doc_elem.getAttribute('status')  # type: ignore[union-attr]
            if status != "0":
                first_child = doc_elem.firstChild  # type: ignore[union-attr]
                reason = first_child.nodeValue if first_child else None
                raise SolrException(rsp.status_code, reason)
        return data

    def __doc_for_json(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Build a JSON-ready document dict, omitting None values."""
        result: dict[str, Any] = {}
        for field, value in fields.items():
            if value is None:
                continue
            result[field] = value
        return result

    def __add(self, lst: list[str], fields: dict[str, Any]) -> None:
        """Append ``<doc>`` XML for a single document to *lst*."""
        lst.append('<doc>')
        for field, value in fields.items():
            if not isinstance(value, (list, tuple, set)):
                values: list[Any] = [value]
            else:
                values = list(value)

            for value in values:
                serialized = serialize_value(value)
                if serialized is None:
                    continue
                lst.append('<field name=%s>%s</field>' % (
                    quoteattr(field), escape(serialized)))
        lst.append('</doc>')

    def _delete(self, id: Any = None, ids: list[Any] | None = None, queries: list[str] | None = None) -> str | None:
        """Build a ``<delete>`` XML fragment from ids and/or queries."""
        if not ids:
            ids = []
        if id is not None:
            ids.insert(0, id)
        lst: list[str] = []
        for doc_id in ids:
            lst.append('<id>%s</id>\n' % escape(str(doc_id)))
        for query in (queries or ()):
            lst.append('<query>%s</query>\n' % escape(str(query)))
        if lst:
            lst.insert(0, '<delete>\n')
            lst.append('</delete>')
            return ''.join(lst)
        return None

    def __repr__(self) -> str:
        return (
            '<%s (url=%s, persistent=%s, post_headers=%s, reconnects=%s)>'
            % (self.__class__.__name__,
               self.url, self.persistent,
               self.xmlheaders, self.reconnects))

    def _reconnect(self) -> None:
        """Close and re-create the httpx client."""
        self.reconnects += 1
        if self.__client is not None:
            self.__client.close()
        self.__client = httpx.Client(**self._client_kwargs)

    def _post(self, url: str, body: str | bytes, headers: dict[str, str], timeout: float | None = None) -> httpx.Response:
        """POST data to Solr with retry and exponential backoff."""
        import time
        _logger = logging.getLogger('solr')
        _headers = self._get_auth_headers()
        _headers.update(headers)
        raw_body: bytes = body if isinstance(body, bytes) else body.encode('UTF-8')
        attempts = self.max_retries + 1
        retry_num = 0
        while attempts > 0:
            try:
                kwargs: dict[str, Any] = {'headers': _headers, 'content': raw_body}
                if timeout is not None:
                    kwargs['timeout'] = timeout
                rsp = self._client.post(url, **kwargs)
                if rsp.status_code != 200:
                    from .exceptions import SolrException
                    raise SolrException(rsp.status_code, rsp.reason_phrase, rsp.text)
                return rsp
            except (httpx.ConnectError, httpx.ReadError, httpx.WriteError):
                self._reconnect()
                attempts -= 1
                if attempts <= 0:
                    raise
                retry_num += 1
                delay = self.retry_delay * (2 ** (retry_num - 1))
                _logger.warning(
                    "Retry %d/%d for %s (delay=%.2fs)",
                    retry_num, self.max_retries, url, delay,
                )
                time.sleep(delay)
        raise RuntimeError("Unreachable")


class SearchHandler:
    """Provides access to a named Solr search handler.

    The ``select`` attribute on :class:`Solr` instances is a ``SearchHandler``
    bound to ``/select``.  Additional handlers can be created for custom
    endpoints.
    """

    def __init__(self, conn: Solr, relpath: str = "/select", arg_separator: str = "_") -> None:
        self.conn = conn
        self.selector = conn.path + relpath
        self.arg_separator = arg_separator

    def __call__(self, q: str | None = None, fields: str | Iterable[str] | None = None,
                 highlight: bool | str | Iterable[str] | None = None,
                 score: bool = True, sort: str | Iterable[str] | None = None,
                 sort_order: str = "asc",
                 json_facet: dict[str, Any] | None = None,
                 facets: list[Any] | None = None,
                 model: type[Any] | None = None,
                 **params: Any) -> Response | None:
        """Execute a search query against Solr.

        Optional parameters can be passed in using underscore notation
        for dotted Solr parameter names (e.g., ``hl_simple_post``).

        Returns a :class:`Response` instance.

        :param highlight: Enable highlighting. Pass ``True`` to highlight
            on *fields*, a field name string, or an iterable of field names.
        :param score: Include the ``score`` pseudo-field in results
            (default ``True``).
        :param sort_order: Default sort direction (``"asc"`` or ``"desc"``)
            applied to sort fields that do not already specify a direction.
        :param json_facet: A JSON facet dict sent as the ``json.facet``
            parameter (Solr 5.0+).
        :param facets: A list of :class:`~solr.facet.Facet` objects whose
            parameters are merged into the query.
        :param model: Optional Pydantic model class. When provided, each
            result document is converted via ``model.model_validate(doc)``.
        :param \\**params: Additional Solr query parameters (e.g., ``fq``,
            ``rows``, ``start``). Underscores in names are converted to dots.
        """
        if json_facet is not None:
            if self.conn.server_version < (5, 0):
                from .exceptions import SolrVersionError
                raise SolrVersionError("json_facet", (5, 0), self.conn.server_version)
            params['json.facet'] = json.dumps(json_facet)

        if facets is not None:
            for facet_obj in facets:
                for k, v in facet_obj.to_params().items():
                    if k in params and k in ('facet.field', 'facet.range',
                                              'facet.query', 'facet.pivot'):
                        existing = params[k]
                        if isinstance(existing, list):
                            existing.append(v)
                        else:
                            params[k] = [existing, v]
                    else:
                        params[k] = v

        group_param = params.get('group')
        if group_param is not None and str(group_param).lower() in ('true', '1', 'yes'):
            if self.conn.server_version < (3, 3):
                from .exceptions import SolrVersionError
                raise SolrVersionError("group", (3, 3), self.conn.server_version)

        if highlight:
            params['hl'] = 'true'
            if not isinstance(highlight, (bool, int, float)):
                if not isinstance(highlight, str):
                    highlight = ",".join(highlight)
                params['hl_fl'] = highlight
            else:
                if not fields:
                    raise ValueError("highlight is True and no fields were given")
                elif isinstance(fields, str):
                    params['hl_fl'] = fields
                else:
                    params['hl_fl'] = ",".join(fields)

        if q is not None:
            params['q'] = q

        fl: str
        if fields:
            if isinstance(fields, str):
                fl = fields
            else:
                fl = ",".join(str(f) for f in fields)
        else:
            fl = '*'

        if sort:
            if not sort_order or sort_order not in ("asc", "desc"):
                raise ValueError("sort_order must be 'asc' or 'desc'")
            if isinstance(sort, str):
                sort_list = [f.strip() for f in sort.split(",")]
            else:
                sort_list = [str(s) for s in sort]
            sorting = []
            for e in sort_list:
                if not (e.endswith(" asc") or e.endswith(" desc")):
                    sorting.append("%s %s" % (e, sort_order))
                else:
                    sorting.append(e)
            params['sort'] = ",".join(sorting)

        if score and 'score' not in fl.replace(',', ' ').split():
            fl += ',score'

        params['fl'] = fl

        timeout = params.pop('timeout', None)

        if self.conn.response_format == 'json':
            params['wt'] = 'json'
            data = self._raw_json(timeout=timeout, **params)
            resp = parse_json_response(data, params, self)
        else:
            if self.conn.server_version >= (7, 0):
                params['wt'] = 'xml'
            else:
                params['version'] = self.conn.response_version
                params['wt'] = 'standard'
            xml = self.raw(timeout=timeout, **params)
            resp = parse_query_response(StringIO(xml), params, self)

        if model is not None and resp is not None:
            resp.results = resp.as_models(model)
        return resp

    def raw(self, **params: Any) -> str:
        """Issue a raw query. No pre/post-processing on parameters or response."""
        timeout = params.pop('timeout', None)
        rsp = self._raw_request(timeout=timeout, **params)
        return rsp.text

    def _raw_json(self, **params: Any) -> dict[str, Any]:
        """Issue a query and return parsed JSON directly from bytes.

        Avoids the intermediate bytes→str→json decode that ``raw()`` +
        ``json.loads(str)`` would perform.
        """
        timeout = params.pop('timeout', None)
        rsp = self._raw_request(timeout=timeout, **params)
        result: dict[str, Any] = json.loads(rsp.content)
        return result

    def _raw_request(self, **params: Any) -> Any:
        """Issue a POST to the handler and return the raw httpx.Response."""
        timeout = params.pop('timeout', None)
        query = []
        for key, value in params.items():
            key = key.replace(self.arg_separator, '.')
            if isinstance(value, (list, tuple)):
                query.extend([(key, strify(v)) for v in value])
            else:
                query.append((key, strify(value)))
        request = urllib.urlencode(query, doseq=True)
        conn = self.conn
        if conn.debug:
            logging.info("solrpy request: %s" % request)

        try:
            rsp = conn._post(self.selector, request, conn.form_headers, timeout=timeout)
            if conn.debug:
                logging.info("solrpy got response: %s" % rsp.text)
        finally:
            if not conn.persistent:
                conn.close()

        return rsp
