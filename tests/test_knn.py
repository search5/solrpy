"""Tests for KNN / Dense Vector Search (Solr 9.0+)."""

import unittest
import solr
import solr.core
from tests.conftest import SOLR_HTTP

SOLR_KNN = "http://localhost:8983/solr/core0"


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

    def test_search_raises_on_old_version(self):
        from solr.knn import KNN
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = (8, 11, 0)
        knn = KNN(conn)
        with self.assertRaises(solr.core.SolrVersionError) as ctx:
            knn.search([0.1, 0.2, 0.3], field='embedding', top_k=10)
        self.assertEqual(ctx.exception.required, (9, 0))

    def test_similarity_raises_on_old_version(self):
        from solr.knn import KNN
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = (8, 11, 0)
        knn = KNN(conn)
        with self.assertRaises(solr.core.SolrVersionError):
            knn.similarity([0.1, 0.2], field='vec', min_return=0.7)


class TestKNNQueryBuilding(unittest.TestCase):

    def _make_knn(self, version=(9, 4, 0)):
        from solr.knn import KNN
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = version
        return KNN(conn)

    def test_basic_search_query(self):
        knn = self._make_knn()
        q = knn.build_knn_query([0.1, 0.2, 0.3], field='vec', top_k=10)
        self.assertEqual(q, '{!knn f=vec topK=10}[0.1,0.2,0.3]')

    def test_early_termination(self):
        knn = self._make_knn()
        q = knn.build_knn_query([0.1, 0.2], field='vec', top_k=5,
                                early_termination=True)
        self.assertIn('earlyTermination=true', q)

    def test_seed_query(self):
        knn = self._make_knn()
        q = knn.build_knn_query([0.1], field='vec', top_k=5,
                                seed_query='category:books')
        self.assertIn("seedQuery='category:books'", q)

    def test_pre_filter(self):
        knn = self._make_knn()
        q = knn.build_knn_query([0.1], field='vec', top_k=5,
                                pre_filter='inStock:true')
        self.assertIn("preFilter=inStock:true", q)

    def test_multiple_pre_filters(self):
        knn = self._make_knn()
        q = knn.build_knn_query([0.1], field='vec', top_k=5,
                                pre_filter=['inStock:true', 'cat:A'])
        self.assertIn('preFilter=inStock:true', q)
        self.assertIn('preFilter=cat:A', q)

    def test_ef_search_scale_factor(self):
        knn = self._make_knn((10, 0, 0))
        q = knn.build_knn_query([0.1, 0.2], field='vec', top_k=5,
                                ef_search_scale_factor=2.0)
        self.assertIn('efSearchScaleFactor=2.0', q)

    def test_ef_search_scale_factor_version_guard(self):
        knn = self._make_knn((9, 4, 0))
        with self.assertRaises(solr.core.SolrVersionError):
            knn.build_knn_query([0.1], field='vec', top_k=5,
                                ef_search_scale_factor=2.0)

    def test_similarity_query(self):
        knn = self._make_knn()
        q = knn.build_similarity_query([0.1, 0.2, 0.3], field='vec',
                                       min_return=0.7)
        self.assertEqual(q, '{!vectorSimilarity f=vec minReturn=0.7}[0.1,0.2,0.3]')

    def test_similarity_with_min_traverse(self):
        knn = self._make_knn()
        q = knn.build_similarity_query([0.1], field='vec',
                                       min_return=0.5, min_traverse=0.3)
        self.assertIn('minTraverse=0.3', q)

    def test_hybrid_query(self):
        knn = self._make_knn()
        q = knn.build_hybrid_query(
            text_query='red shoes',
            vector=[0.1, 0.2, 0.3], field='vec', min_return=0.7)
        self.assertIn('red shoes', q)
        self.assertIn('{!vectorSimilarity', q)
        self.assertIn('OR', q)

    def test_rerank_query(self):
        knn = self._make_knn()
        params = knn.build_rerank_params(
            vector=[0.1, 0.2], field='vec', top_k=10, rerank_docs=50)
        self.assertIn('rq', params)
        self.assertIn('reRankDocs=50', params['rq'])


class TestKNNLiveSearch(unittest.TestCase):
    """Integration tests requiring Solr 9.0+ with DenseVectorField."""

    def setUp(self):
        try:
            self.conn = solr.Solr(SOLR_KNN)
        except Exception:
            self.skipTest("Solr KNN instance not available at %s" % SOLR_KNN)
        if self.conn.server_version < (9, 0):
            self.conn.close()
            self.skipTest("KNN requires Solr 9.0+, got %s" %
                          '.'.join(str(v) for v in self.conn.server_version))
        # Ensure vector test data exists (may be wiped by other tests)
        self.conn.add_many([
            {'id': 'vec1', 'data': 'first',   'embedding': [1.0, 0.0, 0.0]},
            {'id': 'vec2', 'data': 'second',  'embedding': [0.0, 1.0, 0.0]},
            {'id': 'vec3', 'data': 'third',   'embedding': [0.0, 0.0, 1.0]},
            {'id': 'vec4', 'data': 'similar', 'embedding': [0.9, 0.1, 0.0]},
            {'id': 'vec5', 'data': 'mixed',   'embedding': [0.5, 0.5, 0.0]},
        ], commit=True)

    def tearDown(self):
        self.conn.close()

    def test_version_detected_as_9(self):
        self.assertGreaterEqual(self.conn.server_version[0], 9)

    def test_search_returns_results(self):
        from solr import KNN
        knn = KNN(self.conn)
        resp = knn.search([1.0, 0.0, 0.0], field='embedding', top_k=3)
        self.assertIsNotNone(resp)
        self.assertEqual(resp.numFound, 3)

    def test_search_order(self):
        from solr import KNN
        knn = KNN(self.conn)
        resp = knn.search([1.0, 0.0, 0.0], field='embedding', top_k=3)
        ids = [doc['id'] for doc in resp.results]
        self.assertEqual(ids[0], 'vec1')

    def test_search_top_k(self):
        from solr import KNN
        knn = KNN(self.conn)
        resp = knn.search([1.0, 0.0, 0.0], field='embedding', top_k=2)
        self.assertEqual(resp.numFound, 2)

    def test_search_different_vector(self):
        from solr import KNN
        knn = KNN(self.conn)
        resp = knn.search([0.0, 1.0, 0.0], field='embedding', top_k=1)
        self.assertEqual(resp.results[0]['id'], 'vec2')

    def test_search_with_filter(self):
        from solr import KNN
        knn = KNN(self.conn)
        # Filter to only vec1 and vec4 (both have high x-axis values)
        resp = knn.search([1.0, 0.0, 0.0], field='embedding', top_k=5,
                          filters='id:(vec1 OR vec4)')
        ids = [doc['id'] for doc in resp.results]
        self.assertTrue(set(ids).issubset({'vec1', 'vec4'}))

    def test_callable_delegates_to_search(self):
        from solr import KNN
        knn = KNN(self.conn)
        resp = knn([1.0, 0.0, 0.0], field='embedding', top_k=3)
        self.assertEqual(resp.numFound, 3)

    def test_ef_search_scale_factor_live(self):
        if self.conn.server_version < (10, 0):
            self.skipTest("efSearchScaleFactor requires Solr 10.0+")
        from solr import KNN
        knn = KNN(self.conn)
        resp = knn.search([1.0, 0.0, 0.0], field='embedding', top_k=3,
                          ef_search_scale_factor=2.0)
        self.assertIsNotNone(resp)
        self.assertEqual(resp.numFound, 3)
        self.assertEqual(resp.results[0]['id'], 'vec1')

    def test_build_query_with_ef(self):
        if self.conn.server_version < (10, 0):
            self.skipTest("efSearchScaleFactor requires Solr 10.0+")
        from solr import KNN
        knn = KNN(self.conn)
        q = knn.build_query([0.5, 0.5, 0.0], field='embedding', top_k=3,
                            ef_search_scale_factor=1.5)
        self.assertIn('efSearchScaleFactor=1.5', q)

    def test_hybrid_live(self):
        from solr import KNN
        knn = KNN(self.conn)
        resp = knn.hybrid('data:mixed', [1.0, 0.0, 0.0], field='embedding',
                          min_return=0.5)
        self.assertIsNotNone(resp)
        self.assertGreater(resp.numFound, 0)

    def test_similarity_live(self):
        from solr import KNN
        knn = KNN(self.conn)
        resp = knn.similarity([1.0, 0.0, 0.0], field='embedding',
                              min_return=0.5)
        self.assertIsNotNone(resp)
        self.assertGreaterEqual(resp.numFound, 3)


if __name__ == "__main__":
    unittest.main()
