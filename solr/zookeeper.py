"""ZooKeeper integration for SolrCloud node discovery.

Requires the ``kazoo`` library: ``pip install solrpy[cloud]``.
"""
from __future__ import annotations

import json
import random
from typing import Any

try:
    from kazoo.client import KazooClient
    HAS_KAZOO = True
except ImportError:
    HAS_KAZOO = False


class SolrZooKeeper:
    """Manages SolrCloud topology by reading ZooKeeper state.

    Monitors ``/live_nodes``, ``/collections/{name}/state.json``, and
    ``/aliases.json`` to discover active Solr nodes, shard leaders,
    and collection aliases.

    Requires the ``kazoo`` library (``pip install solrpy[cloud]``).

    Example::

        from solr import SolrZooKeeper, SolrCloud

        zk = SolrZooKeeper('zk1:2181,zk2:2181')
        cloud = SolrCloud(zk, collection='mycore')
        cloud.select('*:*')
        cloud.close()
        zk.close()
    """

    LIVE_NODES_PATH = '/live_nodes'
    ALIASES_PATH = '/aliases.json'
    COLLECTION_STATE_PATH = '/collections/%s/state.json'
    CLUSTER_STATE = '/clusterstate.json'

    def __init__(self, hosts: str, timeout: float = 10.0) -> None:
        """Connect to ZooKeeper.

        :param hosts: ZooKeeper connection string, e.g. ``'zk1:2181,zk2:2181'``.
        :param timeout: Connection timeout in seconds.
        :raises ImportError: If ``kazoo`` is not installed.
        """
        if not HAS_KAZOO:
            raise ImportError(
                "kazoo is required for ZooKeeper support. "
                "Install with: pip install solrpy[cloud]")
        self._client = KazooClient(hosts=hosts, timeout=timeout,
                                   read_only=True)
        self._client.start()

    def close(self) -> None:
        """Close the ZooKeeper connection."""
        self._client.stop()
        self._client.close()

    def live_nodes(self) -> list[str]:
        """Return a list of currently active Solr node identifiers."""
        children = self._client.get_children(self.LIVE_NODES_PATH)
        return list(children)

    def collection_state(self, collection: str) -> dict[str, Any]:
        """Return the state dict for a collection.

        Tries per-collection ``state.json`` first (Solr 5+), then falls back
        to the legacy ``/clusterstate.json`` (Solr 4.x).

        :param collection: Collection name.
        :returns: Dict with ``'shards'``, ``'router'``, etc.
        """
        # Try per-collection state.json (Solr 5+)
        path = self.COLLECTION_STATE_PATH % collection
        if self._client.exists(path):
            data, _ = self._client.get(path)
            state: dict[str, Any] = json.loads(data.decode('utf-8'))
            if collection in state:
                result: dict[str, Any] = state[collection]
                return result
            return state

        # Fallback: legacy /clusterstate.json (Solr 4.x)
        if self._client.exists(self.CLUSTER_STATE):
            data, _ = self._client.get(self.CLUSTER_STATE)
            if data:
                all_state: dict[str, Any] = json.loads(data.decode('utf-8'))
                if collection in all_state:
                    legacy: dict[str, Any] = all_state[collection]
                    return legacy

        raise RuntimeError("Collection '%s' not found in ZooKeeper" % collection)

    def aliases(self) -> dict[str, str]:
        """Return collection aliases as ``{alias: real_collection}``."""
        if not self._client.exists(self.ALIASES_PATH):
            return {}
        data, _ = self._client.get(self.ALIASES_PATH)
        if not data:
            return {}
        parsed: dict[str, Any] = json.loads(data.decode('utf-8'))
        result: dict[str, str] = parsed.get('collection', {})
        return result

    def _resolve_alias(self, collection: str) -> str:
        """Resolve a collection alias to the real collection name."""
        all_aliases = self.aliases()
        return all_aliases.get(collection, collection)

    def _get_replicas(self, collection: str, leader_only: bool = False) -> list[dict[str, Any]]:
        """Return active replica info dicts for a collection."""
        real_name = self._resolve_alias(collection)
        state = self.collection_state(real_name)
        live = set(self.live_nodes())
        replicas: list[dict[str, Any]] = []

        for shard_name, shard_data in state.get('shards', {}).items():
            if shard_data.get('state') != 'active':
                continue
            for replica_name, replica_data in shard_data.get('replicas', {}).items():
                if replica_data.get('state') != 'active':
                    continue
                node_name = replica_data.get('node_name', '')
                if node_name not in live:
                    continue
                if leader_only and replica_data.get('leader') != 'true':
                    continue
                replicas.append(replica_data)
        return replicas

    def _replica_to_url(self, replica: dict[str, Any]) -> str:
        """Convert a replica info dict to a Solr base URL."""
        base_url: str = replica.get('base_url', '')
        if base_url:
            return base_url
        # Fallback: construct from node_name
        node = replica.get('node_name', '')
        # node_name format: "host:port_solr" → "http://host:port/solr"
        host_port = node.replace('_solr', '').replace('_', '/')
        return 'http://%s/solr' % host_port

    def replica_urls(self, collection: str) -> list[str]:
        """Return base URLs of all active replicas for a collection.

        :param collection: Collection name (aliases resolved automatically).
        :returns: List of Solr base URLs.
        """
        replicas = self._get_replicas(collection, leader_only=False)
        return [self._replica_to_url(r) for r in replicas]

    def leader_urls(self, collection: str) -> list[str]:
        """Return base URLs of shard leaders for a collection.

        :param collection: Collection name (aliases resolved automatically).
        :returns: List of leader Solr base URLs (one per shard).
        """
        leaders = self._get_replicas(collection, leader_only=True)
        return [self._replica_to_url(r) for r in leaders]

    def random_url(self, collection: str) -> str:
        """Return a random active replica URL for a collection.

        :param collection: Collection name.
        :returns: A Solr base URL.
        :raises RuntimeError: If no active replicas are found.
        """
        urls = self.replica_urls(collection)
        if not urls:
            raise RuntimeError(
                "No active replicas found for collection '%s'" % collection)
        return random.choice(urls)

    def random_leader_url(self, collection: str) -> str:
        """Return a random shard leader URL for a collection.

        :param collection: Collection name.
        :returns: A leader Solr base URL.
        :raises RuntimeError: If no leaders are found.
        """
        urls = self.leader_urls(collection)
        if not urls:
            raise RuntimeError(
                "No leaders found for collection '%s'" % collection)
        return random.choice(urls)
