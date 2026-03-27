"""Tests for lazy version detection in Solr and AsyncSolr."""

import unittest
from unittest.mock import patch, MagicMock

import solr
import solr.core
from solr.async_solr import AsyncSolr


class TestSolrLazyVersionDetection(unittest.TestCase):
    """Verify that Solr.__init__ does NOT call _detect_version()."""

    @patch.object(solr.core.Solr, '_detect_version')
    def test_init_does_not_call_detect_version(self, mock_detect):
        """Construction must not trigger version detection."""
        mock_detect.return_value = (9, 0, 0)
        conn = solr.Solr.__new__(solr.Solr)
        # Manually run __init__ internals without hitting a real server
        # by patching _detect_version before __init__
        conn = solr.Solr('http://localhost:8983/solr/core0')
        mock_detect.assert_not_called()
        conn.close()

    @patch.object(solr.core.Solr, '_detect_version', return_value=(9, 4, 1))
    def test_version_detected_on_first_access(self, mock_detect):
        """First access to server_version must trigger _detect_version."""
        conn = solr.Solr('http://localhost:8983/solr/core0')
        mock_detect.assert_not_called()
        ver = conn.server_version
        mock_detect.assert_called_once()
        self.assertEqual(ver, (9, 4, 1))
        conn.close()

    @patch.object(solr.core.Solr, '_detect_version', return_value=(8, 0, 0))
    def test_version_cached_after_first_access(self, mock_detect):
        """Subsequent accesses must NOT call _detect_version again."""
        conn = solr.Solr('http://localhost:8983/solr/core0')
        _ = conn.server_version
        _ = conn.server_version
        _ = conn.server_version
        mock_detect.assert_called_once()
        conn.close()

    def test_setter_works(self):
        """Direct assignment conn.server_version = (...) must work."""
        conn = solr.Solr.__new__(solr.Solr)
        conn._server_version = None
        conn.server_version = (9, 0, 0)
        self.assertEqual(conn.server_version, (9, 0, 0))

    @patch.object(solr.core.Solr, '_detect_version', return_value=(7, 7, 0))
    def test_setter_bypasses_detection(self, mock_detect):
        """Setting server_version explicitly must skip auto-detection."""
        conn = solr.Solr('http://localhost:8983/solr/core0')
        conn.server_version = (10, 0, 0)
        ver = conn.server_version
        mock_detect.assert_not_called()
        self.assertEqual(ver, (10, 0, 0))
        conn.close()

    @patch.object(solr.core.Solr, '_detect_version', return_value=(9, 0, 0))
    def test_internal_attribute_is_none_initially(self, mock_detect):
        """_server_version must be None right after construction."""
        conn = solr.Solr('http://localhost:8983/solr/core0')
        self.assertIsNone(conn._server_version)
        conn.close()


class TestAsyncSolrLazyVersionDetection(unittest.TestCase):
    """Verify that AsyncSolr.__init__ does NOT call _detect_version_sync()."""

    @patch.object(AsyncSolr, '_detect_version_sync')
    def test_init_does_not_call_detect_version_sync(self, mock_detect):
        """Construction must not trigger version detection."""
        mock_detect.return_value = (9, 0, 0)
        conn = AsyncSolr('http://localhost:8983/solr/core0')
        mock_detect.assert_not_called()

    @patch.object(AsyncSolr, '_detect_version_sync', return_value=(9, 4, 1))
    def test_version_detected_on_first_access(self, mock_detect):
        """First access to server_version must trigger _detect_version_sync."""
        conn = AsyncSolr('http://localhost:8983/solr/core0')
        mock_detect.assert_not_called()
        ver = conn.server_version
        mock_detect.assert_called_once()
        self.assertEqual(ver, (9, 4, 1))

    @patch.object(AsyncSolr, '_detect_version_sync', return_value=(8, 0, 0))
    def test_version_cached_after_first_access(self, mock_detect):
        """Subsequent accesses must NOT call _detect_version_sync again."""
        conn = AsyncSolr('http://localhost:8983/solr/core0')
        _ = conn.server_version
        _ = conn.server_version
        _ = conn.server_version
        mock_detect.assert_called_once()

    def test_setter_works(self):
        """Direct assignment conn.server_version = (...) must work."""
        conn = AsyncSolr.__new__(AsyncSolr)
        conn._server_version = None
        conn.server_version = (9, 0, 0)
        self.assertEqual(conn.server_version, (9, 0, 0))

    @patch.object(AsyncSolr, '_detect_version_sync', return_value=(7, 7, 0))
    def test_setter_bypasses_detection(self, mock_detect):
        """Setting server_version explicitly must skip auto-detection."""
        conn = AsyncSolr('http://localhost:8983/solr/core0')
        conn.server_version = (10, 0, 0)
        ver = conn.server_version
        mock_detect.assert_not_called()
        self.assertEqual(ver, (10, 0, 0))

    @patch.object(AsyncSolr, '_detect_version_sync', return_value=(9, 0, 0))
    def test_internal_attribute_is_none_initially(self, mock_detect):
        """_server_version must be None right after construction."""
        conn = AsyncSolr('http://localhost:8983/solr/core0')
        self.assertIsNone(conn._server_version)


if __name__ == '__main__':
    unittest.main()
