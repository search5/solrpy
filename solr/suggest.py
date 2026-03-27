"""Suggest handler wrapper for Solr 4.7+."""
from __future__ import annotations

import urllib.parse as urllib
from typing import Any, TYPE_CHECKING

from .exceptions import SolrVersionError
from .transport import SolrTransport

if TYPE_CHECKING:
    from .core import Solr


class Suggest:
    """Query Solr's SuggestComponent via the /suggest handler (Solr 4.7+).

    The /suggest handler must be configured in solrconfig.xml with a
    ``SuggestComponent`` and a ``SearchHandler`` bound to ``/suggest``.

    Returns a flat list of suggestion dicts (typically containing ``'term'``,
    ``'weight'``, and ``'payload'`` keys) gathered from all configured
    suggesters that match the query.

    Example::

        from solr import Solr, Suggest

        conn = Solr('http://localhost:8983/solr/mycore')
        suggest = Suggest(conn)
        results = suggest('que', dictionary='mySuggester', count=5)
        for s in results:
            print(s['term'], s['weight'])
    """

    _MIN_VERSION = (4, 7)

    def __init__(self, conn: Solr) -> None:
        self._transport = SolrTransport(conn)

    def _check_version(self) -> None:
        """Raise SolrVersionError if server is too old."""
        if self._transport.server_version < self._MIN_VERSION:
            raise SolrVersionError("suggest", self._MIN_VERSION,
                                   self._transport.server_version)

    def __call__(self, q: str, dictionary: str | None = None,
                 count: int = 10, **params: Any) -> list[dict[str, Any]]:
        """Return a flat list of suggestions for the query term.

        Args:
            q: The partial query string to get suggestions for.
            dictionary: Name of the suggester dictionary to query. If None,
                Solr uses the default suggester defined in solrconfig.xml.
            count: Maximum number of suggestions to return (default 10).
            **params: Additional parameters forwarded verbatim to the
                /suggest handler (e.g. ``suggest_build='true'``).

        Returns:
            A list of suggestion dicts. Each dict typically contains
            ``'term'``, ``'weight'``, and ``'payload'`` keys as returned
            by the configured suggester.

        Raises:
            SolrVersionError: If the connected Solr server is older than 4.7.
        """
        self._check_version()
        query_params: dict[str, str] = {
            'suggest': 'true',
            'suggest.q': q,
            'suggest.count': str(count),
            'wt': 'json',
        }
        if dictionary is not None:
            query_params['suggest.dictionary'] = dictionary
        query_params.update({k: str(v) for k, v in params.items()})

        qs = urllib.urlencode(query_params)
        data = self._transport.get_json('/suggest?' + qs)
        return self._extract_suggestions(data)

    def _extract_suggestions(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract a flat suggestion list from the raw /suggest response dict."""
        results: list[dict[str, Any]] = []
        suggest_block = data.get('suggest', {})
        for suggester_data in suggest_block.values():
            for term_data in suggester_data.values():
                if isinstance(term_data, dict):
                    results.extend(term_data.get('suggestions', []))
        return results
