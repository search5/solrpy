"""Tests for Streaming Expressions (Solr 5.0+)."""

import unittest
import solr
import solr.core

CLOUD_URL = "http://localhost:8985/solr"
COLLECTION = "testcol"


# ===================================================================
# Expression builder tests (no Solr needed)
# ===================================================================

class TestStreamExpressionBuilders(unittest.TestCase):

    def test_import(self):
        from solr.stream import search, merge, rollup, top, unique
        from solr.stream import count, sum, avg, min, max

    def test_search_expr(self):
        from solr.stream import search
        expr = search('col1', q='*:*', fl='id,title', sort='id asc')
        s = str(expr)
        self.assertIn('search(col1', s)
        self.assertIn('q=', s)
        self.assertIn('fl=', s)
        self.assertIn('sort="id asc"', s)  # has space → quoted

    def test_search_with_rows(self):
        from solr.stream import search
        expr = search('col1', q='*:*', fl='id', sort='id asc', rows=10)
        self.assertIn('rows=10', str(expr))

    def test_top_expr(self):
        from solr.stream import search, top
        expr = top(
            search('col1', q='*:*', fl='id,price', sort='price desc'),
            n=5, sort='price desc')
        s = str(expr)
        self.assertTrue(s.startswith('top('))
        self.assertIn('n=5', s)

    def test_unique_expr(self):
        from solr.stream import search, unique
        expr = unique(
            search('col1', q='*:*', fl='id,title', sort='title asc'),
            over='title')
        s = str(expr)
        self.assertTrue(s.startswith('unique('))
        self.assertIn('over=title', s)

    def test_rollup_with_aggregates(self):
        from solr.stream import search, rollup, count, sum
        expr = rollup(
            search('col1', q='*:*', fl='category,price', sort='category asc'),
            over='category',
            count=count('*'),
            total=sum('price'))
        s = str(expr)
        self.assertIn('rollup(', s)
        self.assertIn('over=category', s)
        self.assertIn('count(*)', s)
        self.assertIn('sum(price)', s)

    def test_merge_expr(self):
        from solr.stream import search, merge
        expr = merge(
            search('col1', q='cat:a', fl='id', sort='id asc'),
            search('col1', q='cat:b', fl='id', sort='id asc'),
            on='id asc')
        s = str(expr)
        self.assertTrue(s.startswith('merge('))
        self.assertIn('on="id asc"', s)

    def test_pipe_operator(self):
        from solr.stream import search, unique
        expr = search('col1', q='*:*', fl='id,title', sort='title asc') \
               | unique(over='title')
        s = str(expr)
        self.assertTrue(s.startswith('unique('))
        self.assertIn('search(', s)

    def test_double_pipe(self):
        from solr.stream import search, unique, top
        expr = (search('col1', q='*:*', fl='id,title', sort='title asc')
                | unique(over='title')
                | top(n=5, sort='title asc'))
        s = str(expr)
        self.assertTrue(s.startswith('top('))
        self.assertIn('unique(', s)
        self.assertIn('search(', s)

    def test_aggregate_functions(self):
        from solr.stream import count, sum, avg, min, max
        self.assertEqual(str(count('*')), 'count(*)')
        self.assertEqual(str(sum('price')), 'sum(price)')
        self.assertEqual(str(avg('price')), 'avg(price)')
        self.assertEqual(str(min('price')), 'min(price)')
        self.assertEqual(str(max('price')), 'max(price)')


# ===================================================================
# Live streaming tests (SolrCloud required)
# ===================================================================

class TestStreamLive(unittest.TestCase):

    def setUp(self):
        try:
            self.conn = solr.Solr(CLOUD_URL + '/' + COLLECTION)
        except Exception:
            self.skipTest("SolrCloud not available")
        if self.conn.server_version < (5, 0):
            self.conn.close()
            self.skipTest("Streaming requires Solr 5.0+")

    def tearDown(self):
        self.conn.close()

    def test_basic_stream(self):
        from solr.stream import search
        expr = search(COLLECTION, q='*:*', fl='id', sort='id asc', rows=3)
        results = list(self.conn.stream(expr))
        self.assertGreater(len(results), 0)
        self.assertIn('id', results[0])

    def test_stream_all_docs(self):
        from solr.stream import search
        expr = search(COLLECTION, q='*:*', fl='id,title', sort='id asc')
        results = list(self.conn.stream(expr))
        self.assertEqual(len(results), 5)

    def test_stream_with_pipe(self):
        from solr.stream import search, top
        expr = (search(COLLECTION, q='*:*', fl='id,title', sort='id asc')
                | top(n=2, sort='id asc'))
        results = list(self.conn.stream(expr))
        self.assertEqual(len(results), 2)


if __name__ == "__main__":
    unittest.main()
