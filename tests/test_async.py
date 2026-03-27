"""Tests for AsyncSolr and AsyncTransport (2.0.2)."""

import asyncio
import unittest
import solr
from tests.conftest import SOLR_HTTP


def run(coro):
    """Helper to run async tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


class TestAsyncSolrImport(unittest.TestCase):

    def test_import(self):
        from solr import AsyncSolr
        self.assertTrue(callable(AsyncSolr))


class TestAsyncSolrContextManager(unittest.TestCase):

    def test_async_with(self):
        from solr import AsyncSolr

        async def _test():
            async with AsyncSolr(SOLR_HTTP) as conn:
                self.assertIsNotNone(conn)
                self.assertTrue(conn.ping())

        run(_test())


class TestAsyncSolrBasicOps(unittest.TestCase):

    def test_select(self):
        from solr import AsyncSolr

        async def _test():
            async with AsyncSolr(SOLR_HTTP) as conn:
                resp = await conn.select('*:*')
                self.assertIsNotNone(resp)

        run(_test())

    def test_add_and_delete(self):
        from solr import AsyncSolr

        async def _test():
            async with AsyncSolr(SOLR_HTTP) as conn:
                await conn.add({'id': 'async_test_1', 'data': 'hello'}, commit=True)
                resp = await conn.select('id:async_test_1')
                self.assertEqual(resp.numFound, 1)
                await conn.delete(id='async_test_1', commit=True)

        run(_test())

    def test_add_many(self):
        from solr import AsyncSolr

        async def _test():
            async with AsyncSolr(SOLR_HTTP) as conn:
                docs = [{'id': 'async_m_%d' % i, 'data': 'test'} for i in range(3)]
                await conn.add_many(docs, commit=True)
                resp = await conn.select('id:async_m_*')
                self.assertEqual(resp.numFound, 3)
                await conn.delete_query('id:async_m_*', commit=True)

        run(_test())

    def test_ping(self):
        from solr import AsyncSolr

        async def _test():
            async with AsyncSolr(SOLR_HTTP) as conn:
                self.assertTrue(conn.ping())

        run(_test())

    def test_server_version(self):
        from solr import AsyncSolr

        async def _test():
            async with AsyncSolr(SOLR_HTTP) as conn:
                self.assertIsInstance(conn.server_version, tuple)
                self.assertGreaterEqual(conn.server_version[0], 6)

        run(_test())

    def test_commit(self):
        from solr import AsyncSolr

        async def _test():
            async with AsyncSolr(SOLR_HTTP) as conn:
                await conn.commit()

        run(_test())

    def test_get(self):
        from solr import AsyncSolr

        async def _test():
            async with AsyncSolr(SOLR_HTTP) as conn:
                await conn.add({'id': 'async_get_1', 'data': 'x'}, commit=True)
                doc = await conn.get(id='async_get_1')
                self.assertIsNotNone(doc)
                self.assertEqual(doc['id'], 'async_get_1')
                await conn.delete(id='async_get_1', commit=True)

        run(_test())


class TestAsyncTransport(unittest.TestCase):

    def test_import(self):
        from solr.transport import AsyncTransport
        self.assertTrue(callable(AsyncTransport))

    def test_get_json(self):
        from solr import AsyncSolr
        from solr.transport import AsyncTransport

        async def _test():
            async with AsyncSolr(SOLR_HTTP) as conn:
                transport = AsyncTransport(conn)
                data = await transport.get_json('/admin/ping')
                self.assertEqual(data.get('status'), 'OK')

        run(_test())

    def test_post_json(self):
        from solr import AsyncSolr
        from solr.transport import AsyncTransport

        async def _test():
            async with AsyncSolr(SOLR_HTTP) as conn:
                transport = AsyncTransport(conn)
                result = await transport.post_json('/update', {'commit': {}})
                self.assertIn('responseHeader', result)

        run(_test())


if __name__ == "__main__":
    unittest.main()
