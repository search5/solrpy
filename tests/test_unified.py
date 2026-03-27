"""Tests for unified sync/async companion API (2.0.4).

Each companion class (SchemaAPI, KNN, Suggest, Extract, MoreLikeThis)
should accept both Solr and AsyncSolr, returning values or coroutines
as appropriate.
"""

import asyncio
import inspect
import unittest
import solr
from tests.conftest import SOLR_HTTP


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# -----------------------------------------------------------------------
# Detection tests — verify that companion classes accept both conn types
# -----------------------------------------------------------------------

class TestDualTransportDetection(unittest.TestCase):
    """DualTransport correctly detects sync vs async connections."""

    def test_sync_transport(self):
        from solr.transport import DualTransport
        conn = solr.Solr(SOLR_HTTP)
        dt = DualTransport(conn)
        self.assertFalse(dt.is_async)
        self.assertIsInstance(dt.server_version, tuple)
        conn.close()

    def test_async_transport(self):
        from solr.transport import DualTransport

        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                dt = DualTransport(conn)
                self.assertTrue(dt.is_async)
                self.assertIsInstance(dt.server_version, tuple)

        run(_test())

    def test_sync_get_json_returns_dict(self):
        from solr.transport import DualTransport
        conn = solr.Solr(SOLR_HTTP)
        dt = DualTransport(conn)
        result = dt.get_json('/schema/fields')
        self.assertIsInstance(result, dict)
        conn.close()

    def test_async_get_json_returns_coroutine(self):
        from solr.transport import DualTransport

        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                dt = DualTransport(conn)
                result = dt.get_json('/schema/fields')
                self.assertTrue(inspect.isawaitable(result))
                data = await result
                self.assertIsInstance(data, dict)

        run(_test())


# -----------------------------------------------------------------------
# SchemaAPI — unified mode
# -----------------------------------------------------------------------

class TestSchemaAPIUnified(unittest.TestCase):
    """SchemaAPI works with both Solr and AsyncSolr."""

    def test_sync_fields(self):
        conn = solr.Solr(SOLR_HTTP)
        schema = solr.SchemaAPI(conn)
        fields = schema.fields()
        self.assertIsInstance(fields, list)
        names = [f['name'] for f in fields]
        self.assertIn('id', names)
        conn.close()

    def test_async_fields(self):
        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                schema = solr.SchemaAPI(conn)
                result = schema.fields()
                self.assertTrue(inspect.isawaitable(result))
                fields = await result
                self.assertIsInstance(fields, list)
                names = [f['name'] for f in fields]
                self.assertIn('id', names)

        run(_test())

    def test_sync_get_schema(self):
        conn = solr.Solr(SOLR_HTTP)
        schema = solr.SchemaAPI(conn)
        data = schema.get_schema()
        self.assertIsInstance(data, dict)
        self.assertIn('name', data)
        conn.close()

    def test_async_get_schema(self):
        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                schema = solr.SchemaAPI(conn)
                data = await schema.get_schema()
                self.assertIsInstance(data, dict)
                self.assertIn('name', data)

        run(_test())

    def test_sync_field_types(self):
        conn = solr.Solr(SOLR_HTTP)
        schema = solr.SchemaAPI(conn)
        types = schema.field_types()
        self.assertIsInstance(types, list)
        self.assertTrue(len(types) > 0)
        conn.close()

    def test_async_field_types(self):
        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                schema = solr.SchemaAPI(conn)
                types = await schema.field_types()
                self.assertIsInstance(types, list)
                self.assertTrue(len(types) > 0)

        run(_test())


# -----------------------------------------------------------------------
# KNN — unified mode
# -----------------------------------------------------------------------

class TestKNNUnified(unittest.TestCase):
    """KNN works with both Solr and AsyncSolr."""

    def test_sync_build_query(self):
        conn = solr.Solr(SOLR_HTTP)
        knn = solr.KNN(conn)
        q = knn.build_knn_query([0.1, 0.2, 0.3], field='vec', top_k=5)
        self.assertIn('{!knn', q)
        conn.close()

    def test_async_build_query(self):
        """Build methods are pure (sync) even with AsyncSolr."""
        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                knn = solr.KNN(conn)
                q = knn.build_knn_query([0.1, 0.2, 0.3], field='vec', top_k=5)
                self.assertIn('{!knn', q)

        run(_test())

    def test_async_accepts_async_conn(self):
        """KNN accepts AsyncSolr without error."""
        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                knn = solr.KNN(conn)
                self.assertTrue(knn._is_async)

        run(_test())

    def test_sync_is_not_async(self):
        conn = solr.Solr(SOLR_HTTP)
        knn = solr.KNN(conn)
        self.assertFalse(knn._is_async)
        conn.close()


# -----------------------------------------------------------------------
# MoreLikeThis — unified mode
# -----------------------------------------------------------------------

class TestMoreLikeThisUnified(unittest.TestCase):
    """MoreLikeThis works with both Solr and AsyncSolr."""

    def test_sync_accepts_sync_conn(self):
        conn = solr.Solr(SOLR_HTTP)
        mlt = solr.MoreLikeThis(conn)
        self.assertFalse(mlt._is_async)
        conn.close()

    def test_async_accepts_async_conn(self):
        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                mlt = solr.MoreLikeThis(conn)
                self.assertTrue(mlt._is_async)

        run(_test())


# -----------------------------------------------------------------------
# Suggest — unified mode
# -----------------------------------------------------------------------

class TestSuggestUnified(unittest.TestCase):
    """Suggest works with both Solr and AsyncSolr."""

    def test_sync_accepts_sync_conn(self):
        conn = solr.Solr(SOLR_HTTP)
        suggest = solr.Suggest(conn)
        self.assertFalse(suggest._is_async)
        conn.close()

    def test_async_accepts_async_conn(self):
        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                suggest = solr.Suggest(conn)
                self.assertTrue(suggest._is_async)

        run(_test())


# -----------------------------------------------------------------------
# Extract — unified mode
# -----------------------------------------------------------------------

class TestExtractUnified(unittest.TestCase):
    """Extract works with both Solr and AsyncSolr."""

    def test_sync_accepts_sync_conn(self):
        conn = solr.Solr(SOLR_HTTP)
        extract = solr.Extract(conn)
        self.assertFalse(extract._is_async)
        conn.close()

    def test_async_accepts_async_conn(self):
        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                extract = solr.Extract(conn)
                self.assertTrue(extract._is_async)

        run(_test())


# -----------------------------------------------------------------------
# Backward compatibility — AsyncXxx aliases still work
# -----------------------------------------------------------------------

class TestBackwardCompat(unittest.TestCase):
    """AsyncSchemaAPI etc. still importable and usable."""

    def test_async_schema_api_alias(self):
        from solr import AsyncSchemaAPI

        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                schema = AsyncSchemaAPI(conn)
                fields = await schema.fields()
                self.assertIsInstance(fields, list)

        run(_test())

    def test_async_knn_alias(self):
        from solr import AsyncKNN

        async def _test():
            async with solr.AsyncSolr(SOLR_HTTP) as conn:
                knn = AsyncKNN(conn)
                q = knn.build_knn_query([0.1, 0.2], field='v', top_k=3)
                self.assertIn('{!knn', q)

        run(_test())

    def test_async_mlt_alias(self):
        from solr import AsyncMoreLikeThis
        self.assertTrue(callable(AsyncMoreLikeThis))

    def test_async_suggest_alias(self):
        from solr import AsyncSuggest
        self.assertTrue(callable(AsyncSuggest))

    def test_async_extract_alias(self):
        from solr import AsyncExtract
        self.assertTrue(callable(AsyncExtract))


# -----------------------------------------------------------------------
# _chain helper tests
# -----------------------------------------------------------------------

class TestChainHelper(unittest.TestCase):
    """_chain applies transforms to sync values and async coroutines."""

    def test_sync_chain(self):
        from solr.transport import _chain
        result = _chain({'fields': [1, 2, 3]}, lambda d: d['fields'])
        self.assertEqual(result, [1, 2, 3])

    def test_async_chain(self):
        from solr.transport import _chain

        async def _coro():
            return {'fields': [4, 5, 6]}

        async def _test():
            chained = _chain(_coro(), lambda d: d['fields'])
            self.assertTrue(inspect.isawaitable(chained))
            result = await chained
            self.assertEqual(result, [4, 5, 6])

        run(_test())


if __name__ == "__main__":
    unittest.main()
