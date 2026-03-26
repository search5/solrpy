"""Tests for cursor-based pagination (Solr 4.7+)."""

import unittest
import solr
import solr.core
from tests.conftest import SOLR_HTTP, SolrConnectionTestCase, get_rand_string


class TestCursorNext(SolrConnectionTestCase):

    def setUp(self):
        super().setUp()
        self.conn = self.new_connection()
        # Add 25 documents for pagination testing
        self.test_prefix = get_rand_string()
        docs = [{'id': '%s_%02d' % (self.test_prefix, i), 'data': 'cursor_test'}
                for i in range(25)]
        self.conn.add_many(docs, commit=True)

    def tearDown(self):
        self.conn.delete_query('data:cursor_test', commit=True)
        super().tearDown()

    def test_cursor_next_returns_next_page(self):
        resp = self.conn.select(
            'data:cursor_test', sort='id asc', cursorMark='*', rows=10)
        self.assertEqual(len(resp.results), 10)
        next_resp = resp.cursor_next()
        self.assertIsNotNone(next_resp)
        self.assertEqual(len(next_resp.results), 10)

    def test_cursor_next_returns_none_at_end(self):
        resp = self.conn.select(
            'data:cursor_test', sort='id asc', cursorMark='*', rows=50)
        # All 25 docs in one page; Solr still returns nextCursorMark
        # but second call should find nextCursorMark == cursorMark → None
        next_resp = resp.cursor_next()
        if next_resp is not None:
            # The second page should be empty and return None on next
            final = next_resp.cursor_next()
            self.assertIsNone(final)

    def test_cursor_next_iterates_all(self):
        all_ids = set()
        resp = self.conn.select(
            'data:cursor_test', sort='id asc', cursorMark='*', rows=10)
        while resp is not None:
            for doc in resp.results:
                all_ids.add(doc['id'])
            resp = resp.cursor_next()
        self.assertEqual(len(all_ids), 25)

    def test_cursor_next_without_cursormark_returns_none(self):
        resp = self.conn.select('data:cursor_test', sort='id asc', rows=10)
        result = resp.cursor_next()
        self.assertIsNone(result)

    def test_version_guard(self):
        from solr.response import Response
        resp = Response(None)
        resp._params = {'cursorMark': '*'}
        resp.nextCursorMark = 'AoE='  # simulate a cursor
        resp._conn_version = (4, 0, 0)
        with self.assertRaises(solr.core.SolrVersionError):
            resp.cursor_next()


class TestIterCursor(SolrConnectionTestCase):

    def setUp(self):
        super().setUp()
        self.conn = self.new_connection()
        self.test_prefix = get_rand_string()
        docs = [{'id': '%s_%02d' % (self.test_prefix, i), 'data': 'iter_test'}
                for i in range(25)]
        self.conn.add_many(docs, commit=True)

    def tearDown(self):
        self.conn.delete_query('data:iter_test', commit=True)
        super().tearDown()

    def test_iter_cursor_yields_all(self):
        all_ids = set()
        for batch in self.conn.iter_cursor('data:iter_test', sort='id asc', rows=10):
            for doc in batch.results:
                all_ids.add(doc['id'])
        self.assertEqual(len(all_ids), 25)

    def test_iter_cursor_sort_required(self):
        with self.assertRaises(ValueError):
            # sort is required for cursor pagination
            next(self.conn.iter_cursor('data:iter_test'))

    def test_iter_cursor_empty_result(self):
        batches = list(self.conn.iter_cursor(
            'data:nonexistent_xyz', sort='id asc', rows=10))
        self.assertEqual(len(batches), 1)  # one empty batch
        self.assertEqual(len(batches[0].results), 0)


if __name__ == "__main__":
    unittest.main()
