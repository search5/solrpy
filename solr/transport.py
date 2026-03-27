"""HTTP transport abstraction for Solr communication.

All companion classes (SchemaAPI, Extract, Suggest, etc.) should use
this interface instead of calling Solr._get()/_post() directly.
This isolates the HTTP layer for future replacement (e.g., async in 2.0.2+).

Since 2.0.4, companion classes use :class:`DualTransport` which auto-detects
whether the connection is sync (:class:`~solr.core.Solr`) or async
(:class:`~solr.async_solr.AsyncSolr`) and delegates accordingly.
"""
from __future__ import annotations

import inspect
import json
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .core import Solr


def _chain(result_or_coro: Any, transform: Callable[[Any], Any]) -> Any:
    """Apply *transform* to a sync result, or chain it onto a coroutine.

    If *result_or_coro* is an awaitable (coroutine), returns a new coroutine
    that awaits the original and applies *transform* to its result.
    Otherwise, applies *transform* immediately and returns the value.

    This is the key building block for dual sync/async companion methods::

        raw = self._transport.get_json('/schema/fields')
        return _chain(raw, lambda d: d.get('fields', []))
    """
    if inspect.isawaitable(result_or_coro):
        async def _async() -> Any:
            data = await result_or_coro
            return transform(data)
        return _async()
    return transform(result_or_coro)


class SolrTransport:
    """Thin wrapper over Solr's HTTP methods.

    Companion classes receive this instead of a raw ``Solr`` reference,
    decoupling them from internal ``_get``/``_post`` signatures.

    Example::

        transport = SolrTransport(conn)
        data = transport.get_json('/schema/fields')
        transport.post_json('/schema', {'add-field': {...}})
    """

    def __init__(self, conn: Solr) -> None:
        """Initialize a sync transport.

        :param conn: A :class:`~solr.core.Solr` connection instance.
        """
        self._conn = conn

    @property
    def path(self) -> str:
        """Base path of the Solr core, e.g. ``/solr/core0``."""
        return self._conn.path

    @property
    def server_version(self) -> tuple[int, ...]:
        """Detected Solr server version tuple."""
        return self._conn.server_version

    # -- GET ----------------------------------------------------------------

    def get_raw(self, endpoint: str) -> bytes:
        """GET an endpoint and return raw bytes."""
        rsp = self._conn._get(self.path + endpoint)
        return rsp.content

    def get_json(self, endpoint: str) -> Any:
        """GET an endpoint and return parsed JSON."""
        rsp = self._conn._get(
            self.path + endpoint + ('&' if '?' in endpoint else '?') + 'wt=json')
        return rsp.json()

    # -- POST ---------------------------------------------------------------

    def post_json(self, endpoint: str, body: dict[str, Any] | list[Any]) -> dict[str, Any]:
        """POST JSON to an endpoint and return parsed JSON response."""
        payload = json.dumps(body)
        headers: dict[str, str] = {
            'Content-Type': 'application/json; charset=utf-8',
        }
        rsp = self._conn._post(self.path + endpoint, payload, headers)
        result: dict[str, Any] = rsp.json()
        return result

    def post_raw(self, endpoint: str, body: str | bytes,
                 headers: dict[str, str],
                 timeout: float | None = None) -> str:
        """POST raw data and return decoded response text.

        :param endpoint: URL path relative to the core (e.g. ``/update/extract``).
        :param body: Raw request body as a string or bytes.
        :param headers: HTTP headers to include in the request.
        :param timeout: Optional request timeout in seconds.
        """
        rsp = self._conn._post(self.path + endpoint, body, headers, timeout=timeout)
        return rsp.text


class AsyncTransport:
    """Async version of :class:`SolrTransport`.

    For use with :class:`~solr.async_solr.AsyncSolr`.
    """

    def __init__(self, conn: Any) -> None:
        """Initialize an async transport.

        :param conn: An :class:`~solr.async_solr.AsyncSolr` connection instance.
        """
        self._conn = conn

    @property
    def path(self) -> str:
        """Base path of the Solr core."""
        p: str = self._conn.path
        return p

    @property
    def server_version(self) -> tuple[int, ...]:
        """Detected Solr server version tuple."""
        v: tuple[int, ...] = self._conn.server_version
        return v

    async def get_raw(self, endpoint: str) -> bytes:
        """Async GET and return raw bytes."""
        rsp = await self._conn._get(self.path + endpoint)
        raw: bytes = rsp.content
        return raw

    async def get_json(self, endpoint: str) -> Any:
        """Async GET and return parsed JSON."""
        rsp = await self._conn._get(
            self.path + endpoint + ('&' if '?' in endpoint else '?') + 'wt=json')
        return rsp.json()

    async def post_json(self, endpoint: str, body: dict[str, Any] | list[Any]) -> dict[str, Any]:
        """Async POST JSON and return parsed JSON response."""
        payload = json.dumps(body)
        headers: dict[str, str] = {
            'Content-Type': 'application/json; charset=utf-8',
        }
        rsp = await self._conn._post(self.path + endpoint, payload, headers)
        result: dict[str, Any] = rsp.json()
        return result

    async def post_raw(self, endpoint: str, body: str | bytes,
                       headers: dict[str, str],
                       timeout: float | None = None) -> str:
        """Async POST raw data and return decoded response text.

        :param endpoint: URL path relative to the core (e.g. ``/update/extract``).
        :param body: Raw request body as a string or bytes.
        :param headers: HTTP headers to include in the request.
        :param timeout: Optional request timeout in seconds.
        """
        rsp = await self._conn._post(self.path + endpoint, body, headers, timeout=timeout)
        result: str = rsp.text
        return result


def _is_async_conn(conn: Any) -> bool:
    """Return True if *conn* is an :class:`~solr.async_solr.AsyncSolr`."""
    from .async_solr import AsyncSolr
    return isinstance(conn, AsyncSolr)


class DualTransport:
    """Transport that works with both :class:`~solr.core.Solr` and
    :class:`~solr.async_solr.AsyncSolr`.

    Methods mirror :class:`SolrTransport` / :class:`AsyncTransport`.
    In sync mode they return values directly; in async mode they return
    coroutines (to be ``await``-ed by the caller).

    Example::

        dt = DualTransport(conn)          # conn is Solr or AsyncSolr
        result = dt.get_json('/schema')   # dict (sync) or coroutine (async)
    """

    def __init__(self, conn: Any) -> None:
        """Initialize a dual transport that auto-detects sync or async mode.

        :param conn: A :class:`~solr.core.Solr` or
            :class:`~solr.async_solr.AsyncSolr` connection instance.
        """
        self.is_async: bool = _is_async_conn(conn)
        self._conn = conn
        if self.is_async:
            self._impl: SolrTransport | AsyncTransport = AsyncTransport(conn)
        else:
            self._impl = SolrTransport(conn)

    @property
    def path(self) -> str:
        """Base path of the Solr core."""
        return self._impl.path

    @property
    def server_version(self) -> tuple[int, ...]:
        """Detected Solr server version tuple."""
        return self._impl.server_version

    def get_raw(self, endpoint: str) -> Any:
        """GET and return raw bytes (sync) or coroutine (async)."""
        return self._impl.get_raw(endpoint)

    def get_json(self, endpoint: str) -> Any:
        """GET and return parsed JSON dict (sync) or coroutine (async)."""
        return self._impl.get_json(endpoint)

    def post_json(self, endpoint: str, body: dict[str, Any] | list[Any]) -> Any:
        """POST JSON and return parsed response (sync) or coroutine (async)."""
        return self._impl.post_json(endpoint, body)

    def post_raw(self, endpoint: str, body: str | bytes,
                 headers: dict[str, str],
                 timeout: float | None = None) -> Any:
        """POST raw data and return text (sync) or coroutine (async).

        :param endpoint: URL path relative to the core (e.g. ``/update/extract``).
        :param body: Raw request body as a string or bytes.
        :param headers: HTTP headers to include in the request.
        :param timeout: Optional request timeout in seconds.
        """
        return self._impl.post_raw(endpoint, body, headers, timeout=timeout)
