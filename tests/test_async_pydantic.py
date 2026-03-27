"""Tests for async Pydantic model support (2.0.6).

model= parameter should work with:
- await conn.select('*:*', model=MyDoc)
- await conn.get(id='1', model=MyDoc)  (already works)
- async for doc in await conn.stream(expr, model=MyDoc)  (already works)
"""

import asyncio
import unittest

try:
    from pydantic import BaseModel
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

import solr
from tests.conftest import SOLR_HTTP


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@unittest.skipUnless(HAS_PYDANTIC, "pydantic not installed")
class TestAsyncSelectModel(unittest.TestCase):
    """await conn.select('*:*', model=MyDoc) returns typed results."""

    def test_select_with_model(self):
        class Doc(BaseModel):
            id: str
            data: str | None = None

        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                await conn.add({'id': 'apyd_1', 'data': 'hello'}, commit=True)

                resp = await conn.select('id:apyd_1', model=Doc)
                self.assertIsNotNone(resp)
                self.assertIsInstance(resp.results[0], Doc)
                self.assertEqual(resp.results[0].id, 'apyd_1')
                self.assertEqual(resp.results[0].data, 'hello')

                await conn.delete(id='apyd_1', commit=True)

        run(_test())

    def test_select_without_model(self):
        """Without model=, results are plain dicts (backward compat)."""
        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                await conn.add({'id': 'apyd_2', 'data': 'world'}, commit=True)

                resp = await conn.select('id:apyd_2')
                self.assertIsNotNone(resp)
                self.assertIsInstance(resp.results[0], dict)

                await conn.delete(id='apyd_2', commit=True)

        run(_test())


@unittest.skipUnless(HAS_PYDANTIC, "pydantic not installed")
class TestAsyncGetModel(unittest.TestCase):
    """await conn.get(id='1', model=MyDoc) — already implemented, verify."""

    def test_get_single_with_model(self):
        class Doc(BaseModel):
            id: str
            data: str | None = None

        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                await conn.add({'id': 'apyd_g1', 'data': 'get_test'}, commit=True)

                doc = await conn.get(id='apyd_g1', model=Doc)
                self.assertIsInstance(doc, Doc)
                self.assertEqual(doc.id, 'apyd_g1')

                await conn.delete(id='apyd_g1', commit=True)

        run(_test())

    def test_get_ids_with_model(self):
        class Doc(BaseModel):
            id: str
            data: str | None = None

        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                await conn.add({'id': 'apyd_g2', 'data': 'a'}, commit=True)
                await conn.add({'id': 'apyd_g3', 'data': 'b'}, commit=True)

                docs = await conn.get(ids=['apyd_g2', 'apyd_g3'], model=Doc)
                self.assertIsInstance(docs, list)
                for d in docs:
                    self.assertIsInstance(d, Doc)

                await conn.delete(id='apyd_g2', commit=True)
                await conn.delete(id='apyd_g3', commit=True)

        run(_test())


@unittest.skipUnless(HAS_PYDANTIC, "pydantic not installed")
class TestAsyncStreamModel(unittest.TestCase):
    """async for doc in await conn.stream(expr, model=MyDoc) — verify."""

    def test_stream_with_model(self):
        class Doc(BaseModel):
            id: str

        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                if conn.server_version < (5, 0):
                    self.skipTest("Solr < 5.0")
                from solr.stream import search
                await conn.add({'id': 'apyd_s1', 'data': 'stream'}, commit=True)

                expr = search('core0', q='id:apyd_s1', fl='id',
                              sort='id asc', qt='/select')
                async for doc in await conn.stream(expr, model=Doc):
                    self.assertIsInstance(doc, Doc)

                await conn.delete(id='apyd_s1', commit=True)

        run(_test())


if __name__ == "__main__":
    unittest.main()
