"""SolrCloud client with automatic node discovery and failover.

Supports two modes:
- **ZooKeeper mode**: Real-time node discovery via ``SolrZooKeeper``.
- **HTTP mode**: Node discovery via CLUSTERSTATUS API (no ZooKeeper needed).
"""
from __future__ import annotations

import json
import time
import random
import logging
from typing import Any, TYPE_CHECKING

from .core import Solr
from .response import Response

if TYPE_CHECKING:
    from .zookeeper import SolrZooKeeper

_logger = logging.getLogger('solr.cloud')


class SolrCloud:
    """SolrCloud client with leader-aware routing and automatic failover.

    Two ways to create:

    **With ZooKeeper** (real-time node discovery)::

        from solr import SolrZooKeeper, SolrCloud

        zk = SolrZooKeeper('zk1:2181,zk2:2181')
        cloud = SolrCloud(zk, collection='mycore')

    **Without ZooKeeper** (HTTP-only, CLUSTERSTATUS polling)::

        cloud = SolrCloud.from_urls(
            ['http://solr1:8983/solr', 'http://solr2:8983/solr'],
            collection='mycore')
    """

    def __init__(self, zk: SolrZooKeeper, collection: str,
                 retry_count: int = 3, retry_delay: float = 0.5,
                 **solr_kwargs: Any) -> None:
        """Create a SolrCloud client backed by ZooKeeper.

        :param zk: A :class:`~solr.zookeeper.SolrZooKeeper` instance.
        :param collection: Solr collection name.
        :param retry_count: Number of failover retries.
        :param retry_delay: Base delay between retries (exponential backoff).
        :param solr_kwargs: Extra keyword arguments forwarded to :class:`Solr`.
        """
        self._zk = zk
        self._urls: list[str] | None = None
        self._collection = collection
        self._retry_count = retry_count
        self._retry_delay = retry_delay
        self._solr_kwargs = solr_kwargs
        self._mode = 'zk'

        # Create initial Solr connection
        url = self._zk.random_url(collection)
        self._conn = Solr(url + '/' + collection, **solr_kwargs)

    @classmethod
    def from_urls(cls, urls: list[str], collection: str,
                  retry_count: int = 3, retry_delay: float = 0.5,
                  **solr_kwargs: Any) -> SolrCloud:
        """Create a SolrCloud client using HTTP-only node discovery.

        No ZooKeeper connection needed. Uses the CLUSTERSTATUS API
        to discover nodes, falling back to round-robin across the
        provided URLs.

        :param urls: List of Solr base URLs (e.g. ``['http://host:8983/solr']``).
        :param collection: Solr collection name.
        :param retry_count: Number of failover retries.
        :param retry_delay: Base delay between retries.
        :param solr_kwargs: Extra keyword arguments forwarded to :class:`Solr`.
        """
        instance = cls.__new__(cls)
        instance._zk = None  # type: ignore[assignment]
        instance._urls = list(urls)
        instance._collection = collection
        instance._retry_count = retry_count
        instance._retry_delay = retry_delay
        instance._solr_kwargs = solr_kwargs
        instance._mode = 'http'

        # Try to connect to the first available node
        url = instance._pick_url()
        instance._conn = Solr(url + '/' + collection, **solr_kwargs)
        return instance

    def _pick_url(self) -> str:
        """Pick a Solr base URL for the next request."""
        if self._mode == 'zk':
            return self._zk.random_url(self._collection)

        # HTTP mode: try CLUSTERSTATUS on known URLs, fallback to round-robin
        assert self._urls is not None
        for base_url in self._urls:
            try:
                probe = Solr(base_url + '/' + self._collection,
                             **self._solr_kwargs)
                if probe.ping():
                    probe.close()
                    return base_url
                probe.close()
            except Exception:
                continue
        # All probes failed, return random from list
        return random.choice(self._urls)

    def _pick_leader_url(self) -> str:
        """Pick a shard leader URL for write operations."""
        if self._mode == 'zk':
            return self._zk.random_leader_url(self._collection)
        # HTTP mode: use CLUSTERSTATUS to find leaders
        assert self._urls is not None
        for base_url in self._urls:
            try:
                import urllib.request
                cs_url = '%s/admin/collections?action=CLUSTERSTATUS&collection=%s&wt=json' % (
                    base_url, self._collection)
                with urllib.request.urlopen(cs_url, timeout=5) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                col_state = data['cluster']['collections'][self._collection]
                for shard_data in col_state['shards'].values():
                    for replica_data in shard_data['replicas'].values():
                        if replica_data.get('leader') == 'true':
                            leader_base: str = replica_data.get('base_url', base_url)
                            return leader_base
            except Exception:
                continue
        return random.choice(self._urls)

    def _reconnect(self, leader: bool = False) -> None:
        """Reconnect to a different node."""
        self._conn.close()
        url = self._pick_leader_url() if leader else self._pick_url()
        self._conn = Solr(url + '/' + self._collection, **self._solr_kwargs)

    def _with_failover(self, method: str, *args: Any, leader: bool = False,
                       **kwargs: Any) -> Any:
        """Execute a method with automatic failover."""
        last_error: Exception | None = None
        for attempt in range(self._retry_count + 1):
            try:
                if attempt > 0:
                    self._reconnect(leader=leader)
                func = getattr(self._conn, method)
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                _logger.warning(
                    "SolrCloud %s failed (attempt %d/%d): %s",
                    method, attempt + 1, self._retry_count + 1, e)
                if attempt < self._retry_count:
                    delay = self._retry_delay * (2 ** attempt)
                    time.sleep(delay)
        raise last_error  # type: ignore[misc]

    # -- Public API (mirrors Solr) ------------------------------------------

    @property
    def server_version(self) -> tuple[int, ...]:
        """Detected Solr server version tuple."""
        return self._conn.server_version

    def ping(self) -> bool:
        """Ping the Solr server."""
        return self._conn.ping()

    def close(self) -> None:
        """Close the Solr connection."""
        self._conn.close()

    def select(self, *args: Any, **kwargs: Any) -> Response | None:
        """Execute a search query with automatic failover.

        :param args: Positional arguments forwarded to :meth:`Solr.select`.
        :param kwargs: Keyword arguments forwarded to :meth:`Solr.select`.
        """
        result: Response | None = self._with_failover('select', *args, **kwargs)
        return result

    def add(self, doc: dict[str, Any], **kwargs: Any) -> Any:
        """Add a document, routed to a shard leader.

        :param doc: Document as a dict of field name to value mappings.
        :param kwargs: Additional keyword arguments forwarded to :meth:`Solr.add`.
        """
        return self._with_failover('add', doc, leader=True, **kwargs)

    def add_many(self, docs: Any, **kwargs: Any) -> Any:
        """Add multiple documents, routed to a shard leader.

        :param docs: Iterable of document dicts to add.
        :param kwargs: Additional keyword arguments forwarded to :meth:`Solr.add_many`.
        """
        return self._with_failover('add_many', docs, leader=True, **kwargs)

    def delete(self, **kwargs: Any) -> Any:
        """Delete documents, routed to a shard leader.

        :param kwargs: Keyword arguments forwarded to :meth:`Solr.delete`
            (e.g. ``id='doc1'``).
        """
        return self._with_failover('delete', leader=True, **kwargs)

    def delete_query(self, query: str, **kwargs: Any) -> Any:
        """Delete by query, routed to a shard leader.

        :param query: Solr query string matching documents to delete.
        :param kwargs: Additional keyword arguments forwarded to :meth:`Solr.delete_query`.
        """
        return self._with_failover('delete_query', query, leader=True, **kwargs)

    def delete_many(self, ids: list[Any], **kwargs: Any) -> Any:
        """Delete multiple documents by ID.

        :param ids: List of document IDs to delete.
        :param kwargs: Additional keyword arguments forwarded to :meth:`Solr.delete_many`.
        """
        return self._with_failover('delete_many', ids, leader=True, **kwargs)

    def commit(self, **kwargs: Any) -> Any:
        """Commit changes.

        :param kwargs: Keyword arguments forwarded to :meth:`Solr.commit`.
        """
        return self._with_failover('commit', leader=True, **kwargs)

    def optimize(self, **kwargs: Any) -> Any:
        """Optimize the index.

        :param kwargs: Keyword arguments forwarded to :meth:`Solr.optimize`.
        """
        return self._with_failover('optimize', leader=True, **kwargs)
