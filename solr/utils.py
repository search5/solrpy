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
        """Return UTC offset (zero)."""
        return datetime.timedelta(0)

    def tzname(self, dt: datetime.datetime | None) -> str:
        """Return timezone name."""
        return "UTC"

    def dst(self, dt: datetime.datetime | None) -> datetime.timedelta:
        """Return DST offset (zero)."""
        return datetime.timedelta(0)


utc = UTC()


def utc_to_string(value: datetime.datetime) -> str:
    """Convert datetimes to the subset of ISO 8601 that Solr expects.

    :param value: A :class:`~datetime.datetime` instance. If timezone-naive,
        it is assumed to be UTC.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=utc)
    result = value.astimezone(utc).isoformat()
    if '+' in result:
        result = result.split('+')[0]
    result += 'Z'
    return result


def solr_json_default(obj: Any) -> Any:
    """Custom JSON encoder for Solr update payloads.

    Handles ``datetime.datetime``, ``datetime.date``, ``set``, ``tuple``.
    ``bool``, ``int``, ``float``, ``str``, ``list``, ``dict`` are
    handled natively by :func:`json.dumps`.

    :param obj: The object to serialize. Must be a datetime, date, set, or
        tuple; otherwise :class:`TypeError` is raised.
    """
    if isinstance(obj, datetime.datetime):
        return utc_to_string(obj)
    if isinstance(obj, datetime.date):
        return utc_to_string(
            datetime.datetime.combine(obj, datetime.time(tzinfo=utc)))
    if isinstance(obj, (set, tuple)):
        return list(obj)
    raise TypeError("Object of type %s is not JSON serializable" % type(obj).__name__)


def serialize_value(value: Any) -> str | None:
    """Convert a Python value to a Solr-compatible string.

    Handles ``datetime.datetime``, ``datetime.date``, ``bool``, and
    ``None``.  All other types are converted via ``str()``.

    This is the single source of truth for type serialization, used by
    ``Solr.add()``, ``Solr.atomic_update()``, ``AsyncSolr.add()``, etc.

    :param value: The Python value to serialize.
    :returns: Serialized string, or ``None`` if *value* is ``None``.
    """
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return utc_to_string(value)
    if isinstance(value, datetime.date):
        return utc_to_string(
            datetime.datetime.combine(value, datetime.time(tzinfo=utc)))
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


def utc_from_string(value: str) -> datetime.datetime:
    """Parse a string representing an ISO 8601 date from Solr.

    Note: this doesn't process the entire ISO 8601 standard,
    only the specific format Solr promises to generate.

    :param value: An ISO 8601 date string ending with ``Z`` as returned
        by Solr (e.g. ``"2024-01-15T10:30:00Z"``).
    :raises ValueError: If *value* is not a valid Solr date string.
    """
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
    """Convert any value to a string for URL encoding."""
    return str(s)


def check_response_status(response: httplib.HTTPResponse) -> httplib.HTTPResponse:
    """Raise SolrException if the HTTP response status is not 200."""
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
    """Decorator that raises SolrVersionError if server_version < min_version.

    :param min_version: Minimum Solr version components (e.g. ``4, 7`` for
        Solr 4.7+).
    """

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
        timeout = kw.pop("timeout", None)
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
        if content is None:
            return None
        # JSON update path: content is a list/dict, not a string
        if isinstance(content, (list, dict)):
            return self._json_update(content, query, timeout=timeout)
        return self._update(content, query, timeout=timeout)

    wrapper.__doc__ = function.__doc__
    wrapper.__name__ = function.__name__
    return wrapper
