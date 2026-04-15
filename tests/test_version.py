"""Auto-split from test_all.py"""

import unittest
import solr
import solr.core
from tests.conftest import SOLR_HTTP


class TestDeprecatedAttributesRemoved(unittest.TestCase):
    """encoder/decoder attributes should no longer exist."""

    def test_no_encoder_attribute(self):
        conn = solr.Solr(SOLR_HTTP)
        self.assertFalse(hasattr(conn, 'encoder'))
        conn.close()

    def test_no_decoder_attribute(self):
        conn = solr.Solr(SOLR_HTTP)
        self.assertFalse(hasattr(conn, 'decoder'))
        conn.close()



class TestSolrVersionError(unittest.TestCase):

    def test_str(self):
        err = solr.core.SolrVersionError("atomic_update", (4, 0), (3, 6, 2))
        self.assertIn("atomic_update", str(err))
        self.assertIn("4.0", str(err))
        self.assertIn("3.6.2", str(err))

    def test_attributes(self):
        err = solr.core.SolrVersionError("knn_search", (9, 0), (6, 6, 0))
        self.assertEqual(err.feature, "knn_search")
        self.assertEqual(err.required, (9, 0))
        self.assertEqual(err.actual, (6, 6, 0))

    def test_is_exception(self):
        err = solr.core.SolrVersionError("x", (1,), (0,))
        self.assertIsInstance(err, Exception)



class TestRequiresVersionDecorator(unittest.TestCase):

    def _make_conn(self, version):
        """Return a minimal Solr-like object with the given server_version."""
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = version
        return conn

    def test_passes_when_version_met(self):
        conn = self._make_conn((6, 6, 0))

        @solr.core.requires_version(6, 0)
        def feature(self):
            return "ok"

        self.assertEqual(feature(conn), "ok")

    def test_raises_when_version_not_met(self):
        conn = self._make_conn((3, 6, 0))

        @solr.core.requires_version(4, 0)
        def atomic_update(self):
            return "ok"

        with self.assertRaises(solr.core.SolrVersionError) as ctx:
            atomic_update(conn)
        self.assertEqual(ctx.exception.feature, "atomic_update")
        self.assertEqual(ctx.exception.required, (4, 0))
        self.assertEqual(ctx.exception.actual, (3, 6, 0))

    def test_exact_version_boundary(self):
        conn = self._make_conn((4, 0, 0))

        @solr.core.requires_version(4, 0)
        def feature(self):
            return "ok"

        self.assertEqual(feature(conn), "ok")



class TestVersionDetection(unittest.TestCase):
    """Tests for _detect_version() using mocked HTTP responses."""

    def _make_conn(self, json_body=None, xml_body=None, fail_json=False, fail_xml=False):
        """
        Return a Solr instance with _get mocked.
        json_body / xml_body: string returned for that wt.
        fail_*: simulate an exception for that path.
        """
        conn = solr.Solr.__new__(solr.Solr)
        conn.path = '/solr'

        json_response = json_body
        xml_response  = xml_body

        def mock_get(path):
            if 'wt=json' in path:
                if fail_json:
                    raise Exception("json fail")
                class R:
                    @property
                    def text(self):
                        return json_response
                return R()
            else:
                if fail_xml:
                    raise Exception("xml fail")
                class R:
                    @property
                    def text(self):
                        return xml_response
                return R()

        conn._get = mock_get
        return conn

    def test_detects_version_from_json(self):
        body = '{"lucene": {"solr-spec-version": "9.4.1"}}'
        conn = self._make_conn(json_body=body)
        self.assertEqual(conn._detect_version(), (9, 4, 1))

    def test_detects_version_from_json_two_part(self):
        body = '{"lucene": {"solr-spec-version": "6.6"}}'
        conn = self._make_conn(json_body=body)
        self.assertEqual(conn._detect_version(), (6, 6))

    def test_falls_back_to_xml(self):
        xml = '<response><str name="solr-spec-version">3.6.2</str></response>'
        conn = self._make_conn(fail_json=True, xml_body=xml)
        self.assertEqual(conn._detect_version(), (3, 6, 2))

    def test_falls_back_to_default_on_total_failure(self):
        conn = self._make_conn(fail_json=True, fail_xml=True)
        self.assertEqual(conn._detect_version(), (1, 2, 0))

    def test_detects_version_against_live_solr(self):
        conn = solr.Solr(SOLR_HTTP)
        version = conn.server_version
        self.assertIsInstance(version, tuple)
        self.assertGreaterEqual(len(version), 2)
        self.assertGreaterEqual(version[0], 6)
        conn.close()


# ===================================================================
# 0.9.11 tests
# ===================================================================


class TestSolrConnectionRemoved(unittest.TestCase):
    """Verify SolrConnection is no longer available."""

    def test_no_solr_connection_class(self):
        self.assertFalse(hasattr(solr, 'SolrConnection'))

    def test_no_solr_connection_in_core(self):
        self.assertFalse(hasattr(solr.core, 'SolrConnection'))


# ===================================================================
# 1.0.3 tests — response_format
# ===================================================================


class TestSolrVersionOverride(unittest.TestCase):

    def test_version_override_skips_autodetect(self):
        conn = solr.Solr(SOLR_HTTP, solr_version=(9, 4, 1))
        self.assertEqual(conn.server_version, (9, 4, 1))
        conn.close()

    def test_async_version_override(self):
        from solr.async_solr import AsyncSolr
        conn = AsyncSolr(SOLR_HTTP, solr_version=(9, 4, 1))
        self.assertEqual(conn.server_version, (9, 4, 1))


