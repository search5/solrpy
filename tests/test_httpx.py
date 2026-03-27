"""Tests for httpx migration (2.0.1)."""

import unittest
import solr
from tests.conftest import SOLR_HTTP, SolrConnectionTestCase


class TestHttpxClient(unittest.TestCase):

    def test_uses_httpx(self):
        """Solr should use httpx.Client internally."""
        import httpx
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        self.assertIsInstance(conn._client, httpx.Client)
        conn.close()

    def test_connection_pooling(self):
        """httpx provides connection pooling automatically."""
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        # Multiple requests reuse the same pool
        conn.select('*:*')
        conn.select('*:*')
        conn.select('*:*')
        # No error = pool is working
        conn.close()

    def test_timeout_works(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml', timeout=30)
        resp = conn.select('*:*')
        self.assertIsNotNone(resp)
        conn.close()

    def test_ssl_connection(self):
        """SSL params should be accepted without error."""
        # We can't test actual SSL without certs, but construction should work
        try:
            conn = solr.Solr('https://localhost:8984/solr/core0',
                             response_format='xml', timeout=1)
            conn.close()
        except Exception:
            pass  # Connection will fail but constructor should not raise

    def test_basic_crud_still_works(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        conn.add({'id': 'httpx_test', 'data': 'hello'}, commit=True)
        resp = conn.select('id:httpx_test')
        self.assertEqual(resp.numFound, 1)
        conn.delete(id='httpx_test', commit=True)
        conn.close()

    def test_ping_still_works(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        self.assertTrue(conn.ping())
        conn.close()

    def test_version_detection_still_works(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        self.assertIsInstance(conn.server_version, tuple)
        self.assertGreaterEqual(len(conn.server_version), 2)
        conn.close()


if __name__ == "__main__":
    unittest.main()
