"""HTTP transport abstraction for Solr communication.

All companion classes (SchemaAPI, Extract, Suggest, etc.) should use
this interface instead of calling Solr._get()/_post() directly.
This isolates the HTTP layer for future replacement (e.g., httpx in 2.0.0).
"""
from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING

from .utils import check_response_status, read_response

if TYPE_CHECKING:
    from .core import Solr


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
        return rsp.read()

    def get_json(self, endpoint: str) -> Any:
        """GET an endpoint and return parsed JSON."""
        raw = self.get_raw(endpoint + ('&' if '?' in endpoint else '?') + 'wt=json')
        return json.loads(raw.decode('utf-8'))

    # -- POST ---------------------------------------------------------------

    def post_json(self, endpoint: str, body: dict[str, Any] | list[Any]) -> dict[str, Any]:
        """POST JSON to an endpoint and return parsed JSON response."""
        payload = json.dumps(body)
        headers: dict[str, str] = {
            'Content-Type': 'application/json; charset=utf-8',
        }
        rsp = self._conn._post(self.path + endpoint, payload, headers)
        result: dict[str, Any] = json.loads(read_response(rsp))
        return result

    def post_raw(self, endpoint: str, body: str | bytes,
                 headers: dict[str, str],
                 timeout: float | None = None) -> str:
        """POST raw data and return decoded response text."""
        rsp = self._conn._post(self.path + endpoint, body, headers, timeout=timeout)
        return read_response(rsp)
