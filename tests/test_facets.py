"""Tests for JSON Facet API (Solr 5.0+)."""

import unittest
import solr
import solr.core
from tests.conftest import SOLR_HTTP, SolrConnectionTestCase, get_rand_string


class TestJsonFacet(SolrConnectionTestCase):

    def setUp(self):
        super().setUp()
        self.conn = self.new_connection(response_format='json')
        self.prefix = get_rand_string()
        docs = [
            {'id': '%s_a1' % self.prefix, 'data': 'cat_a', 'user_id': 'u1'},
            {'id': '%s_a2' % self.prefix, 'data': 'cat_a', 'user_id': 'u2'},
            {'id': '%s_b1' % self.prefix, 'data': 'cat_b', 'user_id': 'u1'},
        ]
        self.conn.add_many(docs, commit=True)

    def tearDown(self):
        self.conn.delete_query('id:%s_*' % self.prefix, commit=True)
        super().tearDown()

    def test_json_facet_terms(self):
        resp = self.conn.select(
            'id:%s_*' % self.prefix,
            json_facet={'categories': {'type': 'terms', 'field': 'data'}},
        )
        self.assertTrue(hasattr(resp, 'facets'))
        self.assertIn('categories', resp.facets)

    def test_json_facet_count(self):
        resp = self.conn.select(
            'id:%s_*' % self.prefix,
            json_facet={'total': 'unique(user_id)'},
        )
        self.assertTrue(hasattr(resp, 'facets'))

    def test_json_facet_not_sent_when_none(self):
        resp = self.conn.select('id:%s_*' % self.prefix)
        # facets key may or may not exist, but no json.facet was sent
        self.assertEqual(resp.numFound, 3)

    def test_json_facet_xml_mode(self):
        """json_facet should work in XML mode too (sent as query param)."""
        conn = self.new_connection(response_format='xml')
        resp = conn.select(
            'id:%s_*' % self.prefix,
            json_facet={'categories': {'type': 'terms', 'field': 'data'}},
        )
        # In XML mode, facets come as nested lst elements
        self.assertIsNotNone(resp)

    def test_json_facet_version_guard(self):
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = (4, 10, 0)
        conn.response_format = 'json'
        conn.response_version = 2.2
        conn.path = '/solr/core0'
        handler = solr.SearchHandler(conn, '/select')
        with self.assertRaises(solr.core.SolrVersionError):
            handler('*:*', json_facet={'x': {'type': 'terms', 'field': 'f'}})


if __name__ == "__main__":
    unittest.main()
