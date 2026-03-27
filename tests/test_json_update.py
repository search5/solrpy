"""Tests for internal JSON update path (Solr 4.0+).

When server_version >= (4, 0), add/add_many/atomic_update should
use JSON internally instead of XML. No user-facing parameter change.
"""

import datetime
import unittest
import solr
from solr.utils import UTC
from tests.conftest import SOLR_HTTP


class TestJsonUpdateAdd(unittest.TestCase):
    """add() uses JSON internally on Solr 4.0+."""

    def setUp(self):
        self.conn = solr.Solr(SOLR_HTTP)

    def tearDown(self):
        self.conn.close()

    def test_add_basic(self):
        self.conn.add({'id': 'ju_1', 'data': 'hello'}, commit=True)
        resp = self.conn.select('id:ju_1')
        self.assertEqual(resp.numFound, 1)
        self.assertEqual(resp.results[0]['data'], 'hello')
        self.conn.delete(id='ju_1', commit=True)

    def test_add_multivalue(self):
        self.conn.add({'id': 'ju_2', 'data': 'mv_test',
                       'cat': ['a', 'b', 'c']}, commit=True)
        resp = self.conn.select('id:ju_2')
        self.assertEqual(resp.numFound, 1)
        self.conn.delete(id='ju_2', commit=True)

    def test_add_datetime(self):
        dt = datetime.datetime(2024, 3, 27, 12, 0, 0, tzinfo=UTC())
        self.conn.add({'id': 'ju_3', 'data': 'dt_test'}, commit=True)
        resp = self.conn.select('id:ju_3')
        self.assertEqual(resp.numFound, 1)
        self.conn.delete(id='ju_3', commit=True)

    def test_add_bool(self):
        self.conn.add({'id': 'ju_4', 'data': 'bool_test'}, commit=True)
        resp = self.conn.select('id:ju_4')
        self.assertEqual(resp.numFound, 1)
        self.conn.delete(id='ju_4', commit=True)

    def test_add_none_field_omitted(self):
        self.conn.add({'id': 'ju_5', 'data': 'x', 'user_id': None},
                      commit=True)
        resp = self.conn.select('id:ju_5')
        self.assertEqual(resp.numFound, 1)
        self.conn.delete(id='ju_5', commit=True)

    def test_add_many(self):
        docs = [
            {'id': 'ju_6', 'data': 'one'},
            {'id': 'ju_7', 'data': 'two'},
        ]
        self.conn.add_many(docs, commit=True)
        resp = self.conn.select('id:ju_6 OR id:ju_7')
        self.assertEqual(resp.numFound, 2)
        self.conn.delete(id='ju_6', commit=True)
        self.conn.delete(id='ju_7', commit=True)


class TestJsonUpdateAtomic(unittest.TestCase):
    """atomic_update() uses JSON internally on Solr 4.0+."""

    def setUp(self):
        self.conn = solr.Solr(SOLR_HTTP)
        self.conn.add({'id': 'ju_at_1', 'data': 'original'}, commit=True)

    def tearDown(self):
        self.conn.delete(id='ju_at_1', commit=True)
        self.conn.close()

    def test_atomic_set(self):
        self.conn.atomic_update(
            {'id': 'ju_at_1', 'data': {'set': 'updated'}}, commit=True)
        resp = self.conn.select('id:ju_at_1')
        self.assertEqual(resp.results[0]['data'], 'updated')

    def test_atomic_null(self):
        self.conn.atomic_update(
            {'id': 'ju_at_1', 'data': {'set': None}}, commit=True)
        resp = self.conn.select('id:ju_at_1')
        self.assertNotIn('data', resp.results[0])


class TestJsonUpdateUsesJson(unittest.TestCase):
    """Verify that JSON Content-Type is actually sent on Solr 4.0+."""

    def test_post_uses_json_content_type(self):
        conn = solr.Solr(SOLR_HTTP)
        if conn.server_version < (4, 0):
            conn.close()
            self.skipTest("Solr < 4.0")

        last_headers = {}
        original_post = conn._post

        def capture_post(url, body, headers, **kwargs):
            last_headers.update(headers)
            return original_post(url, body, headers, **kwargs)

        conn._post = capture_post  # type: ignore
        conn.add({'id': 'ju_ct_1', 'data': 'test'}, commit=True)
        self.assertIn('application/json', last_headers.get('Content-Type', ''))
        conn.delete(id='ju_ct_1', commit=True)
        conn.close()


class TestAsyncJsonUpdate(unittest.TestCase):
    """AsyncSolr also uses JSON update path on Solr 4.0+."""

    def test_async_add(self):
        import asyncio

        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                await conn.add({'id': 'aju_1', 'data': 'async_json'},
                               commit=True)
                resp = await conn.select('id:aju_1')
                self.assertEqual(resp.numFound, 1)
                await conn.delete(id='aju_1', commit=True)

        asyncio.get_event_loop().run_until_complete(_test())

    def test_async_add_many(self):
        import asyncio

        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                await conn.add_many([
                    {'id': 'aju_2', 'data': 'a'},
                    {'id': 'aju_3', 'data': 'b'},
                ], commit=True)
                resp = await conn.select('id:aju_2 OR id:aju_3')
                self.assertEqual(resp.numFound, 2)
                await conn.delete(id='aju_2', commit=True)
                await conn.delete(id='aju_3', commit=True)

        asyncio.get_event_loop().run_until_complete(_test())


if __name__ == "__main__":
    unittest.main()
