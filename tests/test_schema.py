"""Tests for Schema API client (Solr 4.2+)."""

import unittest
import solr
import solr.core
from solr.schema import SchemaAPI
from tests.conftest import SOLR_HTTP


class TestSchemaAPI(unittest.TestCase):

    def setUp(self):
        self.conn = solr.Solr(SOLR_HTTP, response_format='xml')
        self.schema = SchemaAPI(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_explicit_creation(self):
        self.assertIsInstance(self.schema, SchemaAPI)

    def test_conn_has_no_schema_attribute(self):
        self.assertFalse(hasattr(self.conn, 'schema'))


class TestSchemaFields(unittest.TestCase):

    def setUp(self):
        self.conn = solr.Solr(SOLR_HTTP, response_format='xml')
        self.schema = SchemaAPI(self.conn)

    def tearDown(self):
        try:
            self.schema.delete_field('test_schema_field')
        except Exception:
            pass
        self.conn.close()

    def test_list_fields(self):
        fields = self.schema.fields()
        self.assertIsInstance(fields, list)
        names = [f['name'] for f in fields]
        self.assertIn('id', names)

    def test_add_and_delete_field(self):
        self.schema.add_field('test_schema_field', 'string',
                              stored=True, indexed=True)
        fields = self.schema.fields()
        names = [f['name'] for f in fields]
        self.assertIn('test_schema_field', names)

        self.schema.delete_field('test_schema_field')
        fields = self.schema.fields()
        names = [f['name'] for f in fields]
        self.assertNotIn('test_schema_field', names)

    def test_replace_field(self):
        self.schema.add_field('test_schema_field', 'string', stored=True)
        self.schema.replace_field('test_schema_field', 'text_general',
                                  stored=False)
        fields = self.schema.fields()
        field = [f for f in fields if f['name'] == 'test_schema_field'][0]
        self.assertEqual(field['type'], 'text_general')


class TestSchemaFieldTypes(unittest.TestCase):

    def setUp(self):
        self.conn = solr.Solr(SOLR_HTTP, response_format='xml')
        self.schema = SchemaAPI(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_list_field_types(self):
        types = self.schema.field_types()
        self.assertIsInstance(types, list)
        names = [t['name'] for t in types]
        self.assertIn('string', names)


class TestSchemaCopyFields(unittest.TestCase):

    def setUp(self):
        self.conn = solr.Solr(SOLR_HTTP, response_format='xml')
        self.schema = SchemaAPI(self.conn)
        try:
            self.schema.add_field('test_src', 'string', stored=True)
        except Exception:
            pass
        try:
            self.schema.add_field('test_dest', 'string', stored=True)
        except Exception:
            pass

    def tearDown(self):
        try:
            self.schema.delete_copy_field('test_src', 'test_dest')
        except Exception:
            pass
        try:
            self.schema.delete_field('test_src')
        except Exception:
            pass
        try:
            self.schema.delete_field('test_dest')
        except Exception:
            pass
        self.conn.close()

    def test_add_and_list_copy_field(self):
        self.schema.add_copy_field('test_src', 'test_dest')
        copies = self.schema.copy_fields()
        matches = [c for c in copies
                   if c['source'] == 'test_src' and c['dest'] == 'test_dest']
        self.assertGreater(len(matches), 0)

    def test_delete_copy_field(self):
        self.schema.add_copy_field('test_src', 'test_dest')
        self.schema.delete_copy_field('test_src', 'test_dest')
        copies = self.schema.copy_fields()
        matches = [c for c in copies
                   if c['source'] == 'test_src' and c['dest'] == 'test_dest']
        self.assertEqual(len(matches), 0)


class TestSchemaFullDump(unittest.TestCase):

    def setUp(self):
        self.conn = solr.Solr(SOLR_HTTP, response_format='xml')
        self.schema = SchemaAPI(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_get_schema(self):
        schema = self.schema.get_schema()
        self.assertIsInstance(schema, dict)
        self.assertIn('name', schema)


class TestSchemaVersionGuard(unittest.TestCase):

    def test_schema_on_old_version(self):
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = (3, 6, 0)
        conn.path = '/solr'
        conn.auth_headers = {}
        conn.persistent = True
        schema = SchemaAPI(conn)
        with self.assertRaises(solr.core.SolrVersionError):
            schema.fields()


if __name__ == "__main__":
    unittest.main()
