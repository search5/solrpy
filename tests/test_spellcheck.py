"""Tests for SpellcheckResult response wrapper."""

import unittest
import solr
from solr.response import Response, SpellcheckResult


class TestSpellcheckResult(unittest.TestCase):

    def test_correctly_spelled_true_by_default(self) -> None:
        sp = SpellcheckResult({})
        self.assertTrue(sp.correctly_spelled)

    def test_correctly_spelled_false(self) -> None:
        sp = SpellcheckResult({'correctlySpelled': False})
        self.assertFalse(sp.correctly_spelled)

    def test_collation_from_direct_key(self) -> None:
        sp = SpellcheckResult({'collation': 'corrected query'})
        self.assertEqual(sp.collation, 'corrected query')

    def test_collation_from_suggestions_list(self) -> None:
        raw = {
            'suggestions': [
                'misspeled',
                {'numFound': 1, 'startOffset': 0, 'endOffset': 9,
                 'suggestion': ['misspelled']},
                'collation', 'misspelled query',
            ]
        }
        sp = SpellcheckResult(raw)
        self.assertEqual(sp.collation, 'misspelled query')

    def test_collation_none_when_absent(self) -> None:
        sp = SpellcheckResult({'suggestions': []})
        self.assertIsNone(sp.collation)

    def test_suggestions_parsed(self) -> None:
        raw = {
            'suggestions': [
                'misspeled',
                {'numFound': 2, 'startOffset': 0, 'endOffset': 9,
                 'suggestion': ['misspelled', 'mispelled']},
            ]
        }
        sp = SpellcheckResult(raw)
        sug = sp.suggestions
        self.assertEqual(len(sug), 1)
        self.assertEqual(sug[0]['original'], 'misspeled')
        self.assertEqual(sug[0]['numFound'], 2)
        self.assertIn('suggestion', sug[0])

    def test_suggestions_multiple_words(self) -> None:
        raw = {
            'suggestions': [
                'word1', {'numFound': 1, 'suggestion': ['Word1']},
                'word2', {'numFound': 2, 'suggestion': ['Word2a', 'Word2b']},
            ]
        }
        sp = SpellcheckResult(raw)
        sug = sp.suggestions
        self.assertEqual(len(sug), 2)
        self.assertEqual(sug[0]['original'], 'word1')
        self.assertEqual(sug[1]['original'], 'word2')

    def test_suggestions_skips_collation_entry(self) -> None:
        raw = {
            'suggestions': [
                'misspeled', {'numFound': 1, 'suggestion': ['misspelled']},
                'collation', 'misspelled query',
            ]
        }
        sp = SpellcheckResult(raw)
        sug = sp.suggestions
        self.assertEqual(len(sug), 1)
        self.assertEqual(sug[0]['original'], 'misspeled')

    def test_suggestions_empty_list(self) -> None:
        sp = SpellcheckResult({'suggestions': []})
        self.assertEqual(sp.suggestions, [])

    def test_repr(self) -> None:
        sp = SpellcheckResult({'correctlySpelled': True})
        self.assertIn('SpellcheckResult', repr(sp))


class TestResponseSpellcheckProperty(unittest.TestCase):

    def test_spellcheck_none_by_default(self) -> None:
        resp = Response(None)
        self.assertIsNone(resp.spellcheck)

    def test_spellcheck_property_wraps_raw_dict(self) -> None:
        resp = Response(None)
        resp.spellcheck = {'correctlySpelled': False, 'collation': 'fix query'}  # type: ignore[assignment]
        self.assertIsInstance(resp.spellcheck, SpellcheckResult)

    def test_spellcheck_correctly_spelled(self) -> None:
        resp = Response(None)
        resp.spellcheck = {'correctlySpelled': False}  # type: ignore[assignment]
        assert resp.spellcheck is not None
        self.assertFalse(resp.spellcheck.correctly_spelled)

    def test_spellcheck_collation(self) -> None:
        resp = Response(None)
        resp.spellcheck = {'collation': 'corrected query'}  # type: ignore[assignment]
        assert resp.spellcheck is not None
        self.assertEqual(resp.spellcheck.collation, 'corrected query')

    def test_spellcheck_set_to_none(self) -> None:
        resp = Response(None)
        resp.spellcheck = {'correctlySpelled': True}  # type: ignore[assignment]
        resp.spellcheck = None  # type: ignore[assignment]
        self.assertIsNone(resp.spellcheck)

    def test_spellcheck_suggestions(self) -> None:
        resp = Response(None)
        resp.spellcheck = {  # type: ignore[assignment]
            'suggestions': [
                'tset', {'numFound': 1, 'suggestion': ['test']},
            ],
            'correctlySpelled': False,
        }
        assert resp.spellcheck is not None
        sug = resp.spellcheck.suggestions
        self.assertEqual(len(sug), 1)
        self.assertEqual(sug[0]['original'], 'tset')


class TestSpellcheckImport(unittest.TestCase):

    def test_importable_from_top_level(self) -> None:
        from solr import SpellcheckResult as TopLevel
        self.assertIs(TopLevel, SpellcheckResult)


if __name__ == "__main__":
    unittest.main()
