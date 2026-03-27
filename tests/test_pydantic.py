"""Tests for Pydantic response model support."""

import unittest
import solr
from tests.conftest import SOLR_HTTP, SolrConnectionTestCase, get_rand_string

try:
    from pydantic import BaseModel
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


@unittest.skipUnless(HAS_PYDANTIC, "pydantic not installed")
class TestResponseAsModels(SolrConnectionTestCase):

    def setUp(self):
        super().setUp()
        self.conn = self.new_connection()
        self.prefix = get_rand_string()
        self.conn.add_many([
            {'id': '%s_1' % self.prefix, 'data': 'alpha', 'user_id': 'u1'},
            {'id': '%s_2' % self.prefix, 'data': 'beta', 'user_id': 'u2'},
            {'id': '%s_3' % self.prefix, 'data': 'gamma', 'user_id': 'u1'},
        ], commit=True)

    def tearDown(self):
        self.conn.delete_query('id:%s_*' % self.prefix, commit=True)
        super().tearDown()

    def test_as_models(self):
        class Doc(BaseModel):
            id: str
            data: str
            user_id: str

        resp = self.conn.select('id:%s_*' % self.prefix)
        docs = resp.as_models(Doc)
        self.assertEqual(len(docs), 3)
        self.assertIsInstance(docs[0], Doc)
        self.assertEqual(docs[0].id, '%s_1' % self.prefix)

    def test_as_models_with_optional_field(self):
        class Doc(BaseModel):
            id: str
            data: str
            missing_field: str | None = None

        resp = self.conn.select('id:%s_*' % self.prefix)
        docs = resp.as_models(Doc)
        self.assertEqual(len(docs), 3)
        self.assertIsNone(docs[0].missing_field)

    def test_as_models_empty_response(self):
        class Doc(BaseModel):
            id: str

        resp = self.conn.select('id:nonexistent_xyz')
        docs = resp.as_models(Doc)
        self.assertEqual(len(docs), 0)


@unittest.skipUnless(HAS_PYDANTIC, "pydantic not installed")
class TestSelectWithModel(SolrConnectionTestCase):

    def setUp(self):
        super().setUp()
        self.conn = self.new_connection()
        self.prefix = get_rand_string()
        self.conn.add_many([
            {'id': '%s_1' % self.prefix, 'data': 'hello', 'user_id': 'u1'},
            {'id': '%s_2' % self.prefix, 'data': 'world', 'user_id': 'u2'},
        ], commit=True)

    def tearDown(self):
        self.conn.delete_query('id:%s_*' % self.prefix, commit=True)
        super().tearDown()

    def test_select_with_model(self):
        class Doc(BaseModel):
            id: str
            data: str

        resp = self.conn.select('id:%s_*' % self.prefix, model=Doc)
        self.assertEqual(len(resp.results), 2)
        self.assertIsInstance(resp.results[0], Doc)
        self.assertEqual(resp.results[0].data, 'hello')

    def test_select_without_model_unchanged(self):
        resp = self.conn.select('id:%s_*' % self.prefix)
        self.assertIsInstance(resp.results[0], dict)


@unittest.skipUnless(HAS_PYDANTIC, "pydantic not installed")
class TestGetWithModel(unittest.TestCase):

    def setUp(self):
        self.conn = solr.Solr(SOLR_HTTP, response_format='xml')
        self.conn.add({'id': 'pydantic_get_test', 'data': 'test'}, commit=True)

    def tearDown(self):
        self.conn.delete(id='pydantic_get_test', commit=True)
        self.conn.close()

    def test_get_single_with_model(self):
        class Doc(BaseModel):
            id: str
            data: str

        doc = self.conn.get(id='pydantic_get_test', model=Doc)
        self.assertIsInstance(doc, Doc)
        self.assertEqual(doc.id, 'pydantic_get_test')

    def test_get_single_not_found_returns_none(self):
        class Doc(BaseModel):
            id: str

        doc = self.conn.get(id='nonexistent_xyz', model=Doc)
        self.assertIsNone(doc)

    def test_get_multiple_with_model(self):
        class Doc(BaseModel):
            id: str

        docs = self.conn.get(ids=['pydantic_get_test'], model=Doc)
        self.assertIsInstance(docs, list)
        self.assertGreater(len(docs), 0)
        self.assertIsInstance(docs[0], Doc)


if __name__ == "__main__":
    unittest.main()
