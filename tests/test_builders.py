"""Tests for Facet, Field, Sort builder classes."""

import unittest
import solr
import solr.core
from tests.conftest import SOLR_HTTP, SolrConnectionTestCase, get_rand_string


# ===================================================================
# Field builder tests
# ===================================================================

class TestFieldBuilder(unittest.TestCase):

    def test_import(self):
        from solr import Field
        self.assertTrue(callable(Field))

    def test_simple_field(self):
        from solr import Field
        f = Field('id')
        self.assertEqual(str(f), 'id')

    def test_field_with_alias(self):
        from solr import Field
        f = Field('price', alias='price_usd')
        self.assertEqual(str(f), 'price_usd:price')

    def test_function_field(self):
        from solr import Field
        f = Field.func('sum', 'price', 'tax')
        self.assertEqual(str(f), 'sum(price,tax)')

    def test_transformer(self):
        from solr import Field
        f = Field.transformer('explain')
        self.assertEqual(str(f), '[explain]')

    def test_transformer_with_params(self):
        from solr import Field
        f = Field.transformer('child', parentFilter='type:parent')
        self.assertIn('[child', str(f))
        self.assertIn('parentFilter=type:parent', str(f))

    def test_score(self):
        from solr import Field
        f = Field.score()
        self.assertEqual(str(f), 'score')

    def test_multiple_fields_to_string(self):
        from solr import Field
        fields = [Field('id'), Field('title'), Field('price', alias='p')]
        result = ','.join(str(f) for f in fields)
        self.assertEqual(result, 'id,title,p:price')


# ===================================================================
# Sort builder tests
# ===================================================================

class TestSortBuilder(unittest.TestCase):

    def test_import(self):
        from solr import Sort
        self.assertTrue(callable(Sort))

    def test_simple_sort(self):
        from solr import Sort
        s = Sort('price', 'desc')
        self.assertEqual(str(s), 'price desc')

    def test_asc_sort(self):
        from solr import Sort
        s = Sort('title', 'asc')
        self.assertEqual(str(s), 'title asc')

    def test_func_sort(self):
        from solr import Sort
        s = Sort.func('geodist()', 'asc')
        self.assertEqual(str(s), 'geodist() asc')

    def test_multiple_sorts_to_string(self):
        from solr import Sort
        sorts = [Sort('category', 'asc'), Sort('price', 'desc')]
        result = ','.join(str(s) for s in sorts)
        self.assertEqual(result, 'category asc,price desc')


# ===================================================================
# Facet builder tests
# ===================================================================

class TestFacetBuilder(unittest.TestCase):

    def test_import(self):
        from solr import Facet
        self.assertTrue(callable(Facet.field))

    def test_field_facet_params(self):
        from solr import Facet
        f = Facet.field('category', mincount=1, limit=10)
        params = f.to_params()
        self.assertEqual(params['facet'], 'true')
        self.assertIn('category', params['facet.field'])
        self.assertEqual(params['f.category.facet.mincount'], '1')
        self.assertEqual(params['f.category.facet.limit'], '10')

    def test_range_facet_params(self):
        from solr import Facet
        f = Facet.range('price', start=0, end=100, gap=10)
        params = f.to_params()
        self.assertEqual(params['facet'], 'true')
        self.assertIn('price', params['facet.range'])
        self.assertEqual(params['f.price.facet.range.start'], '0')
        self.assertEqual(params['f.price.facet.range.end'], '100')
        self.assertEqual(params['f.price.facet.range.gap'], '10')

    def test_query_facet_params(self):
        from solr import Facet
        f = Facet.query('cheap', 'price:[0 TO 50]')
        params = f.to_params()
        self.assertEqual(params['facet'], 'true')
        self.assertIn('price:[0 TO 50]', params['facet.query'])

    def test_pivot_facet_params(self):
        from solr import Facet
        f = Facet.pivot('category', 'author')
        params = f.to_params()
        self.assertEqual(params['facet'], 'true')
        self.assertEqual(params['facet.pivot'], 'category,author')

    def test_multiple_facets_merge(self):
        from solr import Facet
        facets = [
            Facet.field('category', mincount=1),
            Facet.field('author', limit=5),
        ]
        merged: dict = {}
        for f in facets:
            for k, v in f.to_params().items():
                if k in merged and k == 'facet.field':
                    if isinstance(merged[k], list):
                        merged[k].append(v)
                    else:
                        merged[k] = [merged[k], v]
                else:
                    merged[k] = v
        self.assertEqual(merged['facet'], 'true')
        self.assertIn('category', merged['facet.field'])
        self.assertIn('author', merged['facet.field'])


# ===================================================================
# Integration tests — using builders with select()
# ===================================================================

class TestBuildersWithSelect(SolrConnectionTestCase):

    def setUp(self):
        super().setUp()
        self.conn = self.new_connection()
        self.prefix = get_rand_string()
        docs = [
            {'id': '%s_1' % self.prefix, 'data': 'cat_a', 'user_id': 'u1'},
            {'id': '%s_2' % self.prefix, 'data': 'cat_a', 'user_id': 'u2'},
            {'id': '%s_3' % self.prefix, 'data': 'cat_b', 'user_id': 'u1'},
        ]
        self.conn.add_many(docs, commit=True)

    def tearDown(self):
        self.conn.delete_query('id:%s_*' % self.prefix, commit=True)
        super().tearDown()

    def test_fields_as_objects(self):
        from solr import Field
        resp = self.conn.select(
            'id:%s_*' % self.prefix,
            fields=[Field('id'), Field('data')],
        )
        self.assertEqual(resp.numFound, 3)
        self.assertIn('id', resp.results[0])

    def test_fields_raw_string_still_works(self):
        resp = self.conn.select('id:%s_*' % self.prefix, fl='id,data')
        self.assertEqual(resp.numFound, 3)

    def test_sort_as_objects(self):
        from solr import Sort
        resp = self.conn.select(
            'id:%s_*' % self.prefix,
            sort=[Sort('id', 'asc')],
        )
        self.assertEqual(resp.numFound, 3)
        ids = [d['id'] for d in resp.results]
        self.assertEqual(ids, sorted(ids))

    def test_sort_raw_string_still_works(self):
        resp = self.conn.select(
            'id:%s_*' % self.prefix, sort='id asc')
        self.assertEqual(resp.numFound, 3)

    def test_facets_as_objects(self):
        from solr import Facet
        resp = self.conn.select(
            'id:%s_*' % self.prefix,
            facets=[Facet.field('data')],
        )
        self.assertIsNotNone(resp)

    def test_facets_raw_passthrough_still_works(self):
        resp = self.conn.select(
            'id:%s_*' % self.prefix,
            facet='true', facet_field='data',
        )
        self.assertIsNotNone(resp)


if __name__ == "__main__":
    unittest.main()
