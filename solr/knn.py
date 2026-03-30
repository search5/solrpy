"""Dense Vector / KNN Search wrapper for Solr 9.0+.

Provides a convenience class for building and executing K-Nearest-Neighbor
queries, similarity threshold searches, hybrid queries, and re-ranking
using Solr's ``{!knn}`` and ``{!vectorSimilarity}`` query parsers.
"""
from __future__ import annotations

from typing import Any, Sequence, TYPE_CHECKING

from .exceptions import SolrVersionError
from .response import Response
from .transport import _is_async_conn

if TYPE_CHECKING:
    from .core import Solr


class KNN:
    """Dense Vector Search for Solr 9.0+.

    Supports ``{!knn}``, ``{!vectorSimilarity}``, hybrid search, and
    re-ranking patterns.  Created explicitly by the user.

    Works with both ``Solr`` (sync) and ``AsyncSolr`` (async) connections.

    Example::

        from solr import Solr, KNN

        conn = Solr('http://localhost:8983/solr/mycore')
        knn = KNN(conn)

        # Top-K nearest neighbors
        response = knn.search([0.1, 0.2, 0.3], field='embedding', top_k=10)

        # Similarity threshold
        response = knn.similarity([0.1, 0.2, 0.3], field='embedding',
                                  min_return=0.7)
    """

    _MIN_VERSION = (9, 0)

    def __init__(self, conn: Any) -> None:
        """Initialize a KNN search client.

        :param conn: A :class:`~solr.core.Solr` or :class:`~solr.async_solr.AsyncSolr` connection.
        """
        self._conn = conn
        self._is_async: bool = _is_async_conn(conn)

    def _check_version(self) -> None:
        """Raise SolrVersionError if server is too old."""
        if self._conn.server_version < self._MIN_VERSION:
            raise SolrVersionError("knn_search", self._MIN_VERSION,
                                   self._conn.server_version)

    # -- Query builders ------------------------------------------------------

    def build_knn_query(
        self,
        vector: Sequence[float],
        field: str,
        top_k: int = 10,
        early_termination: bool = False,
        saturation_threshold: float | None = None,
        patience: int | None = None,
        ef_search_scale_factor: float | None = None,
        seed_query: str | None = None,
        pre_filter: str | list[str] | None = None,
        include_tags: str | None = None,
        exclude_tags: str | None = None,
    ) -> str:
        """Build a ``{!knn}`` query string.

        :param vector: Dense vector as a sequence of floats.
        :param field: Name of the ``DenseVectorField`` to search.
        :param top_k: Number of nearest neighbors to retrieve.
        :param early_termination: Enable HNSW early termination optimization.
        :param saturation_threshold: Queue saturation cutoff for early termination.
        :param patience: Iteration limit for early termination.
        :param ef_search_scale_factor: Candidate examination multiplier (Solr 10.0+).
        :param seed_query: Lexical query to guide vector search entry point.
        :param pre_filter: Explicit pre-filter query string(s).
        :param include_tags: Only use fq filters with these tags.
        :param exclude_tags: Exclude fq filters with these tags.
        :returns: The KNN query string.
        """
        parts = ['f=%s' % field, 'topK=%d' % top_k]

        if early_termination:
            parts.append('earlyTermination=true')
        if saturation_threshold is not None:
            parts.append('saturationThreshold=%s' % saturation_threshold)
        if patience is not None:
            parts.append('patience=%d' % patience)
        if ef_search_scale_factor is not None:
            if self._conn.server_version < (10, 0):
                raise SolrVersionError(
                    "efSearchScaleFactor", (10, 0), self._conn.server_version)
            parts.append('efSearchScaleFactor=%s' % ef_search_scale_factor)
        if seed_query is not None:
            parts.append("seedQuery='%s'" % seed_query)
        if pre_filter is not None:
            if isinstance(pre_filter, str):
                pre_filter = [pre_filter]
            for pf in pre_filter:
                parts.append('preFilter=%s' % pf)
        if include_tags is not None:
            parts.append('includeTags=%s' % include_tags)
        if exclude_tags is not None:
            parts.append('excludeTags=%s' % exclude_tags)

        vec_str = '[%s]' % ','.join(str(v) for v in vector)
        return '{!knn %s}%s' % (' '.join(parts), vec_str)

    def build_similarity_query(
        self,
        vector: Sequence[float],
        field: str,
        min_return: float,
        min_traverse: float | None = None,
        pre_filter: str | list[str] | None = None,
    ) -> str:
        """Build a ``{!vectorSimilarity}`` query string.

        :param vector: Dense vector as a sequence of floats.
        :param field: Name of the ``DenseVectorField`` to search.
        :param min_return: Minimum similarity threshold for results.
        :param min_traverse: Minimum similarity to continue graph traversal.
        :param pre_filter: Explicit pre-filter query string(s).
        :returns: The vectorSimilarity query string.
        """
        parts = ['f=%s' % field, 'minReturn=%s' % min_return]

        if min_traverse is not None:
            parts.append('minTraverse=%s' % min_traverse)
        if pre_filter is not None:
            if isinstance(pre_filter, str):
                pre_filter = [pre_filter]
            for pf in pre_filter:
                parts.append('preFilter=%s' % pf)

        vec_str = '[%s]' % ','.join(str(v) for v in vector)
        return '{!vectorSimilarity %s}%s' % (' '.join(parts), vec_str)

    def build_hybrid_query(
        self,
        text_query: str,
        vector: Sequence[float],
        field: str,
        min_return: float = 0.5,
    ) -> str:
        """Build a hybrid (lexical OR vector) query string.

        :param text_query: The lexical search query.
        :param vector: Dense vector for similarity matching.
        :param field: Name of the ``DenseVectorField``.
        :param min_return: Minimum similarity threshold for the vector part.
        :returns: A combined OR query string.
        """
        vec_str = '[%s]' % ','.join(str(v) for v in vector)
        sim_q = '{!vectorSimilarity f=%s minReturn=%s}%s' % (
            field, min_return, vec_str)
        return '(%s OR %s)' % (text_query, sim_q)

    def build_rerank_params(
        self,
        vector: Sequence[float],
        field: str,
        top_k: int = 10,
        rerank_docs: int = 100,
        rerank_weight: float = 1.0,
    ) -> dict[str, str]:
        """Build re-ranking parameters for use with a lexical base query.

        :param vector: Dense vector for re-ranking.
        :param field: Name of the ``DenseVectorField``.
        :param top_k: topK for the KNN re-rank query.
        :param rerank_docs: Number of top lexical docs to re-rank.
        :param rerank_weight: Weight of vector score in final ranking.
        :returns: A dict with ``rq`` key ready to pass as query parameter.
        """
        knn_q = self.build_knn_query(vector, field, top_k)
        rq = ('{!rerank reRankQuery=$rqq reRankDocs=%d reRankWeight=%s}'
              % (rerank_docs, rerank_weight))
        return {'rq': rq, 'rqq': knn_q}

    # -- Execution methods ---------------------------------------------------

    def search(
        self,
        vector: Sequence[float],
        field: str,
        top_k: int = 10,
        filters: str | None = None,
        early_termination: bool = False,
        saturation_threshold: float | None = None,
        patience: int | None = None,
        ef_search_scale_factor: float | None = None,
        seed_query: str | None = None,
        pre_filter: str | list[str] | None = None,
        **params: Any,
    ) -> Any:
        """Execute a ``{!knn}`` search query (Solr 9.0+).

        :param vector: Dense vector as a sequence of floats.
        :param field: Name of the ``DenseVectorField`` to search.
        :param top_k: Number of nearest neighbors to retrieve.
        :param filters: Filter query (``fq`` parameter).
        :param early_termination: Enable HNSW early termination.
        :param seed_query: Lexical query to guide vector search.
        :param pre_filter: Explicit pre-filter query string(s).
        :param params: Additional Solr parameters.
        :returns: A :class:`~solr.response.Response` instance (sync) or coroutine (async).
        """
        self._check_version()
        q = self.build_knn_query(
            vector, field, top_k,
            early_termination=early_termination,
            saturation_threshold=saturation_threshold,
            patience=patience,
            ef_search_scale_factor=ef_search_scale_factor,
            seed_query=seed_query,
            pre_filter=pre_filter,
        )
        if filters is not None:
            params['fq'] = filters
        return self._conn.select(q, **params)

    def similarity(
        self,
        vector: Sequence[float],
        field: str,
        min_return: float,
        min_traverse: float | None = None,
        pre_filter: str | list[str] | None = None,
        filters: str | None = None,
        **params: Any,
    ) -> Any:
        """Execute a ``{!vectorSimilarity}`` search (Solr 9.0+).

        Returns all documents whose similarity to the vector exceeds
        *min_return*.

        :param vector: Dense vector as a sequence of floats.
        :param field: Name of the ``DenseVectorField``.
        :param min_return: Minimum similarity threshold for results.
        :param min_traverse: Minimum similarity to continue traversal.
        :param pre_filter: Explicit pre-filter query string(s).
        :param filters: Filter query (``fq`` parameter).
        :param params: Additional Solr parameters.
        :returns: A :class:`~solr.response.Response` instance.
        """
        self._check_version()
        q = self.build_similarity_query(
            vector, field, min_return,
            min_traverse=min_traverse,
            pre_filter=pre_filter,
        )
        if filters is not None:
            params['fq'] = filters
        return self._conn.select(q, **params)

    def hybrid(
        self,
        text_query: str,
        vector: Sequence[float],
        field: str,
        min_return: float = 0.5,
        **params: Any,
    ) -> Any:
        """Execute a hybrid (lexical OR vector) search (Solr 9.0+).

        :param text_query: The lexical search query.
        :param vector: Dense vector for similarity matching.
        :param field: Name of the ``DenseVectorField``.
        :param min_return: Minimum similarity threshold for vector part.
        :param params: Additional Solr parameters.
        :returns: A :class:`~solr.response.Response` instance.
        """
        self._check_version()
        q = self.build_hybrid_query(text_query, vector, field, min_return)
        return self._conn.select(q, **params)

    def rerank(
        self,
        query: str,
        vector: Sequence[float],
        field: str,
        top_k: int = 10,
        rerank_docs: int = 100,
        rerank_weight: float = 1.0,
        **params: Any,
    ) -> Any:
        """Execute a lexical query re-ranked by vector similarity (Solr 9.0+).

        :param query: The base lexical query.
        :param vector: Dense vector for re-ranking.
        :param field: Name of the ``DenseVectorField``.
        :param top_k: topK for the KNN re-rank query.
        :param rerank_docs: Number of top lexical docs to re-rank.
        :param rerank_weight: Weight of vector score in final ranking.
        :param params: Additional Solr parameters.
        :returns: A :class:`~solr.response.Response` instance.
        """
        self._check_version()
        rr = self.build_rerank_params(vector, field, top_k,
                                      rerank_docs, rerank_weight)
        params.update(rr)
        return self._conn.select(query, **params)

    def build_query(self, vector: Sequence[float], field: str, top_k: int = 10,
                    ef_search_scale_factor: float | None = None) -> str:
        """Alias for :meth:`build_knn_query` (backward compatibility).

        :param vector: Dense vector as a sequence of floats.
        :param field: Name of the ``DenseVectorField`` to search.
        :param top_k: Number of nearest neighbors to retrieve.
        :param ef_search_scale_factor: Candidate examination multiplier (Solr 10.0+).
        """
        return self.build_knn_query(vector, field, top_k,
                                    ef_search_scale_factor=ef_search_scale_factor)

    def __call__(self, vector: Sequence[float], field: str, top_k: int = 10,
                 **params: Any) -> Any:
        """Shortcut for :meth:`search`.

        :param vector: Dense vector as a sequence of floats.
        :param field: Name of the ``DenseVectorField`` to search.
        :param top_k: Number of nearest neighbors to retrieve.
        :param params: Additional Solr parameters forwarded to :meth:`search`.
        """
        return self.search(vector, field, top_k, **params)
