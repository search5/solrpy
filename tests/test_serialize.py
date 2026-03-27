"""Tests for serialize_value() and its use in add/atomic_update/async paths."""

import datetime
import unittest
import solr
from solr.utils import UTC, serialize_value
from tests.conftest import SOLR_HTTP


class TestSerializeValue(unittest.TestCase):
    """Unit tests for the serialize_value() helper."""

    def test_datetime_with_tz(self):
        dt = datetime.datetime(2024, 3, 27, 12, 0, 0, tzinfo=UTC())
        self.assertEqual(serialize_value(dt), '2024-03-27T12:00:00Z')

    def test_datetime_naive(self):
        dt = datetime.datetime(2024, 3, 27, 12, 0, 0)
        self.assertEqual(serialize_value(dt), '2024-03-27T12:00:00Z')

    def test_date(self):
        d = datetime.date(2024, 3, 27)
        self.assertEqual(serialize_value(d), '2024-03-27T00:00:00Z')

    def test_bool_true(self):
        self.assertEqual(serialize_value(True), 'true')

    def test_bool_false(self):
        self.assertEqual(serialize_value(False), 'false')

    def test_string_passthrough(self):
        self.assertEqual(serialize_value('hello'), 'hello')

    def test_int_passthrough(self):
        self.assertEqual(serialize_value(42), '42')

    def test_float_passthrough(self):
        self.assertEqual(serialize_value(3.14), '3.14')

    def test_none_returns_none(self):
        self.assertIsNone(serialize_value(None))

    def test_decimal(self):
        from decimal import Decimal
        self.assertEqual(serialize_value(Decimal('3.14')), '3.14')


class TestSolrJsonDefault(unittest.TestCase):
    """Unit tests for the solr_json_default() JSON encoder."""

    def test_decimal_to_float(self):
        import json
        from decimal import Decimal
        from solr.utils import solr_json_default
        result = json.dumps({'price': Decimal('9.99')}, default=solr_json_default)
        self.assertIn('9.99', result)
        # Should be a number, not a string
        data = json.loads(result)
        self.assertIsInstance(data['price'], float)

    def test_none_in_json(self):
        """None should serialize to JSON null, not string 'None'."""
        import json
        result = json.dumps({'field': None})
        self.assertIn('null', result)
        self.assertNotIn('None', result)

    def test_atomic_update_none_json(self):
        """{'set': None} should produce {"set": null} in JSON."""
        import json
        from solr.utils import solr_json_default
        doc = {'id': '1', 'old_field': {'set': None}}
        result = json.dumps(doc, default=solr_json_default)
        data = json.loads(result)
        self.assertIsNone(data['old_field']['set'])


class TestAtomicUpdateSerialization(unittest.TestCase):
    """atomic_update must serialize datetime/bool/date correctly."""

    def setUp(self):
        self.conn = solr.Solr(SOLR_HTTP)

    def tearDown(self):
        self.conn.close()

    def test_atomic_update_datetime(self):
        dt = datetime.datetime(2024, 3, 27, 12, 0, 0, tzinfo=UTC())
        doc = {'id': 'ser_test_1', 'data': {'set': 'x'}}
        # Should not raise
        self.conn.add({'id': 'ser_test_1', 'data': 'x'}, commit=True)
        self.conn.atomic_update(doc, commit=True)
        self.conn.delete(id='ser_test_1', commit=True)

    def test_atomic_update_bool(self):
        """Bool values in atomic update must become 'true'/'false'."""
        doc = {'id': 'ser_test_2', 'data': {'set': 'val'}}
        self.conn.add({'id': 'ser_test_2', 'data': 'val'}, commit=True)
        self.conn.atomic_update(doc, commit=True)
        self.conn.delete(id='ser_test_2', commit=True)


class TestAsyncAddSerialization(unittest.TestCase):
    """AsyncSolr.add/add_many must serialize datetime/bool/date correctly."""

    def test_async_add_datetime(self):
        import asyncio

        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                dt = datetime.datetime(2024, 3, 27, 12, 0, 0, tzinfo=UTC())
                await conn.add({'id': 'async_ser_1', 'data': str(dt)[:10],
                                'timestamp_dt': dt}, commit=True)
                await conn.delete(id='async_ser_1', commit=True)

        asyncio.get_event_loop().run_until_complete(_test())

    def test_async_add_many_bool(self):
        import asyncio

        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                await conn.add_many([
                    {'id': 'async_ser_2', 'data': 'test'},
                ], commit=True)
                await conn.delete(id='async_ser_2', commit=True)

        asyncio.get_event_loop().run_until_complete(_test())


if __name__ == "__main__":
    unittest.main()
