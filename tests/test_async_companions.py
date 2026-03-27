"""Tests for async companion classes (2.0.3)."""

import asyncio
import unittest
import solr
from tests.conftest import SOLR_HTTP


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestAsyncSchemaAPI(unittest.TestCase):

    def test_import(self):
        from solr import AsyncSchemaAPI
        self.assertTrue(callable(AsyncSchemaAPI))

    def test_list_fields(self):
        from solr import AsyncSolr, AsyncSchemaAPI

        async def _test():
            async with AsyncSolr(SOLR_HTTP) as conn:
                schema = AsyncSchemaAPI(conn)
                fields = await schema.fields()
                self.assertIsInstance(fields, list)
                names = [f['name'] for f in fields]
                self.assertIn('id', names)

        run(_test())


class TestAsyncKNN(unittest.TestCase):

    def test_import(self):
        from solr import AsyncKNN
        self.assertTrue(callable(AsyncKNN))

    def test_build_query_sync(self):
        """build_query methods are sync (no await needed)."""
        from solr import AsyncSolr, AsyncKNN

        async def _test():
            async with AsyncSolr(SOLR_HTTP) as conn:
                knn = AsyncKNN(conn)
                q = knn.build_knn_query([0.1, 0.2, 0.3], field='vec', top_k=5)
                self.assertIn('{!knn', q)

        run(_test())


class TestAsyncMLT(unittest.TestCase):

    def test_import(self):
        from solr import AsyncMoreLikeThis
        self.assertTrue(callable(AsyncMoreLikeThis))


class TestAsyncSuggest(unittest.TestCase):

    def test_import(self):
        from solr import AsyncSuggest
        self.assertTrue(callable(AsyncSuggest))


class TestAsyncExtract(unittest.TestCase):

    def test_import(self):
        from solr import AsyncExtract
        self.assertTrue(callable(AsyncExtract))


if __name__ == "__main__":
    unittest.main()
