from __future__ import annotations

import gzip
import datetime
import http.client as httplib
import urllib.parse as urllib
from typing import Any, Callable, TYPE_CHECKING

from .exceptions import SolrException, SolrVersionError

if TYPE_CHECKING:
    from .core import Solr


class UTC(datetime.tzinfo):
    """UTC timezone."""

    def utcoffset(self, dt: datetime.datetime | None) -> datetime.timedelta:
        return datetime.timedelta(0)

    def tzname(self, dt: datetime.datetime | None) -> str:
        return "UTC"

    def dst(self, dt: datetime.datetime | None) -> datetime.timedelta:
        return datetime.timedelta(0)


utc = UTC()


def utc_to_string(value: datetime.datetime) -> str:
    """Convert datetimes to the subset of ISO 8601 that Solr expects."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=utc)
    result = value.astimezone(utc).isoformat()
    if '+' in result:
        result = result.split('+')[0]
    result += 'Z'
    return result


def utc_from_string(value: str) -> datetime.datetime:
    """Parse a string representing an ISO 8601 date from Solr."""
    try:
        if not value.endswith('Z') and value[10] == 'T':
            raise ValueError(value)
        year = int(value[0:4])
        month = int(value[5:7])
        day = int(value[8:10])
        hour = int(value[11:13])
        minute = int(value[14:16])
        microseconds = int(float(value[17:-1]) * 1000000.0)
        second, microsecond = divmod(microseconds, 1000000)
        return datetime.datetime(year, month, day, hour,
            minute, second, microsecond, utc)
    except ValueError:
        raise ValueError("'%s' is not a valid ISO 8601 Solr date" % value)


def qs_from_items(query: dict[str, str | list[str]] | None) -> str:
    """Build a query string from a dict."""
    qs = ''
    if query:
        sep = '?'
        for k, v in query.items():
            k = urllib.quote(k)
            if isinstance(v, str):
                v = [v]
            for s in v:
                qs += "%s%s=%s" % (sep, k, urllib.quote_plus(s))
                sep = '&'
    return qs


def strify(s: Any) -> str:
    return str(s)


def check_response_status(response: httplib.HTTPResponse) -> httplib.HTTPResponse:
    if response.status != 200:
        ex = SolrException(response.status, response.reason)
        try:
            ex.body = response.read()
        except Exception:
            pass
        raise ex
    return response


def read_response(response: httplib.HTTPResponse) -> str:
    """Read an HTTP response body, decompressing gzip if needed."""
    data = response.read()
    if response.getheader('Content-Encoding', '') == 'gzip':
        data = gzip.decompress(data)
    return data.decode('utf-8')


def requires_version(*min_version: int) -> Callable[..., Any]:
    """Decorator that raises SolrVersionError if server_version < min_version."""

    def decorator(function: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(self: Solr, *args: Any, **kw: Any) -> Any:
            if self.server_version < min_version:
                raise SolrVersionError(
                    function.__name__, min_version, self.server_version)
            return function(self, *args, **kw)
        wrapper.__doc__ = function.__doc__
        wrapper.__name__ = function.__name__
        return wrapper
    return decorator


def committing(function: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that handles commit/optimize control arguments."""

    def wrapper(self: Solr, *args: Any, **kw: Any) -> Any:
        default_commit = getattr(self, 'always_commit', False)
        commit = kw.pop("commit", default_commit)
        optimize = kw.pop("optimize", False)
        query: dict[str, str] = {}
        if commit or optimize:
            if optimize:
                query["optimize"] = "true"
            elif commit:
                query["commit"] = "true"
            wait_searcher = kw.pop("wait_searcher", True)
            wait_flush = kw.pop("wait_flush", True)
            if not wait_searcher:
                query["waitSearcher"] = "false"
            if not wait_flush:
                query["waitFlush"] = "false"
                query["waitSearcher"] = "false"
        elif "wait_flush" in kw:
            raise TypeError(
                "wait_flush cannot be specified without commit or optimize")
        elif "wait_searcher" in kw:
            raise TypeError(
                "wait_searcher cannot be specified without commit or optimize")
        content = function(self, *args, **kw)
        if content:
            return self._update(content, query)

    wrapper.__doc__ = function.__doc__
    wrapper.__name__ = function.__name__
    return wrapper
