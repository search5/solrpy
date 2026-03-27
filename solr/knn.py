"""Dense Vector / KNN Search wrapper for Solr 9.0+.

Provides a convenience class for building and executing K-Nearest-Neighbor
queries using Solr's ``{!knn}`` query parser and ``DenseVectorField``.
"""
from __future__ import annotations

from typing import Any, Sequence, TYPE_CHECKING

from .exceptions import SolrVersionError
from .response import Response

if TYPE_CHECKING:
    from .core import Solr


class KNN:
    """Dense Vector / KNN Search for Solr 9.0+.

    Builds ``{!knn f=<field> topK=<k>}[v1,v2,...]`` queries and executes
    them via the ``/select`` handler.

    Example::

        from solr import Solr, KNN

        conn = Solr('http://localhost:8983/solr/mycore')
        knn = KNN(conn)
        response = knn([0.1, 0.2, 0.3, ...], field='embedding', top_k=10)
        for doc in response.results:
            print(doc['id'], doc.get('score'))
    """

    _MIN_VERSION = (9, 0)

    def __init__(self, conn: Solr) -> None:
        self._conn = conn

    def _check_version(self) -> None:
        """Raise SolrVersionError if server is too old."""
        if self._conn.server_version < self._MIN_VERSION:
            raise SolrVersionError("knn_search", self._MIN_VERSION,
                                   self._conn.server_version)

    def build_query(self, vector: Sequence[float], field: str, top_k: int,
                    ef_search_scale_factor: float | None = None) -> str:
        """Build a ``{!knn}`` query string without executing it.

        :param vector: Dense vector as a sequence of floats.
        :param field: Name of the ``DenseVectorField`` to search.
        :param top_k: Number of nearest neighbors to retrieve.
        :param ef_search_scale_factor: Solr 10.0+ parameter to tune search
            accuracy independently from result count.
        :returns: The KNN query string.
        :raises SolrVersionError: If ``ef_search_scale_factor`` is used on
            Solr < 10.0.
        """
        parts = ['f=%s' % field, 'topK=%d' % top_k]

        if ef_search_scale_factor is not None:
            if self._conn.server_version < (10, 0):
                raise SolrVersionError(
                    "efSearchScaleFactor", (10, 0), self._conn.server_version)
            parts.append('efSearchScaleFactor=%s' % ef_search_scale_factor)

        vec_str = '[%s]' % ','.join(str(v) for v in vector)
        return '{!knn %s}%s' % (' '.join(parts), vec_str)

    def __call__(self, vector: Sequence[float], field: str, top_k: int,
                 filters: str | None = None,
                 ef_search_scale_factor: float | None = None,
                 **params: Any) -> Response | None:
        """Execute a KNN search query (Solr 9.0+).

        :param vector: Dense vector as a sequence of floats.
        :param field: Name of the ``DenseVectorField`` to search.
        :param top_k: Number of nearest neighbors to retrieve.
        :param filters: Optional filter query (``fq`` parameter).
        :param ef_search_scale_factor: Solr 10.0+ accuracy tuning parameter.
        :param params: Additional Solr parameters forwarded to ``select()``.
        :returns: A :class:`~solr.response.Response` instance.
        :raises SolrVersionError: If connected Solr is older than 9.0.
        """
        self._check_version()
        q = self.build_query(vector, field, top_k, ef_search_scale_factor)

        if filters is not None:
            params['fq'] = filters

        return self._conn.select(q, **params)
