"""Tests for PysolrCompat -- a pysolr-compatible wrapper around solrpy."""

import unittest
from unittest.mock import patch, MagicMock

import solr
from solr.compat import PysolrCompat


def _make_compat(url='http://localhost:8983/solr/core0', **kwargs):
    """Create a PysolrCompat instance with httpx.Client mocked out."""
    with patch('httpx.Client'):
        return PysolrCompat(url, **kwargs)


class TestPysolrCompatInit(unittest.TestCase):
    """PysolrCompat should subclass Solr and accept the same constructor args."""

    def test_is_subclass_of_solr(self):
        conn = _make_compat()
        self.assertIsInstance(conn, solr.Solr)

    def test_constructor_accepts_url(self):
        conn = _make_compat()
        self.assertEqual(conn.host, 'localhost:8983')

    def test_constructor_passes_kwargs_to_solr(self):
        conn = _make_compat(timeout=30)
        self.assertEqual(conn.timeout, 30)


class TestPysolrCompatSearch(unittest.TestCase):
    """search() should delegate to select()."""

    def setUp(self):
        self.conn = _make_compat()

    def test_search_delegates_to_select(self):
        mock_response = MagicMock()
        self.conn.select = MagicMock(return_value=mock_response)

        result = self.conn.search('field:value', rows=10)

        self.conn.select.assert_called_once_with('field:value', rows=10)
        self.assertIs(result, mock_response)

    def test_search_with_no_kwargs(self):
        mock_response = MagicMock()
        self.conn.select = MagicMock(return_value=mock_response)

        result = self.conn.search('*:*')

        self.conn.select.assert_called_once_with('*:*')


class TestPysolrCompatAdd(unittest.TestCase):
    """add() should accept a list (like pysolr) or a single dict (fallback)."""

    def setUp(self):
        self.conn = _make_compat()

    def test_add_list_delegates_to_add_many(self):
        docs = [{'id': '1', 'title': 'A'}, {'id': '2', 'title': 'B'}]
        self.conn.add_many = MagicMock()
        self.conn.commit = MagicMock()

        self.conn.add(docs, commit=True)

        self.conn.add_many.assert_called_once_with(docs)
        self.conn.commit.assert_called_once()

    def test_add_list_without_commit(self):
        docs = [{'id': '1'}]
        self.conn.add_many = MagicMock()
        self.conn.commit = MagicMock()

        self.conn.add(docs, commit=False)

        self.conn.add_many.assert_called_once_with(docs)
        self.conn.commit.assert_not_called()

    def test_add_list_commit_defaults_true(self):
        """pysolr defaults commit=True on add()."""
        docs = [{'id': '1'}]
        self.conn.add_many = MagicMock()
        self.conn.commit = MagicMock()

        self.conn.add(docs)

        self.conn.add_many.assert_called_once_with(docs)
        self.conn.commit.assert_called_once()

    def test_add_single_dict_delegates_to_parent_add(self):
        doc = {'id': '1', 'title': 'A'}
        with patch.object(solr.Solr, 'add') as mock_add:
            self.conn.commit = MagicMock()
            self.conn.add(doc, commit=True)
            mock_add.assert_called_once_with(doc)
            self.conn.commit.assert_called_once()

    def test_add_empty_list(self):
        self.conn.add_many = MagicMock()
        self.conn.commit = MagicMock()

        self.conn.add([])

        self.conn.add_many.assert_called_once_with([])
        self.conn.commit.assert_called_once()


class TestPysolrCompatDelete(unittest.TestCase):
    """delete() should map pysolr kwargs (id=, q=) to solrpy methods."""

    def setUp(self):
        self.conn = _make_compat()

    def test_delete_by_id(self):
        with patch.object(solr.Solr, 'delete') as mock_delete:
            self.conn.commit = MagicMock()
            self.conn.delete(id='doc1', commit=True)
            mock_delete.assert_called_once_with(id='doc1')
            self.conn.commit.assert_called_once()

    def test_delete_by_query(self):
        self.conn.delete_query = MagicMock()
        self.conn.commit = MagicMock()

        self.conn.delete(q='category:obsolete')

        self.conn.delete_query.assert_called_once_with('category:obsolete')
        self.conn.commit.assert_called_once()

    def test_delete_by_id_and_query(self):
        """When both id and q are given, both operations should execute."""
        with patch.object(solr.Solr, 'delete') as mock_delete:
            self.conn.delete_query = MagicMock()
            self.conn.commit = MagicMock()

            self.conn.delete(id='doc1', q='category:obsolete')

            mock_delete.assert_called_once_with(id='doc1')
            self.conn.delete_query.assert_called_once_with('category:obsolete')
            self.conn.commit.assert_called_once()

    def test_delete_commit_defaults_true(self):
        with patch.object(solr.Solr, 'delete') as mock_delete:
            self.conn.commit = MagicMock()
            self.conn.delete(id='doc1')
            self.conn.commit.assert_called_once()

    def test_delete_no_commit(self):
        with patch.object(solr.Solr, 'delete') as mock_delete:
            self.conn.commit = MagicMock()
            self.conn.delete(id='doc1', commit=False)
            self.conn.commit.assert_not_called()


class TestPysolrCompatCommit(unittest.TestCase):
    """commit() should delegate to parent Solr.commit()."""

    def test_commit_delegates(self):
        conn = _make_compat()
        with patch.object(solr.Solr, 'commit') as mock_commit:
            conn.commit()
            mock_commit.assert_called_once()


class TestPysolrCompatPing(unittest.TestCase):
    """ping() should delegate to parent Solr.ping()."""

    def test_ping_delegates(self):
        conn = _make_compat()
        with patch.object(solr.Solr, 'ping', return_value=True) as mock_ping:
            result = conn.ping()
            mock_ping.assert_called_once()
            self.assertTrue(result)


class TestPysolrCompatExtract(unittest.TestCase):
    """extract() should create an Extract companion and delegate."""

    def setUp(self):
        self.conn = _make_compat()

    @patch('solr.compat.Extract')
    def test_extract_creates_companion_and_calls(self, MockExtract):
        mock_instance = MagicMock()
        MockExtract.return_value = mock_instance

        file_obj = MagicMock()
        self.conn.extract(file_obj, content_type='application/pdf', literal_id='doc1')

        MockExtract.assert_called_once_with(self.conn)
        mock_instance.assert_called_once_with(
            file_obj, content_type='application/pdf', literal_id='doc1'
        )

    @patch('solr.compat.Extract')
    def test_extract_returns_result(self, MockExtract):
        mock_instance = MagicMock(return_value='extract_result')
        MockExtract.return_value = mock_instance

        result = self.conn.extract(MagicMock())
        self.assertEqual(result, 'extract_result')


class TestPysolrCompatImport(unittest.TestCase):
    """PysolrCompat should be importable from the top-level solr package."""

    def test_importable_from_solr(self):
        from solr import PysolrCompat
        self.assertTrue(callable(PysolrCompat))


if __name__ == '__main__':
    unittest.main()
