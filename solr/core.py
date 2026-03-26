from __future__ import annotations

import re
import json
import socket
import datetime
import logging
import warnings
import base64
import http.client as httplib
import urllib.parse as urlparse
import urllib.parse as urllib
from io import StringIO
from typing import Any, Iterable
from xml.sax.saxutils import escape, quoteattr

from .exceptions import SolrException, SolrVersionError
from .utils import (
    UTC, utc_to_string, utc_from_string, qs_from_items, strify,
    check_response_status, read_response, committing, requires_version,
)
from .response import Response, Results
from .parsers import parse_json_response, parse_query_response

__version__ = "1.0.7"

__all__ = ['SolrException', 'SolrVersionError', 'Solr',
           'Response', 'SearchHandler']


# ===================================================================
# Connection Objects
# ===================================================================

class Solr:

    def __init__(self, url: str,
                 persistent: bool = True,
                 timeout: float | None = None,
                 ssl_key: str | None = None,
                 ssl_cert: str | None = None,
                 http_user: str | None = None,
                 http_pass: str | None = None,
                 post_headers: dict[str, str] | None = None,
                 max_retries: int = 3,
                 always_commit: bool = False,
                 response_format: str = 'json',
                 debug: bool = False) -> None:

        self.scheme, self.host, self.path = urlparse.urlparse(url, 'http')[:3]
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

        assert self.max_retries >= 0

        self.conn: httplib.HTTPConnection | httplib.HTTPSConnection
        if self.scheme == 'https':
            self.conn = httplib.HTTPSConnection(
                self.host, key_file=ssl_key, cert_file=ssl_cert,
                timeout=self.timeout)
        else:
            self.conn = httplib.HTTPConnection(
                self.host, timeout=self.timeout)

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

        if http_user is not None and http_pass is not None:
            http_auth = http_user + ':' + http_pass
            http_auth = 'Basic ' + base64.b64encode(http_auth.encode('utf-8')).decode('utf-8').strip()
            self.auth_headers: dict[str, str] = {'Authorization': http_auth}
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
        self.server_version = self._detect_version()

    def close(self) -> None:
        """Close the underlying HTTP(S) connection."""
        self.conn.close()

    def ping(self) -> bool:
        """Ping the Solr server. Returns True if reachable, False otherwise."""
        base_paths = [self.path]
        parent = self.path.rsplit('/', 1)[0]
        if parent and parent != self.path:
            base_paths.append(parent)
        for base in base_paths:
            try:
                rsp = self._get(base + '/admin/ping?wt=json')
                data = rsp.read().decode('utf-8')
                return '"OK"' in data or '"status":"OK"' in data
            except Exception:
                pass
        return False

    def _get(self, path: str) -> httplib.HTTPResponse:
        """Issue a GET request and return the response object."""
        _headers = self.auth_headers.copy()
        self.conn.request('GET', path, None, _headers)
        return check_response_status(self.conn.getresponse())

    def _detect_version(self) -> tuple[int, ...]:
        """Detect the Solr server version. Returns a tuple, e.g. (9, 4, 1)."""
        base_paths = [self.path]
        parent = self.path.rsplit('/', 1)[0]
        if parent and parent != self.path:
            base_paths.append(parent)

        for base in base_paths:
            try:
                rsp = self._get(base + '/admin/info/system?wt=json')
                data = json.loads(rsp.read().decode('utf-8'))
                ver_str = data['lucene']['solr-spec-version']
                return tuple(int(x) for x in ver_str.split('.')[:3])
            except Exception:
                pass

        for base in base_paths:
            try:
                rsp = self._get(base + '/admin/info/system?wt=xml')
                raw = rsp.read().decode('utf-8')
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
    def add(self, doc: dict[str, Any]) -> str:
        """Add a document to the Solr server."""
        lst = ['<add>']
        self.__add(lst, doc)
        lst.append('</add>')
        return ''.join(lst)

    @committing
    def add_many(self, docs: Iterable[dict[str, Any]]) -> str:
        """Add several documents to the Solr server."""
        lst = ['<add>']
        for doc in docs:
            self.__add(lst, doc)
        lst.append('</add>')
        return ''.join(lst)

    def commit(self, wait_flush: bool = True, wait_searcher: bool = True, _optimize: bool = False) -> str:
        """Issue a commit command to the Solr server."""
        verb = "optimize" if _optimize else "commit"
        return self._commit(verb, wait_flush, wait_searcher)

    def optimize(self, wait_flush: bool = True, wait_searcher: bool = True) -> str:
        """Issue an optimize command to the Solr server."""
        return self._commit("optimize", wait_flush, wait_searcher)

    def _commit(self, verb: str, wait_flush: bool, wait_searcher: bool) -> str:
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

    def _update(self, request: str, query: dict[str, str] | None = None) -> str:
        selector = '%s/update%s' % (self.path, qs_from_items(query))  # type: ignore[arg-type]
        try:
            rsp = self._post(selector, request, self.xmlheaders)
            data = read_response(rsp)
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
                raise SolrException(rsp.status, reason)
        return data

    def __add(self, lst: list[str], fields: dict[str, Any]) -> None:
        lst.append('<doc>')
        for field, value in fields.items():
            if not isinstance(value, (list, tuple, set)):
                values: list[Any] = [value]
            else:
                values = list(value)

            for value in values:
                if value is None:
                    continue
                if isinstance(value, datetime.datetime):
                    value = utc_to_string(value)
                elif isinstance(value, datetime.date):
                    value = datetime.datetime.combine(
                        value, datetime.time(tzinfo=UTC()))
                    value = utc_to_string(value)
                elif isinstance(value, bool):
                    value = value and 'true' or 'false'

                lst.append('<field name=%s>%s</field>' % (
                    (quoteattr(field),
                    escape(str(value)))))
        lst.append('</doc>')

    def _delete(self, id: Any = None, ids: list[Any] | None = None, queries: list[str] | None = None) -> str | None:
        if not ids:
            ids = []
        if id is not None:
            ids.insert(0, id)
        lst: list[str] = []
        for id in ids:
            lst.append('<id>%s</id>\n' % escape(str(id)))
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
        self.reconnects += 1
        self.close()
        self.conn.connect()

    def _post(self, url: str, body: str, headers: dict[str, str]) -> httplib.HTTPResponse:  # type: ignore[return]
        _headers = self.auth_headers.copy()
        _headers.update(headers)
        attempts = self.max_retries + 1
        while attempts > 0:
            try:
                self.conn.request('POST', url, body.encode('UTF-8'), _headers)
                return check_response_status(self.conn.getresponse())
            except (socket.error,
                    httplib.ImproperConnectionState,
                    httplib.BadStatusLine):
                self._reconnect()
                attempts -= 1
                if attempts <= 0:
                    raise


class SearchHandler:

    def __init__(self, conn: Solr, relpath: str = "/select", arg_separator: str = "_") -> None:
        self.conn = conn
        self.selector = conn.path + relpath
        self.arg_separator = arg_separator

    def __call__(self, q: str | None = None, fields: str | Iterable[str] | None = None,
                 highlight: bool | str | Iterable[str] | None = None,
                 score: bool = True, sort: str | Iterable[str] | None = None,
                 sort_order: str = "asc", **params: Any) -> Response | None:
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
                    params['hl_fl'] = [fields]
                else:
                    params['hl_fl'] = ",".join(fields)

        if q is not None:
            params['q'] = q

        fl: str
        if fields:
            if isinstance(fields, str):
                fl = fields
            else:
                fl = ",".join(fields)
        else:
            fl = '*'

        if sort:
            if not sort_order or sort_order not in ("asc", "desc"):
                raise ValueError("sort_order must be 'asc' or 'desc'")
            if isinstance(sort, str):
                sort_list = [f.strip() for f in sort.split(",")]
            else:
                sort_list = list(sort)
            sorting = []
            for e in sort_list:
                if not (e.endswith("asc") or e.endswith("desc")):
                    sorting.append("%s %s" % (e, sort_order))
                else:
                    sorting.append(e)
            params['sort'] = ",".join(sorting)

        if score and 'score' not in fl.replace(',', ' ').split():
            fl += ',score'

        params['fl'] = fl

        if self.conn.response_format == 'json':
            params['wt'] = 'json'
            raw = self.raw(**params)
            data = json.loads(raw)
            return parse_json_response(data, params, self)
        else:
            params['version'] = self.conn.response_version
            params['wt'] = 'standard'
            xml = self.raw(**params)
            return parse_query_response(StringIO(xml), params, self)  # type: ignore[no-any-return]

    def raw(self, **params: Any) -> str:
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
            rsp = conn._post(self.selector, request, conn.form_headers)
            data = read_response(rsp)
            if conn.debug:
                logging.info("solrpy got response: %s" % data)
        finally:
            if not conn.persistent:
                conn.close()

        return data
