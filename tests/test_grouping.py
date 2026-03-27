"""Tests for Solr Grouping / Field Collapsing (Solr 3.3+)."""

import json
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

import solr
from solr.response import Group, GroupField, GroupedResult, Results
from solr.parsers import parse_json_response, parse_query_response
from solr.exceptions import SolrVersionError
from tests.conftest import SOLR_HTTP, SolrConnectionTestCase


# ---------------------------------------------------------------------------
# Unit tests for GroupedResult / GroupField / Group
# ---------------------------------------------------------------------------

class TestGroupClass(unittest.TestCase):
    """Tests for the Group wrapper class."""

    def _make_group_json(self, group_value, docs):
        """Build a JSON-format group dict."""
        return {
            'groupValue': group_value,
            'doclist': {
                'numFound': len(docs),
                'start': 0,
                'docs': docs,
            },
        }

    def _make_group_xml(self, group_value, docs):
        """Build an XML-format group dict (doclist is already a Results obj)."""
        r = Results(docs)
        r.numFound = str(len(docs))
        r.start = '0'
        return {
            'groupValue': group_value,
            'doclist': r,
        }

    def test_group_value_json(self):
        g = Group(self._make_group_json('electronics', [{'id': '1'}]))
        self.assertEqual(g.groupValue, 'electronics')

    def test_group_value_none(self):
        """groupValue can be None for documents without the grouped field."""
        g = Group({'groupValue': None, 'doclist': {'numFound': 1, 'start': 0, 'docs': [{'id': '99'}]}})
        self.assertIsNone(g.groupValue)

    def test_doclist_from_json(self):
        docs = [{'id': '1', 'title': 'A'}, {'id': '2', 'title': 'B'}]
        g = Group(self._make_group_json('electronics', docs))
        dl = g.doclist
        self.assertIsInstance(dl, Results)
        self.assertEqual(len(dl), 2)
        self.assertEqual(dl.numFound, 2)
        self.assertEqual(dl.start, 0)
        self.assertEqual(dl[0]['id'], '1')

    def test_doclist_from_xml(self):
        """When doclist is already a Results object (XML parsing), wrap it correctly."""
        docs = [{'id': 'a'}, {'id': 'b'}]
        g = Group(self._make_group_xml('books', docs))
        dl = g.doclist
        self.assertIsInstance(dl, Results)
        self.assertEqual(len(dl), 2)
        self.assertEqual(dl.numFound, 2)
        self.assertEqual(dl.start, 0)

    def test_repr(self):
        g = Group({'groupValue': 'test', 'doclist': {'numFound': 3, 'start': 0, 'docs': [{}, {}, {}]}})
        r = repr(g)
        self.assertIn('test', r)
        self.assertIn('3', r)


class TestGroupFieldClass(unittest.TestCase):
    """Tests for the GroupField wrapper class."""

    def _make_field(self, matches, ngroups, groups):
        return GroupField({
            'matches': matches,
            'ngroups': ngroups,
            'groups': groups,
        })

    def test_matches(self):
        f = self._make_field(100, 5, [])
        self.assertEqual(f.matches, 100)

    def test_ngroups_present(self):
        f = self._make_field(100, 5, [])
        self.assertEqual(f.ngroups, 5)

    def test_ngroups_absent(self):
        """ngroups is None when group.ngroups was not requested."""
        f = GroupField({'matches': 100, 'groups': []})
        self.assertIsNone(f.ngroups)

    def test_groups_list(self):
        raw_groups = [
            {'groupValue': 'a', 'doclist': {'numFound': 1, 'start': 0, 'docs': [{'id': '1'}]}},
            {'groupValue': 'b', 'doclist': {'numFound': 2, 'start': 0, 'docs': [{'id': '2'}, {'id': '3'}]}},
        ]
        f = self._make_field(3, 2, raw_groups)
        groups = f.groups
        self.assertEqual(len(groups), 2)
        self.assertIsInstance(groups[0], Group)
        self.assertEqual(groups[0].groupValue, 'a')
        self.assertEqual(groups[1].groupValue, 'b')

    def test_repr(self):
        f = self._make_field(10, 3, [])
        r = repr(f)
        self.assertIn('10', r)
        self.assertIn('3', r)


class TestGroupedResultClass(unittest.TestCase):
    """Tests for the GroupedResult wrapper class."""

    def _make_raw(self):
        return {
            'category': {
                'matches': 10,
                'ngroups': 3,
                'groups': [
                    {'groupValue': 'electronics', 'doclist': {'numFound': 4, 'start': 0, 'docs': []}},
                    {'groupValue': 'books', 'doclist': {'numFound': 6, 'start': 0, 'docs': []}},
                ],
            },
            'brand': {
                'matches': 10,
                'ngroups': 2,
                'groups': [],
            },
        }

    def test_getitem(self):
        gr = GroupedResult(self._make_raw())
        self.assertIsInstance(gr['category'], GroupField)

    def test_getitem_missing(self):
        gr = GroupedResult(self._make_raw())
        with self.assertRaises(KeyError):
            _ = gr['nonexistent']

    def test_contains(self):
        gr = GroupedResult(self._make_raw())
        self.assertIn('category', gr)
        self.assertNotIn('nonexistent', gr)

    def test_iter(self):
        gr = GroupedResult(self._make_raw())
        fields = list(gr)
        self.assertIn('category', fields)
        self.assertIn('brand', fields)

    def test_len(self):
        gr = GroupedResult(self._make_raw())
        self.assertEqual(len(gr), 2)

    def test_repr(self):
        gr = GroupedResult(self._make_raw())
        r = repr(gr)
        self.assertIn('category', r)


# ---------------------------------------------------------------------------
# JSON parser integration tests
# ---------------------------------------------------------------------------

class TestParseJsonGroupedResponse(unittest.TestCase):
    """Verify parse_json_response produces GroupedResult from grouped data."""

    def _make_json_data(self):
        return {
            'responseHeader': {'status': 0, 'QTime': 5},
            'grouped': {
                'category': {
                    'matches': 10,
                    'ngroups': 3,
                    'groups': [
                        {
                            'groupValue': 'electronics',
                            'doclist': {
                                'numFound': 4,
                                'start': 0,
                                'docs': [
                                    {'id': '1', 'title': 'Phone'},
                                    {'id': '2', 'title': 'Laptop'},
                                ],
                            },
                        },
                        {
                            'groupValue': 'books',
                            'doclist': {
                                'numFound': 6,
                                'start': 0,
                                'docs': [{'id': '3', 'title': 'Python'}],
                            },
                        },
                        {
                            'groupValue': None,
                            'doclist': {
                                'numFound': 0,
                                'start': 0,
                                'docs': [],
                            },
                        },
                    ],
                },
            },
        }

    def test_grouped_is_grouped_result(self):
        resp = parse_json_response(self._make_json_data(), {}, None)
        self.assertIsInstance(resp.grouped, GroupedResult)

    def test_grouped_field_access(self):
        resp = parse_json_response(self._make_json_data(), {}, None)
        cat = resp.grouped['category']
        self.assertIsInstance(cat, GroupField)
        self.assertEqual(cat.matches, 10)
        self.assertEqual(cat.ngroups, 3)

    def test_grouped_groups(self):
        resp = parse_json_response(self._make_json_data(), {}, None)
        groups = resp.grouped['category'].groups
        self.assertEqual(len(groups), 3)
        self.assertEqual(groups[0].groupValue, 'electronics')
        self.assertEqual(len(groups[0].doclist), 2)
        self.assertEqual(groups[0].doclist.numFound, 4)

    def test_grouped_null_group_value(self):
        resp = parse_json_response(self._make_json_data(), {}, None)
        groups = resp.grouped['category'].groups
        self.assertIsNone(groups[2].groupValue)

    def test_response_without_grouped(self):
        """Non-grouped responses must not have a grouped attribute."""
        data = {
            'responseHeader': {'status': 0, 'QTime': 1},
            'response': {'numFound': 1, 'start': 0, 'docs': [{'id': '1'}]},
        }
        resp = parse_json_response(data, {}, None)
        self.assertFalse(hasattr(resp, 'grouped'))


# ---------------------------------------------------------------------------
# XML parser integration tests
# ---------------------------------------------------------------------------

class TestParseXmlGroupedResponse(unittest.TestCase):
    """Verify parse_query_response produces GroupedResult from grouped XML."""

    def _parse(self, xml):
        return parse_query_response(StringIO(xml), {}, None)

    def _grouped_xml(self):
        return '''<response>
          <lst name="responseHeader">
            <int name="status">0</int>
            <int name="QTime">5</int>
          </lst>
          <result name="response" numFound="0" start="0"/>
          <lst name="grouped">
            <lst name="category">
              <int name="matches">10</int>
              <int name="ngroups">3</int>
              <arr name="groups">
                <lst>
                  <str name="groupValue">electronics</str>
                  <result name="doclist" numFound="4" start="0">
                    <doc><str name="id">1</str><str name="title">Phone</str></doc>
                    <doc><str name="id">2</str><str name="title">Laptop</str></doc>
                  </result>
                </lst>
                <lst>
                  <str name="groupValue">books</str>
                  <result name="doclist" numFound="6" start="0">
                    <doc><str name="id">3</str><str name="title">Python</str></doc>
                  </result>
                </lst>
              </arr>
            </lst>
          </lst>
        </response>'''

    def test_grouped_is_grouped_result(self):
        resp = self._parse(self._grouped_xml())
        self.assertIsInstance(resp.grouped, GroupedResult)

    def test_grouped_field_access(self):
        resp = self._parse(self._grouped_xml())
        cat = resp.grouped['category']
        self.assertIsInstance(cat, GroupField)
        self.assertEqual(cat.matches, 10)
        self.assertEqual(cat.ngroups, 3)

    def test_grouped_groups(self):
        resp = self._parse(self._grouped_xml())
        groups = resp.grouped['category'].groups
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0].groupValue, 'electronics')
        dl = groups[0].doclist
        self.assertIsInstance(dl, Results)
        self.assertEqual(len(dl), 2)
        self.assertEqual(dl.numFound, 4)
        self.assertEqual(dl[0]['id'], '1')

    def test_response_without_grouped(self):
        xml = '''<response>
          <lst name="responseHeader"><int name="status">0</int></lst>
          <result name="response" numFound="2" start="0">
            <doc><str name="id">x</str></doc>
            <doc><str name="id">y</str></doc>
          </result>
        </response>'''
        resp = self._parse(xml)
        self.assertFalse(hasattr(resp, 'grouped'))


# ---------------------------------------------------------------------------
# Version guard tests
# ---------------------------------------------------------------------------

class TestGroupVersionGuard(unittest.TestCase):
    """group=True raises SolrVersionError on Solr < 3.3."""

    def _make_conn(self, version):
        conn = MagicMock()
        conn.server_version = version
        conn.response_format = 'json'
        conn.debug = False
        conn.path = '/solr/core0'
        conn.arg_separator = '_'
        return conn

    def test_group_raises_on_old_solr(self):
        """group=True should raise SolrVersionError for Solr < 3.3."""
        from solr.core import SearchHandler
        conn = self._make_conn((3, 2, 0))
        handler = SearchHandler(conn)
        with self.assertRaises(SolrVersionError) as cm:
            handler(q='*:*', group='true', group_field='category')
        self.assertIn('3', str(cm.exception))

    def test_group_allowed_on_solr_33(self):
        """group=True should not raise for Solr >= 3.3."""
        from solr.core import SearchHandler
        conn = self._make_conn((3, 3, 0))
        # Mock the raw() call to return a valid JSON response
        conn.response_format = 'json'
        handler = SearchHandler(conn)
        handler._raw_json = MagicMock(return_value={
            'responseHeader': {'status': 0, 'QTime': 1},
            'grouped': {
                'category': {
                    'matches': 0,
                    'groups': [],
                },
            },
        })
        resp = handler(q='*:*', group='true', group_field='category')
        self.assertIsNotNone(resp)

    def test_no_group_no_version_check(self):
        """Queries without group= should not trigger the version check."""
        from solr.core import SearchHandler
        conn = self._make_conn((1, 2, 0))
        conn.response_format = 'json'
        handler = SearchHandler(conn)
        handler._raw_json = MagicMock(return_value={
            'responseHeader': {'status': 0, 'QTime': 1},
            'response': {'numFound': 0, 'start': 0, 'docs': []},
        })
        resp = handler(q='*:*')
        self.assertIsNotNone(resp)


# ---------------------------------------------------------------------------
# Integration tests (require a running Solr instance)
# ---------------------------------------------------------------------------

try:
    import socket
    _s = socket.create_connection(('localhost', 8983), timeout=0.5)
    _s.close()
    SOLR_AVAILABLE = True
except (OSError, ConnectionRefusedError):
    SOLR_AVAILABLE = False


@unittest.skipUnless(SOLR_AVAILABLE, "Solr not available on localhost:8983")
class TestGroupingIntegration(SolrConnectionTestCase):
    """Integration tests for grouped queries against a live Solr instance."""

    def setUp(self):
        super().setUp()
        self.conn = self.new_connection(response_format='json')
        # Use 'user_id' as the grouping field (it exists in the test schema).
        # Two documents share user_id 'grp_shared', one has 'grp_unique'.
        self.conn.delete('id:g1 OR id:g2 OR id:g3', commit=True)
        docs = [
            {'id': 'g1', 'user_id': 'grp_shared', 'data': 'doc one'},
            {'id': 'g2', 'user_id': 'grp_shared', 'data': 'doc two'},
            {'id': 'g3', 'user_id': 'grp_unique', 'data': 'doc three'},
        ]
        for doc in docs:
            self.conn.add(doc)
        self.conn.commit()

    def tearDown(self):
        self.conn.delete('id:g1 OR id:g2 OR id:g3', commit=True)
        super().tearDown()

    def test_grouped_response(self):
        resp = self.conn.select(
            'id:g1 OR id:g2 OR id:g3',
            score=False,
            group='true',
            group_field='user_id',
            group_ngroups='true',
        )
        self.assertIsInstance(resp.grouped, GroupedResult)
        self.assertIn('user_id', resp.grouped)
        field = resp.grouped['user_id']
        self.assertEqual(field.matches, 3)
        self.assertEqual(field.ngroups, 2)
        self.assertEqual(len(field.groups), 2)

    def test_group_doclist_contents(self):
        resp = self.conn.select(
            'id:g1 OR id:g2',
            score=False,
            group='true',
            group_field='user_id',
        )
        groups = resp.grouped['user_id'].groups
        self.assertGreater(len(groups), 0)
        for group in groups:
            self.assertIsNotNone(group.groupValue)
            self.assertIsInstance(group.doclist, Results)
            self.assertGreater(len(group.doclist), 0)


if __name__ == '__main__':
    unittest.main()
