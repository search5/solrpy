"""Auto-split from test_all.py"""

import unittest
import solr
import solr.core
from tests.conftest import SOLR_HTTP, SolrConnectionTestCase, get_rand_userdoc


class TestNamedResultTag(unittest.TestCase):
    """XML parser should use the name attribute on <result> tags."""

    def _parse(self, xml):
        from io import StringIO
        return solr.core.parse_query_response(StringIO(xml), {}, None)

    def test_unnamed_result_maps_to_results(self):
        xml = '''<response>
          <lst name="responseHeader"><int name="status">0</int></lst>
          <result name="response" numFound="1" start="0">
            <doc><str name="id">1</str></doc>
          </result>
        </response>'''
        resp = self._parse(xml)
        self.assertTrue(hasattr(resp, 'results'))
        self.assertEqual(len(resp.results), 1)

    def test_named_result_uses_name_attribute(self):
        """Grouped XML responses are parsed into GroupedResult/GroupField/Group objects."""
        xml = '''<response>
          <lst name="responseHeader"><int name="status">0</int></lst>
          <result name="response" numFound="0" start="0"/>
          <lst name="grouped">
            <lst name="category">
              <int name="matches">42</int>
              <int name="ngroups">1</int>
              <arr name="groups">
                <lst>
                  <str name="groupValue">electronics</str>
                  <result name="doclist" numFound="2" start="0">
                    <doc><str name="id">a</str></doc>
                    <doc><str name="id">b</str></doc>
                  </result>
                </lst>
              </arr>
            </lst>
          </lst>
        </response>'''
        from solr.response import GroupedResult, GroupField, Group
        resp = self._parse(xml)
        self.assertIsInstance(resp.grouped, GroupedResult)
        self.assertIn('category', resp.grouped)
        cat = resp.grouped['category']
        self.assertIsInstance(cat, GroupField)
        self.assertEqual(cat.matches, 42)
        self.assertEqual(cat.ngroups, 1)
        groups = cat.groups
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].groupValue, 'electronics')
        self.assertEqual(len(groups[0].doclist), 2)

    def test_response_named_result_still_maps_to_results(self):
        """<result name="response"> should still be accessible as .results."""
        xml = '''<response>
          <lst name="responseHeader"><int name="status">0</int></lst>
          <result name="response" numFound="3" start="0">
            <doc><str name="id">x</str></doc>
            <doc><str name="id">y</str></doc>
            <doc><str name="id">z</str></doc>
          </result>
        </response>'''
        resp = self._parse(xml)
        self.assertTrue(hasattr(resp, 'results'))
        self.assertEqual(len(resp.results), 3)



class TestDoubleTypeParsing(unittest.TestCase):
    """Verify <double> tags are parsed as float."""

    def _parse(self, xml):
        from io import StringIO
        return solr.core.parse_query_response(StringIO(xml), {}, None)

    def test_double_in_stats(self):
        xml = '''<response>
          <lst name="responseHeader"><int name="status">0</int></lst>
          <result name="response" numFound="0" start="0"/>
          <lst name="stats">
            <lst name="stats_fields">
              <lst name="price">
                <double name="min">1.99</double>
                <double name="max">99.99</double>
                <double name="mean">42.5</double>
              </lst>
            </lst>
          </lst>
        </response>'''
        resp = self._parse(xml)
        price_stats = resp.stats['stats_fields']['price']
        self.assertIsInstance(price_stats['min'], float)
        self.assertAlmostEqual(price_stats['min'], 1.99)
        self.assertAlmostEqual(price_stats['max'], 99.99)
        self.assertAlmostEqual(price_stats['mean'], 42.5)



class TestParseJsonResponse(unittest.TestCase):
    """Test the JSON response parser."""

    def test_basic_json_response(self):
        data = {
            "responseHeader": {"status": 0, "QTime": 1},
            "response": {
                "numFound": 2, "start": 0,
                "docs": [
                    {"id": "1", "title": "First"},
                    {"id": "2", "title": "Second"},
                ],
            },
        }
        resp = solr.core.parse_json_response(data, {}, None)
        self.assertEqual(resp.numFound, 2)
        self.assertEqual(resp.start, 0)
        self.assertEqual(len(resp.results), 2)
        self.assertEqual(resp.results[0]['id'], '1')
        self.assertEqual(resp.header['status'], 0)

    def test_json_response_with_highlighting(self):
        data = {
            "responseHeader": {"status": 0, "QTime": 1},
            "response": {
                "numFound": 1, "start": 0,
                "docs": [{"id": "1"}],
            },
            "highlighting": {
                "1": {"title": ["<em>match</em>"]},
            },
        }
        resp = solr.core.parse_json_response(data, {}, None)
        self.assertTrue(hasattr(resp, 'highlighting'))
        self.assertIn('1', resp.highlighting)

    def test_json_response_with_facets(self):
        data = {
            "responseHeader": {"status": 0, "QTime": 1},
            "response": {
                "numFound": 0, "start": 0, "docs": [],
            },
            "facet_counts": {
                "facet_fields": {"category": ["books", 5, "music", 3]},
            },
        }
        resp = solr.core.parse_json_response(data, {}, None)
        self.assertTrue(hasattr(resp, 'facet_counts'))

    def test_json_response_empty(self):
        data = {
            "responseHeader": {"status": 0, "QTime": 0},
            "response": {"numFound": 0, "start": 0, "docs": []},
        }
        resp = solr.core.parse_json_response(data, {}, None)
        self.assertEqual(resp.numFound, 0)
        self.assertEqual(len(resp.results), 0)

    def test_json_response_maxScore(self):
        data = {
            "responseHeader": {"status": 0, "QTime": 0},
            "response": {
                "numFound": 1, "start": 0, "maxScore": 1.5,
                "docs": [{"id": "1"}],
            },
        }
        resp = solr.core.parse_json_response(data, {}, None)
        self.assertAlmostEqual(resp.maxScore, 1.5)



class TestGzipResponse(unittest.TestCase):
    """Test that gzip-compressed responses are handled."""

    def test_gzip_header_sent(self):
        conn = solr.Solr(SOLR_HTTP)
        self.assertIn('Accept-Encoding', conn.form_headers)
        self.assertIn('gzip', conn.form_headers['Accept-Encoding'])
        conn.close()

    def test_gzip_header_in_xml_headers(self):
        conn = solr.Solr(SOLR_HTTP)
        self.assertIn('Accept-Encoding', conn.xmlheaders)
        self.assertIn('gzip', conn.xmlheaders['Accept-Encoding'])
        conn.close()

    def test_query_works_with_gzip(self):
        """Solr may or may not gzip the response, but the query should work."""
        conn = solr.Solr(SOLR_HTTP)
        conn.add({'id': 'gzip_test', 'data': 'test'}, commit=True)
        response = conn.select('id:gzip_test')
        self.assertEqual(len(response.results), 1)
        conn.delete(id='gzip_test', commit=True)
        conn.close()


# ===================================================================
# 1.0.5 tests — SolrConnection removed
# ===================================================================

