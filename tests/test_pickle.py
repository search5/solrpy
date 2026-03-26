"""Auto-split from test_all.py"""

import pickle
import pickle as cPickle
import unittest
import solr


class SolrExceptionHttpStatusPickleTestCase(unittest.TestCase):

    module = pickle

    def setUp(self):
        self.initial = solr.SolrException(404, "Not Found")

    # These tests check current constructions:

    def test_unpicklable0(self):
        self._test_unpickle(self.module.dumps(self.initial, protocol=0))

    def test_unpicklable1(self):
        self._test_unpickle(self.module.dumps(self.initial, protocol=1))

    def test_unpicklable2(self):
        self._test_unpickle(self.module.dumps(self.initial, protocol=2))

    # These tests check legacy constructions, unpickled by self.module.
    # The initial pickles were constructed with past releases of solrpy.
    # (Persistent instances are known to exist in databases.)

    def test_legacy_cPickle_0(self):
        self._test_unpickle(
            b"csolr.core\nSolrException\np1\n(tRp2\n(dp3\nS'body'\np4\nNs"
            b"S'reason'\np5\nS'Not Found'\np6\nsS'httpcode'\np7\nI404\nsb.")

    def test_legacy_cPickle_1(self):
        self._test_unpickle(
            b'csolr.core\nSolrException\nq\x01)Rq\x02}q\x03(U\x04bodyq\x04NU'
            b'\x06reasonq\x05U\tNot Foundq\x06U\x08httpcodeq\x07M\x94\x01ub.')

    def test_legacy_cPickle_2(self):
        self._test_unpickle(
            b'\x80\x02csolr.core\nSolrException\nq\x01)Rq\x02}q\x03(U\x04body'
            b'q\x04NU\x06reasonq\x05U\tNot Foundq\x06U\x08httpcodeq\x07M\x94'
            b'\x01ub.')

    def test_legacy_pickle_0(self):
        self._test_unpickle(
            b"csolr.core\nSolrException\np0\n(tRp1\n(dp2\nS'body'\np3\nNs"
            b"S'reason'\np4\nS'Not Found'\np5\nsS'httpcode'\np6\nI404\nsb.")

    def test_legacy_pickle_1(self):
        self._test_unpickle(
            b'csolr.core\nSolrException\nq\x00)Rq\x01}q\x02(U\x04bodyq\x03NU'
            b'\x06reasonq\x04U\tNot Foundq\x05U\x08httpcodeq\x06M\x94\x01ub.')

    def test_legacy_pickle_2(self):
        self._test_unpickle(
            b'\x80\x02csolr.core\nSolrException\nq\x00)Rq\x01}q\x02(U\x04body'
            b'q\x03NU\x06reasonq\x04U\tNot Foundq\x05U\x08httpcodeq\x06M\x94'
            b'\x01ub.')

    def _test_unpickle(self, s):
        loaded = self.module.loads(s)
        self.assertEqual(loaded.httpcode, self.initial.httpcode)
        self.assertEqual(loaded.reason, self.initial.reason)
        self.assertEqual(loaded.body, self.initial.body)
        self.assertEqual(repr(loaded), repr(self.initial))
        self.assertEqual(str(loaded), str(self.initial))



class SolrExceptionSimpleMessagePickleTestCase(
    SolrExceptionHttpStatusPickleTestCase):

    def setUp(self):
        # Doesn't really fit the apparent intention for SolrException,
        # but this is used and has been used in the past, so let's
        # continue to work with existing pickled exceptions.
        self.initial = solr.SolrException("Simple message, not HTTP status")

    def test_legacy_cPickle_0(self):
        self._test_unpickle(
            b"csolr.core\nSolrException\np1\n(tRp2\n(dp3\nS'body'\np4\nNs"
            b"S'reason'\np5\nNsS'httpcode'\np6\n"
            b"S'Simple message, not HTTP status'\np7\nsb.")

    def test_legacy_cPickle_1(self):
        self._test_unpickle(
            b'csolr.core\nSolrException\nq\x01)Rq\x02}q\x03(U\x04bodyq\x04NU'
            b'\x06reasonq\x05NU\x08httpcodeq\x06U'
            b'\x1fSimple message, not HTTP statusq\x07ub.')

    def test_legacy_cPickle_2(self):
        self._test_unpickle(
            b'\x80\x02csolr.core\nSolrException\nq\x01)Rq\x02}q\x03(U\x04body'
            b'q\x04NU\x06reasonq\x05NU\x08httpcodeq\x06U'
            b'\x1fSimple message, not HTTP statusq\x07ub.')

    def test_legacy_pickle_0(self):
        self._test_unpickle(
            b"csolr.core\nSolrException\np0\n(tRp1\n(dp2\nS'body'\np3\nNs"
            b"S'reason'\np4\nNsS'httpcode'\np5\n"
            b"S'Simple message, not HTTP status'\np6\nsb.")

    def test_legacy_pickle_1(self):
        self._test_unpickle(
            b'csolr.core\nSolrException\nq\x00)Rq\x01}q\x02(U\x04bodyq\x03NU'
            b'\x06reasonq\x04NU\x08httpcodeq\x05U'
            b'\x1fSimple message, not HTTP statusq\x06ub.')

    def test_legacy_pickle_2(self):
        self._test_unpickle(
            b'\x80\x02csolr.core\nSolrException\nq\x00)Rq\x01}q\x02(U\x04body'
            b'q\x03NU\x06reasonq\x04NU\x08httpcodeq\x05U'
            b'\x1fSimple message, not HTTP statusq\x06ub.')



class SolrExceptionHttpStatusCPickleTestCase(
    SolrExceptionHttpStatusPickleTestCase):

    module = cPickle



class SolrExceptionSimpleMessageCPickleTestCase(
    SolrExceptionSimpleMessagePickleTestCase):

    module = cPickle


# ===================================================================
# 0.9.9 tests
# ===================================================================

