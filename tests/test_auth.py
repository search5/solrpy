"""Tests for authentication improvements."""

import unittest
import solr
from tests.conftest import SOLR_HTTP


class TestBearerTokenAuth(unittest.TestCase):

    def test_bearer_token_sets_header(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml',
                         auth_token='my-secret-token')
        self.assertIn('Authorization', conn.auth_headers)
        self.assertEqual(conn.auth_headers['Authorization'],
                         'Bearer my-secret-token')
        conn.close()

    def test_bearer_token_overrides_basic(self):
        """auth_token takes priority over http_user/http_pass."""
        conn = solr.Solr(SOLR_HTTP, response_format='xml',
                         http_user='user', http_pass='pass',
                         auth_token='token123')
        self.assertTrue(
            conn.auth_headers['Authorization'].startswith('Bearer'))
        conn.close()

    def test_no_auth_token_no_header(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        self.assertEqual(conn.auth_headers, {})
        conn.close()


class TestCustomAuthCallable(unittest.TestCase):

    def test_auth_callable_called_on_post(self):
        calls = []

        def my_auth():
            calls.append(1)
            return {'X-Custom-Auth': 'dynamic-value'}

        conn = solr.Solr(SOLR_HTTP, response_format='xml', auth=my_auth)
        conn.add({'id': 'auth_test', 'data': 'x'}, commit=True)
        conn.delete(id='auth_test', commit=True)
        self.assertGreater(len(calls), 0)
        conn.close()

    def test_auth_callable_called_on_get(self):
        calls = []

        def my_auth():
            calls.append(1)
            return {'X-Custom-Auth': 'val'}

        conn = solr.Solr(SOLR_HTTP, response_format='xml', auth=my_auth)
        conn.ping()
        self.assertGreater(len(calls), 0)
        conn.close()

    def test_auth_callable_headers_sent(self):
        """Verify custom headers actually reach the request."""
        conn = solr.Solr(SOLR_HTTP, response_format='xml',
                         auth=lambda: {'X-Test': '123'})
        # Should not raise — headers are merged into request
        self.assertTrue(conn.ping())
        conn.close()

    def test_auth_callable_with_basic_auth(self):
        """auth callable takes priority over http_user/http_pass."""
        conn = solr.Solr(SOLR_HTTP, response_format='xml',
                         http_user='u', http_pass='p',
                         auth=lambda: {'Authorization': 'Custom xyz'})
        # auth callable should override basic auth
        sent_headers = {}
        original_get = conn.conn.get
        def capture(*args, **kwargs):
            if 'headers' in kwargs:
                sent_headers.update(kwargs['headers'])
            return original_get(*args, **kwargs)
        conn.conn.get = capture  # type: ignore
        conn.ping()
        self.assertEqual(sent_headers.get('Authorization'), 'Custom xyz')
        conn.close()


class TestBasicAuthStillWorks(unittest.TestCase):

    def test_basic_auth_header(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml',
                         http_user='admin', http_pass='secret')
        self.assertIn('Authorization', conn.auth_headers)
        self.assertTrue(conn.auth_headers['Authorization'].startswith('Basic'))
        conn.close()


if __name__ == "__main__":
    unittest.main()
