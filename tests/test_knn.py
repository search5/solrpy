"""Tests for KNN / Dense Vector Search (Solr 9.0+)."""

import unittest
import solr
import solr.core
from tests.conftest import SOLR_HTTP


class TestKNNCreation(unittest.TestCase):

    def test_import(self):
        from solr import KNN
        self.assertTrue(callable(KNN))

    def test_explicit_creation(self):
        from solr import KNN
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        knn = KNN(conn)
        self.assertIsNotNone(knn)
        conn.close()

    def test_conn_has_no_knn_attribute(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        self.assertFalse(hasattr(conn, 'knn'))
        conn.close()


class TestKNNVersionGuard(unittest.TestCase):

    def test_raises_on_old_version(self):
        from solr.knn import KNN
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = (8, 11, 0)
        knn = KNN(conn)
        with self.assertRaises(solr.core.SolrVersionError) as ctx:
            knn([0.1, 0.2, 0.3], field='embedding', top_k=10)
        self.assertEqual(ctx.exception.required, (9, 0))

    def test_passes_on_solr_9(self):
        """Version check should pass on 9.x (query will fail without actual index)."""
        from solr.knn import KNN
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = (9, 4, 1)
        conn.response_format = 'json'
        conn.response_version = 2.2
        conn.path = '/solr/core0'
        knn = KNN(conn)
        # Can't actually execute on Solr 6.6, just verify no version error
        # by checking the query string generation
        q = knn.build_query([0.1, 0.2, 0.3], field='embedding', top_k=5)
        self.assertIn('{!knn', q)
        self.assertIn('f=embedding', q)
        self.assertIn('topK=5', q)
        self.assertIn('0.1', q)


SOLR9_HTTP = "http://localhost:8984/solr/knn_core"


class TestKNNLiveSearch(unittest.TestCase):
    """Integration tests against Solr 9.4 with DenseVectorField."""

    def setUp(self):
        self.conn = solr.Solr(SOLR9_HTTP)

    def tearDown(self):
        self.conn.close()

    def test_version_detected_as_9(self):
        self.assertGreaterEqual(self.conn.server_version[0], 9)

    def test_knn_search_returns_results(self):
        from solr import KNN
        knn = KNN(self.conn)
        resp = knn([1.0, 0.0, 0.0], field='embedding', top_k=3)
        self.assertIsNotNone(resp)
        self.assertEqual(resp.numFound, 3)

    def test_knn_search_order(self):
        from solr import KNN
        knn = KNN(self.conn)
        resp = knn([1.0, 0.0, 0.0], field='embedding', top_k=3)
        ids = [doc['id'] for doc in resp.results]
        self.assertEqual(ids[0], 'vec1')

    def test_knn_search_top_k(self):
        from solr import KNN
        knn = KNN(self.conn)
        resp = knn([1.0, 0.0, 0.0], field='embedding', top_k=2)
        self.assertEqual(resp.numFound, 2)

    def test_knn_different_vector(self):
        from solr import KNN
        knn = KNN(self.conn)
        resp = knn([0.0, 1.0, 0.0], field='embedding', top_k=1)
        self.assertEqual(resp.results[0]['id'], 'vec2')

    def test_knn_with_filter(self):
        from solr import KNN
        knn = KNN(self.conn)
        resp = knn([1.0, 0.0, 0.0], field='embedding', top_k=5,
                   filters='id:vec5')
        ids = [doc['id'] for doc in resp.results]
        self.assertIn('vec5', ids)


class TestKNNQueryBuilding(unittest.TestCase):

    def test_basic_query(self):
        from solr.knn import KNN
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = (9, 0, 0)
        knn = KNN(conn)
        q = knn.build_query([0.1, 0.2, 0.3], field='vec', top_k=10)
        self.assertEqual(q, '{!knn f=vec topK=10}[0.1,0.2,0.3]')

    def test_query_with_floats(self):
        from solr.knn import KNN
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = (9, 0, 0)
        knn = KNN(conn)
        q = knn.build_query([1.0, 2.5, -0.3], field='embedding', top_k=20)
        self.assertEqual(q, '{!knn f=embedding topK=20}[1.0,2.5,-0.3]')

    def test_ef_search_scale_factor(self):
        from solr.knn import KNN
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = (10, 0, 0)
        knn = KNN(conn)
        q = knn.build_query([0.1, 0.2], field='vec', top_k=5,
                            ef_search_scale_factor=2.0)
        self.assertIn('efSearchScaleFactor=2.0', q)

    def test_ef_search_scale_factor_version_guard(self):
        from solr.knn import KNN
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = (9, 4, 0)
        knn = KNN(conn)
        with self.assertRaises(solr.core.SolrVersionError) as ctx:
            knn.build_query([0.1], field='vec', top_k=5,
                            ef_search_scale_factor=2.0)
        self.assertEqual(ctx.exception.required, (10, 0))


if __name__ == "__main__":
    unittest.main()
