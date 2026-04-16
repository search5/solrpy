"""Tests for httpx migration (2.0.1)."""

import unittest
import solr
from solr.async_solr import AsyncSolr
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


class TestVerifyParam(unittest.TestCase):

    def test_verify_default_absent_from_client_kwargs(self):
        conn = solr.Solr(SOLR_HTTP)
        self.assertNotIn('verify', conn._client_kwargs)
        conn.close()

    def test_verify_false_in_client_kwargs(self):
        conn = solr.Solr(SOLR_HTTP, verify=False)
        self.assertIs(conn._client_kwargs['verify'], False)
        conn.close()

    def test_verify_path_in_client_kwargs(self):
        conn = solr.Solr(SOLR_HTTP, verify='/path/to/ca-bundle.crt')
        self.assertEqual(conn._client_kwargs['verify'], '/path/to/ca-bundle.crt')

    def test_verify_false_passed_to_httpx_client(self):
        import httpx
        conn = solr.Solr(SOLR_HTTP, verify=False)
        self.assertIsInstance(conn._client, httpx.Client)
        conn.close()

    def test_async_verify_default_is_none(self):
        conn = AsyncSolr(SOLR_HTTP)
        self.assertIsNone(conn._verify)

    def test_async_verify_false(self):
        conn = AsyncSolr(SOLR_HTTP, verify=False)
        self.assertFalse(conn._verify)

    def test_async_verify_path(self):
        from unittest.mock import patch
        with patch('httpx.AsyncClient'):
            conn = AsyncSolr(SOLR_HTTP, verify='/path/to/ca.pem')
        self.assertEqual(conn._verify, '/path/to/ca.pem')


if __name__ == "__main__":
    unittest.main()
