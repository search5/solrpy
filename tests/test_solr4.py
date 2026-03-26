"""Auto-split from test_all.py"""

import unittest
import solr
import solr.core
from tests.conftest import SOLR_HTTP


class TestSoftCommit(unittest.TestCase):

    def test_soft_commit_xml(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        sent = {}
        original_update = conn._update
        def capture(xstr, query=None, **kw):
            sent['xml'] = xstr
            return original_update(xstr, query, **kw)
        conn._update = capture
        conn.commit(soft_commit=True)
        self.assertIn('softCommit="true"', sent['xml'])
        conn.close()

    def test_soft_commit_default_false(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        sent = {}
        original_update = conn._update
        def capture(xstr, query=None, **kw):
            sent['xml'] = xstr
            return original_update(xstr, query, **kw)
        conn._update = capture
        conn.commit()
        self.assertNotIn('softCommit', sent['xml'])
        conn.close()

    def test_soft_commit_version_guard(self):
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = (3, 6, 0)
        with self.assertRaises(solr.core.SolrVersionError):
            conn.commit(soft_commit=True)



class TestAtomicUpdate(unittest.TestCase):

    def setUp(self):
        self.conn = solr.Solr(SOLR_HTTP, response_format='xml')
        self.conn.add({'id': 'atomic_test', 'data': 'original', 'user_id': 'u1'}, commit=True)

    def tearDown(self):
        self.conn.delete(id='atomic_test', commit=True)
        self.conn.close()

    def test_set_modifier(self):
        self.conn.atomic_update({
            'id': 'atomic_test',
            'data': {'set': 'updated'},
        }, commit=True)
        resp = self.conn.select('id:atomic_test')
        self.assertEqual(resp.results[0]['data'], 'updated')

    def test_inc_modifier(self):
        self.conn.add({'id': 'atomic_inc', 'data': 'x', 'num': 10}, commit=True)
        self.conn.atomic_update({
            'id': 'atomic_inc',
            'num': {'inc': 5},
        }, commit=True)
        resp = self.conn.select('id:atomic_inc')
        self.assertEqual(resp.results[0]['num'], 15)
        self.conn.delete(id='atomic_inc', commit=True)

    def test_set_none_removes_field(self):
        self.conn.atomic_update({
            'id': 'atomic_test',
            'user_id': {'set': None},
        }, commit=True)
        resp = self.conn.select('id:atomic_test')
        self.assertNotIn('user_id', resp.results[0])

    def test_atomic_update_many(self):
        self.conn.add({'id': 'atomic_m1', 'data': 'a'}, commit=True)
        self.conn.add({'id': 'atomic_m2', 'data': 'b'}, commit=True)
        self.conn.atomic_update_many([
            {'id': 'atomic_m1', 'data': {'set': 'aa'}},
            {'id': 'atomic_m2', 'data': {'set': 'bb'}},
        ], commit=True)
        r1 = self.conn.select('id:atomic_m1')
        r2 = self.conn.select('id:atomic_m2')
        self.assertEqual(r1.results[0]['data'], 'aa')
        self.assertEqual(r2.results[0]['data'], 'bb')
        self.conn.delete(ids=['atomic_m1', 'atomic_m2'], commit=True)

    def test_version_guard(self):
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = (3, 6, 0)
        with self.assertRaises(solr.core.SolrVersionError):
            conn.atomic_update({'id': '1', 'data': {'set': 'x'}})

    def test_xml_generation(self):
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = (9, 0, 0)
        conn.path = '/solr'
        conn.persistent = False
        conn.always_commit = False
        sent = {}
        conn._update = lambda xml, query=None, **kw: sent.update({'xml': xml})
        conn.atomic_update({'id': 'doc1', 'title': {'set': 'New'}, 'count': {'inc': 1}})
        xml = sent['xml']
        self.assertIn('<add>', xml)
        self.assertIn('update="set"', xml)
        self.assertIn('update="inc"', xml)
        self.assertIn('null="true"' if False else 'New', xml)



class TestRealtimeGet(unittest.TestCase):

    def setUp(self):
        self.conn = solr.Solr(SOLR_HTTP, response_format='xml')
        self.conn.add({'id': 'rtg_1', 'data': 'hello'}, commit=True)
        self.conn.add({'id': 'rtg_2', 'data': 'world'}, commit=True)

    def tearDown(self):
        self.conn.delete(ids=['rtg_1', 'rtg_2'], commit=True)
        self.conn.close()

    def test_get_single(self):
        doc = self.conn.get(id='rtg_1')
        self.assertIsNotNone(doc)
        self.assertEqual(doc['id'], 'rtg_1')

    def test_get_single_not_found(self):
        doc = self.conn.get(id='nonexistent_doc_xyz')
        self.assertIsNone(doc)

    def test_get_multiple(self):
        docs = self.conn.get(ids=['rtg_1', 'rtg_2'])
        self.assertEqual(len(docs), 2)
        ids = {d['id'] for d in docs}
        self.assertIn('rtg_1', ids)
        self.assertIn('rtg_2', ids)

    def test_get_with_fields(self):
        doc = self.conn.get(id='rtg_1', fields=['id', 'data'])
        self.assertIsNotNone(doc)
        self.assertIn('id', doc)

    def test_get_no_args_raises(self):
        with self.assertRaises(ValueError):
            self.conn.get()

    def test_version_guard(self):
        conn = solr.Solr.__new__(solr.Solr)
        conn.server_version = (3, 6, 0)
        with self.assertRaises(solr.core.SolrVersionError):
            conn.get(id='1')



class TestMoreLikeThis(unittest.TestCase):

    def test_mlt_explicit_creation(self):
        from solr import MoreLikeThis
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        mlt = MoreLikeThis(conn)
        self.assertIsInstance(mlt, MoreLikeThis)
        conn.close()

    def test_conn_has_no_mlt_attribute(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        self.assertFalse(hasattr(conn, 'mlt'))
        conn.close()

    def test_mlt_has_raw(self):
        from solr import MoreLikeThis
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        mlt = MoreLikeThis(conn)
        self.assertTrue(callable(getattr(mlt, 'raw', None)))
        conn.close()


if __name__ == "__main__":
    unittest.main()
