"""Tests for SolrCloud support (Solr 4.0+)."""

import unittest
import solr
import solr.core

ZK_HOST = "localhost:2181"
CLOUD_URLS = [
    "http://localhost:8985/solr",
    "http://localhost:8986/solr",
    "http://localhost:8987/solr",
]
COLLECTION = "testcol"


# ===================================================================
# ZooKeeper class tests
# ===================================================================

class TestZooKeeperImport(unittest.TestCase):

    def test_import(self):
        from solr.zookeeper import SolrZooKeeper
        self.assertTrue(callable(SolrZooKeeper))

    def test_exported_from_package(self):
        self.assertTrue(hasattr(solr, 'SolrZooKeeper'))


class TestZooKeeperConnection(unittest.TestCase):

    def test_connect_and_get_live_nodes(self):
        from solr.zookeeper import SolrZooKeeper
        zk = SolrZooKeeper(ZK_HOST)
        nodes = zk.live_nodes()
        self.assertIsInstance(nodes, list)
        self.assertGreaterEqual(len(nodes), 1)
        zk.close()

    def test_get_collection_state(self):
        from solr.zookeeper import SolrZooKeeper
        zk = SolrZooKeeper(ZK_HOST)
        state = zk.collection_state(COLLECTION)
        self.assertIsInstance(state, dict)
        self.assertIn('shards', state)
        zk.close()

    def test_get_leader_urls(self):
        from solr.zookeeper import SolrZooKeeper
        zk = SolrZooKeeper(ZK_HOST)
        leaders = zk.leader_urls(COLLECTION)
        self.assertIsInstance(leaders, list)
        self.assertGreater(len(leaders), 0)
        for url in leaders:
            self.assertTrue(url.startswith('http'))
        zk.close()

    def test_get_replica_urls(self):
        from solr.zookeeper import SolrZooKeeper
        zk = SolrZooKeeper(ZK_HOST)
        replicas = zk.replica_urls(COLLECTION)
        self.assertIsInstance(replicas, list)
        self.assertGreater(len(replicas), 0)
        zk.close()

    def test_get_random_url(self):
        from solr.zookeeper import SolrZooKeeper
        zk = SolrZooKeeper(ZK_HOST)
        url = zk.random_url(COLLECTION)
        self.assertTrue(url.startswith('http'))
        zk.close()

    def test_aliases(self):
        from solr.zookeeper import SolrZooKeeper
        zk = SolrZooKeeper(ZK_HOST)
        aliases = zk.aliases()
        self.assertIsInstance(aliases, dict)
        zk.close()


# ===================================================================
# SolrCloud class tests
# ===================================================================

class TestSolrCloudImport(unittest.TestCase):

    def test_import(self):
        from solr.cloud import SolrCloud
        self.assertTrue(callable(SolrCloud))

    def test_exported_from_package(self):
        self.assertTrue(hasattr(solr, 'SolrCloud'))


class TestSolrCloudWithZK(unittest.TestCase):

    def setUp(self):
        from solr.zookeeper import SolrZooKeeper
        from solr.cloud import SolrCloud
        self.zk = SolrZooKeeper(ZK_HOST)
        self.cloud = SolrCloud(self.zk, collection=COLLECTION)

    def tearDown(self):
        self.cloud.close()
        self.zk.close()

    def test_select(self):
        resp = self.cloud.select('*:*')
        self.assertIsNotNone(resp)

    def test_add_and_query(self):
        self.cloud.add({'id': 'cloud_test_1', 'name': 'hello'}, commit=True)
        resp = self.cloud.select('id:cloud_test_1')
        self.assertEqual(resp.numFound, 1)
        self.cloud.delete(id='cloud_test_1', commit=True)

    def test_add_many(self):
        docs = [{'id': 'cloud_m_%d' % i, 'name': 'doc%d' % i} for i in range(5)]
        self.cloud.add_many(docs, commit=True)
        resp = self.cloud.select('id:cloud_m_*')
        self.assertEqual(resp.numFound, 5)
        self.cloud.delete_query('id:cloud_m_*', commit=True)

    def test_server_version(self):
        self.assertIsInstance(self.cloud.server_version, tuple)
        self.assertGreaterEqual(self.cloud.server_version[0], 4)

    def test_ping(self):
        self.assertTrue(self.cloud.ping())


class TestSolrCloudFromUrls(unittest.TestCase):
    """Test HTTP-only mode without ZooKeeper."""

    def setUp(self):
        from solr.cloud import SolrCloud
        self.cloud = SolrCloud.from_urls(CLOUD_URLS, collection=COLLECTION)

    def tearDown(self):
        self.cloud.close()

    def test_select(self):
        resp = self.cloud.select('*:*')
        self.assertIsNotNone(resp)

    def test_add_and_query(self):
        self.cloud.add({'id': 'http_cloud_1', 'name': 'test'}, commit=True)
        resp = self.cloud.select('id:http_cloud_1')
        self.assertEqual(resp.numFound, 1)
        self.cloud.delete(id='http_cloud_1', commit=True)

    def test_server_version(self):
        self.assertIsInstance(self.cloud.server_version, tuple)


class TestSolrCloudFailover(unittest.TestCase):

    def test_failover_on_bad_node(self):
        """If one URL is dead, SolrCloud should try the next."""
        from solr.cloud import SolrCloud
        urls = ['http://localhost:19999/solr'] + CLOUD_URLS  # first is dead
        cloud = SolrCloud.from_urls(urls, collection=COLLECTION)
        resp = cloud.select('*:*')
        self.assertIsNotNone(resp)
        cloud.close()


if __name__ == "__main__":
    unittest.main()
