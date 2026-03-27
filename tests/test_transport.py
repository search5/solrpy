"""Tests for SolrTransport HTTP abstraction layer."""

import unittest
import solr
from solr.transport import SolrTransport
from tests.conftest import SOLR_HTTP


class TestSolrTransport(unittest.TestCase):

    def setUp(self):
        self.conn = solr.Solr(SOLR_HTTP, response_format='xml')
        self.transport = SolrTransport(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_path(self):
        self.assertEqual(self.transport.path, self.conn.path)

    def test_server_version(self):
        self.assertEqual(self.transport.server_version, self.conn.server_version)

    def test_get_json(self):
        data = self.transport.get_json('/admin/ping')
        self.assertEqual(data.get('status'), 'OK')

    def test_get_raw(self):
        raw = self.transport.get_raw('/admin/ping?wt=json')
        self.assertIn(b'OK', raw)

    def test_post_json(self):
        result = self.transport.post_json('/update', {'commit': {}})
        self.assertIn('responseHeader', result)

    def test_post_raw(self):
        headers = {'Content-Type': 'text/xml; charset=utf-8'}
        text = self.transport.post_raw('/update', '<commit/>', headers)
        self.assertIn('status', text)

    def test_companion_classes_use_transport(self):
        """Verify companion classes don't call conn._get/_post directly."""
        import inspect
        import solr.schema, solr.suggest, solr.extract
        for mod in [solr.schema, solr.suggest, solr.extract]:
            src = inspect.getsource(mod)
            self.assertNotIn('._conn._get(', src,
                             f'{mod.__name__} still calls _conn._get directly')
            self.assertNotIn('._conn._post(', src,
                             f'{mod.__name__} still calls _conn._post directly')


if __name__ == "__main__":
    unittest.main()
