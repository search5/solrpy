"""Tests for Schema API client (Solr 4.2+)."""

import unittest
import solr
import solr.core
from tests.conftest import SOLR_HTTP


class TestSchemaAPI(unittest.TestCase):

    def setUp(self):
        self.conn = solr.Solr(SOLR_HTTP, response_format='xml')

    def tearDown(self):
        self.conn.close()

    def test_schema_accessor_exists(self):
        self.assertTrue(hasattr(self.conn, 'schema'))

    def test_schema_is_separate_class(self):
        from solr.schema import SchemaAPI
        self.assertIsInstance(self.conn.schema, SchemaAPI)


class TestSchemaFields(unittest.TestCase):

    def setUp(self):
        self.conn = solr.Solr(SOLR_HTTP, response_format='xml')

    def tearDown(self):
        # Clean up test fields
        try:
            self.conn.schema.delete_field('test_schema_field')
        except Exception:
            pass
        self.conn.close()

    def test_list_fields(self):
        fields = self.conn.schema.fields()
        self.assertIsInstance(fields, list)
        names = [f['name'] for f in fields]
        self.assertIn('id', names)

    def test_add_and_delete_field(self):
        self.conn.schema.add_field('test_schema_field', 'string',
                                   stored=True, indexed=True)
        fields = self.conn.schema.fields()
        names = [f['name'] for f in fields]
        self.assertIn('test_schema_field', names)

        self.conn.schema.delete_field('test_schema_field')
        fields = self.conn.schema.fields()
        names = [f['name'] for f in fields]
        self.assertNotIn('test_schema_field', names)

    def test_replace_field(self):
        self.conn.schema.add_field('test_schema_field', 'string', stored=True)
        self.conn.schema.replace_field('test_schema_field', 'text_general',
                                       stored=False)
        fields = self.conn.schema.fields()
        field = [f for f in fields if f['name'] == 'test_schema_field'][0]
        self.assertEqual(field['type'], 'text_general')


class TestSchemaFieldTypes(unittest.TestCase):

    def setUp(self):
        self.conn = solr.Solr(SOLR_HTTP, response_format='xml')

    def tearDown(self):
        self.conn.close()

    def test_list_field_types(self):
        types = self.conn.schema.field_types()
        self.assertIsInstance(types, list)
        names = [t['name'] for t in types]
        self.assertIn('string', names)


class TestSchemaCopyFields(unittest.TestCase):

    def setUp(self):
        self.conn = solr.Solr(SOLR_HTTP, response_format='xml')
        try:
            self.conn.schema.add_field('test_src', 'string', stored=True)
        except Exception:
            pass
        try:
            self.conn.schema.add_field('test_dest', 'string', stored=True)
        except Exception:
            pass

    def tearDown(self):
        try:
            self.conn.schema.delete_copy_field('test_src', 'test_dest')
        except Exception:
            pass
        try:
            self.conn.schema.delete_field('test_src')
        except Exception:
            pass
        try:
            self.conn.schema.delete_field('test_dest')
        except Exception:
            pass
        self.conn.close()

    def test_add_and_list_copy_field(self):
        self.conn.schema.add_copy_field('test_src', 'test_dest')
        copies = self.conn.schema.copy_fields()
        matches = [c for c in copies
                   if c['source'] == 'test_src' and c['dest'] == 'test_dest']
        self.assertGreater(len(matches), 0)

    def test_delete_copy_field(self):
        self.conn.schema.add_copy_field('test_src', 'test_dest')
        self.conn.schema.delete_copy_field('test_src', 'test_dest')
        copies = self.conn.schema.copy_fields()
        matches = [c for c in copies
                   if c['source'] == 'test_src' and c['dest'] == 'test_dest']
        self.assertEqual(len(matches), 0)


class TestSchemaFullDump(unittest.TestCase):

    def setUp(self):
        self.conn = solr.Solr(SOLR_HTTP, response_format='xml')

    def tearDown(self):
        self.conn.close()

    def test_get_schema(self):
        schema = self.conn.schema.get_schema()
        self.assertIsInstance(schema, dict)
        self.assertIn('name', schema)


class TestSchemaVersionGuard(unittest.TestCase):

    def test_schema_on_old_version(self):
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = (3, 6, 0)
        conn.path = '/solr'
        conn.auth_headers = {}
        conn.persistent = True
        from solr.schema import SchemaAPI
        schema = SchemaAPI(conn)
        with self.assertRaises(solr.core.SolrVersionError):
            schema.fields()


if __name__ == "__main__":
    unittest.main()
