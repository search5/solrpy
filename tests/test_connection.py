"""Auto-split from test_all.py"""

import socket
import unittest
import httpx
import solr
import solr.core
from tests.conftest import (
    SolrConnectionTestCase, ThrowConnectionExceptions,
    SOLR_HTTP, SOLR_PATH, get_rand_userdoc,
)


class TestHTTPConnection(SolrConnectionTestCase):

    def test_connect(self):
        """Check if we're really connected to Solr through HTTP."""
        conn = self.new_connection()
        self.assertTrue(conn.ping())

    def test_close_connection(self):
        """Make sure connections to Solr are being closed properly."""
        conn = self.new_connection()
        conn.close()
        self.assertTrue(conn._client.is_closed)  # conn._client is httpx.Client

    def test_invalid_max_retries(self):
        """ Passing something that can't be cast as an integer for max_retries
        should raise a ValueError and a value less than 0 should raise an
        AssertionError """
        self.assertRaises(ValueError, self.new_connection,
                          max_retries='asdf')
        self.assertRaises(AssertionError, self.new_connection,
                          max_retries=-5)



class TestRetries(SolrConnectionTestCase):

    def setUp(self):
        super(TestRetries, self).setUp()
        self.conn = self.new_connection()

    def test_connection_error_retries(self):
        """Verify that connection errors trigger retries."""
        thrower = ThrowConnectionExceptions(self.conn)
        self.conn._reconnect = lambda: None  # prevent client recreation
        with self.assertRaises(httpx.ConnectError):
            self.query(self.conn, "user_id:12345")
        # max_retries=3 → 4 total attempts (1 initial + 3 retries)
        self.assertEqual(thrower.calls, 4)

    def test_success_after_failure(self):
        """After one failure, the next attempt should succeed."""
        thrower = ThrowConnectionExceptions(self.conn, max=1)
        self.conn._reconnect = lambda: None
        self.query(self.conn, "user_id:12345")
        self.assertEqual(thrower.calls, 2)


# Additional commit-control tests using RequestTracking.


class TestPing(unittest.TestCase):
    """Test the Solr.ping() method."""

    def test_ping_returns_true_on_live_server(self):
        conn = solr.Solr(SOLR_HTTP)
        self.assertTrue(conn.ping())
        conn.close()

    def test_ping_returns_false_on_bad_url(self):
        conn = solr.Solr.__new__(solr.Solr)
        conn.path = '/solr/nonexistent_core'
        conn.host = 'localhost:8983'
        conn.scheme = 'http'
        conn.auth_headers = {}
        conn._auth_callable = None
        conn.persistent = True
        conn._client = httpx.Client(base_url='http://localhost:8983')
        self.assertFalse(conn.ping())
        conn.close()



class TestURLValidation(unittest.TestCase):
    """Solr constructor should warn on suspicious URLs."""

    def test_valid_url_no_warning(self):
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            conn = solr.Solr(SOLR_HTTP, response_format='xml')
            solr_warnings = [x for x in w if 'solrpy' in str(x.message)]
            self.assertEqual(len(solr_warnings), 0)
            conn.close()

    def test_url_ending_with_solr_no_warning(self):
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            conn = solr.Solr('http://localhost:8983/solr', response_format='xml')
            solr_warnings = [x for x in w if 'solrpy' in str(x.message)]
            self.assertEqual(len(solr_warnings), 0)
            conn.close()

    def test_suspicious_url_warns(self):
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            conn = solr.Solr('http://localhost:8983/search', response_format='xml')
            solr_warnings = [x for x in w if 'solrpy' in str(x.message)]
            self.assertEqual(len(solr_warnings), 1)
            self.assertIn('/solr', str(solr_warnings[0].message))
            conn.close()

    def test_root_url_warns(self):
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            conn = solr.Solr('http://localhost:8983/', response_format='xml')
            solr_warnings = [x for x in w if 'solrpy' in str(x.message)]
            self.assertEqual(len(solr_warnings), 1)
            conn.close()

    def test_url_with_solr_in_path_no_warning(self):
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            conn = solr.Solr('http://localhost:8983/solr/mycore', response_format='xml')
            solr_warnings = [x for x in w if 'solrpy' in str(x.message)]
            self.assertEqual(len(solr_warnings), 0)
            conn.close()


# ===================================================================
# 1.0.7 tests — paginator Django dependency removal
# ===================================================================


class TestRetryBackoff(unittest.TestCase):
    """Test exponential backoff and retry_delay."""

    def test_default_retry_delay(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        self.assertEqual(conn.retry_delay, 0.1)
        conn.close()

    def test_custom_retry_delay(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml', retry_delay=0.5)
        self.assertEqual(conn.retry_delay, 0.5)
        conn.close()

    def test_retry_logs_warning(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml', max_retries=1, retry_delay=0.01)
        call_count = [0]
        original_post = conn._client.post

        def failing_post(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 1:
                raise httpx.ConnectError("fake connection error")
            return original_post(*args, **kwargs)

        conn._client.post = failing_post  # type: ignore

        with self.assertLogs('solr', level='WARNING') as cm:
            conn._post('/solr/core0/update', '<commit/>', conn.xmlheaders)
        self.assertTrue(any('Retry' in msg for msg in cm.output))
        conn.close()

    def test_backoff_increases_delay(self):
        """Verify that retry uses exponential backoff (delay doubles)."""
        import time
        conn = solr.Solr(SOLR_HTTP, response_format='xml', max_retries=2, retry_delay=0.05)
        call_count = [0]
        original_post = conn._client.post

        def failing_post(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                raise httpx.ConnectError("fake connection error")
            return original_post(*args, **kwargs)

        conn._client.post = failing_post  # type: ignore
        conn._reconnect = lambda: None  # prevent client recreation

        start = time.monotonic()
        conn._post('/solr/core0/update', '<commit/>', conn.xmlheaders)
        elapsed = time.monotonic() - start

        # retry_delay=0.05, 2 retries: 0.05 + 0.10 = 0.15s minimum
        self.assertGreaterEqual(elapsed, 0.1)
        conn.close()


# ===================================================================
# 1.0.9 tests — per-request timeout
# ===================================================================


class TestPerRequestTimeout(unittest.TestCase):

    def test_select_with_timeout(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        conn.add({'id': 'timeout_test', 'data': 'hello'}, commit=True)
        resp = conn.select('id:timeout_test', timeout=10)
        self.assertEqual(resp.numFound, 1)
        conn.delete(id='timeout_test', commit=True)
        conn.close()

    def test_select_raw_with_timeout(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        raw = conn.select.raw(q='*:*', wt='xml', timeout=10)
        self.assertIn('<response>', raw)
        conn.close()

    def test_timeout_restores_after_request(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml', timeout=30)
        conn.select('*:*', timeout=5)
        self.assertEqual(conn.timeout, 30)
        conn.close()

    def test_add_with_timeout(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        conn.add({'id': 'timeout_add', 'data': 'x'}, commit=True, timeout=10)
        resp = conn.select('id:timeout_add')
        self.assertEqual(resp.numFound, 1)
        conn.delete(id='timeout_add', commit=True)
        conn.close()

    def test_delete_with_timeout(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        conn.add({'id': 'timeout_del', 'data': 'x'}, commit=True)
        conn.delete(id='timeout_del', commit=True, timeout=10)
        resp = conn.select('id:timeout_del')
        self.assertEqual(resp.numFound, 0)
        conn.close()


# ===================================================================
# 1.1.0 tests — Solr 4.0+ features
# ===================================================================

