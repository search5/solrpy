"""Tests for Suggest handler wrapper (Solr 4.7+)."""

import json
import unittest
from unittest.mock import MagicMock

import solr
from solr.suggest import Suggest
from solr.exceptions import SolrVersionError


class TestSuggestVersionGuard(unittest.TestCase):

    def _make_conn(self, version: tuple[int, ...]) -> solr.Solr:
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = version
        conn.path = '/solr/core0'
        conn.auth_headers = {}
        return conn  # type: ignore[return-value]

    def test_raises_on_old_solr(self) -> None:
        conn = self._make_conn((4, 5, 0))
        suggest = Suggest(conn)
        with self.assertRaises(SolrVersionError):
            suggest('test')

    def test_passes_on_solr_4_7(self) -> None:
        conn = self._make_conn((4, 7, 0))
        mock_rsp = MagicMock()
        mock_rsp.read.return_value = json.dumps(
            {'suggest': {'s': {'test': {'numFound': 0, 'suggestions': []}}}}
        ).encode('utf-8')
        conn._get = MagicMock(return_value=mock_rsp)  # type: ignore[attr-defined]
        suggest = Suggest(conn)
        results = suggest('test')
        self.assertIsInstance(results, list)

    def test_passes_on_modern_solr(self) -> None:
        conn = self._make_conn((9, 0, 0))
        mock_rsp = MagicMock()
        mock_rsp.read.return_value = json.dumps({'suggest': {}}).encode('utf-8')
        conn._get = MagicMock(return_value=mock_rsp)  # type: ignore[attr-defined]
        suggest = Suggest(conn)
        results = suggest('que')
        self.assertEqual(results, [])


class TestSuggestExtract(unittest.TestCase):

    def setUp(self) -> None:
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = (8, 0, 0)
        conn.path = '/solr/core0'
        conn.auth_headers = {}
        self.suggest = Suggest(conn)  # type: ignore[arg-type]

    def test_extract_single_suggester(self) -> None:
        data = {
            'suggest': {
                'mySuggester': {
                    'que': {
                        'numFound': 2,
                        'suggestions': [
                            {'term': 'query', 'weight': 100, 'payload': ''},
                            {'term': 'question', 'weight': 80, 'payload': ''},
                        ],
                    }
                }
            }
        }
        results = self.suggest._extract_suggestions(data)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['term'], 'query')
        self.assertEqual(results[1]['term'], 'question')

    def test_extract_multiple_suggesters(self) -> None:
        data = {
            'suggest': {
                'suggesterA': {
                    'q': {'numFound': 1, 'suggestions': [
                        {'term': 'alpha', 'weight': 10, 'payload': ''}
                    ]},
                },
                'suggesterB': {
                    'q': {'numFound': 1, 'suggestions': [
                        {'term': 'beta', 'weight': 5, 'payload': ''}
                    ]},
                },
            }
        }
        results = self.suggest._extract_suggestions(data)
        terms = [r['term'] for r in results]
        self.assertIn('alpha', terms)
        self.assertIn('beta', terms)

    def test_extract_empty_response(self) -> None:
        data: dict = {'suggest': {}}
        results = self.suggest._extract_suggestions(data)
        self.assertEqual(results, [])

    def test_extract_missing_suggest_key(self) -> None:
        results = self.suggest._extract_suggestions({})
        self.assertEqual(results, [])


class TestSuggestQueryParams(unittest.TestCase):

    def _make_conn(self, version: tuple[int, ...] = (8, 0, 0)) -> solr.Solr:
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = version
        conn.path = '/solr/core0'
        conn.auth_headers = {}
        return conn  # type: ignore[return-value]

    def test_default_params_sent(self) -> None:
        conn = self._make_conn()
        mock_rsp = MagicMock()
        mock_rsp.read.return_value = json.dumps({'suggest': {}}).encode('utf-8')
        get_mock = MagicMock(return_value=mock_rsp)
        conn._get = get_mock  # type: ignore[attr-defined]
        Suggest(conn)('query')
        called_path = get_mock.call_args[0][0]
        self.assertIn('suggest=true', called_path)
        self.assertIn('suggest.q=query', called_path)
        self.assertIn('suggest.count=10', called_path)
        self.assertIn('wt=json', called_path)

    def test_dictionary_param_sent(self) -> None:
        conn = self._make_conn()
        mock_rsp = MagicMock()
        mock_rsp.read.return_value = json.dumps({'suggest': {}}).encode('utf-8')
        get_mock = MagicMock(return_value=mock_rsp)
        conn._get = get_mock  # type: ignore[attr-defined]
        Suggest(conn)('query', dictionary='myDict')
        called_path = get_mock.call_args[0][0]
        self.assertIn('suggest.dictionary=myDict', called_path)

    def test_count_param_sent(self) -> None:
        conn = self._make_conn()
        mock_rsp = MagicMock()
        mock_rsp.read.return_value = json.dumps({'suggest': {}}).encode('utf-8')
        get_mock = MagicMock(return_value=mock_rsp)
        conn._get = get_mock  # type: ignore[attr-defined]
        Suggest(conn)('q', count=5)
        called_path = get_mock.call_args[0][0]
        self.assertIn('suggest.count=5', called_path)


class TestSuggestImport(unittest.TestCase):

    def test_importable_from_top_level(self) -> None:
        from solr import Suggest as TopLevelSuggest
        self.assertIs(TopLevelSuggest, Suggest)


if __name__ == "__main__":
    unittest.main()
