"""Auto-split from test_all.py"""

import unittest
import solr
import solr.core
from tests.conftest import (
    SolrConnectionTestCase, RequestTracking, SOLR_HTTP, SOLR_PATH,
    get_rand_string, get_rand_userdoc,
)


class TestAddingDocuments(SolrConnectionTestCase):

    def setUp(self):
        super(TestAddingDocuments, self).setUp()
        self.conn = self.new_connection()

    def test_add_one_document(self):
        """ Try to add one document.
        """
        doc = get_rand_userdoc()

        self.add(**doc)
        self.conn.commit()
        results = self.query(self.conn, "id:" + doc["id"]).results

        self.assertEqual(len(results), 1,
            "Could not find expected data (id:%s)" % id)

        self.assertEqual(results[0]["user_id"], doc["user_id"])
        self.assertEqual(results[0]["data"], doc["data"])

    def test_add_one_document_multiplefields(self):
        """ Adds several documents with multiple fields, namely
        a list, a tuple, and a set
        """
        user_id = get_rand_string()
        data = get_rand_string()
        letterset = [ u'a', u'b', u'c' ]
        letters = [
            letterset,
            tuple(letterset),
            set(letterset),
            ]

        for lset in letters:
            doc = get_rand_userdoc(user_id=user_id, data=data)
            doc["letters"] = lset
            self.add(**doc)
            self.conn.commit()

        results = self.query(self.conn, "user_id:" + user_id).results

        self.assertEqual(len(results), 3,
            "Could not find expected data (user_id:%s)" % user_id)

        for i, doc in enumerate(results):
            self.assertEqual(doc["user_id"], user_id)
            self.assertEqual(doc["data"], data)
            self.assertEqual(doc["letters"], list(letters[i]))

    def test_add_one_document_implicit_commit(self):
        """ Try to add one document and commit changes in one operation.
        """

        # That one fails in r5 (<commit/> must be made on its own)

        doc = get_rand_userdoc()

        # Commit the changes
        self.conn.add(doc, commit=True)
        self.check_added(doc)

    def test_add_no_commit(self):
        """ Add one document without commiting the operation.
        """
        doc = get_rand_userdoc()
        self.add(**doc)
        results = self.query(self.conn, "user_id:" + doc["user_id"]).results
        self.assertEqual(len(results), 0,
            "Document (id:%s) shouldn't have been fetched" % (doc["id"]))

    def test_add_many(self):
        """ Try to add more than one document in a single operation.
        """
        doc_count = 10
        user_ids = [get_rand_string() for x in range(doc_count)]
        data =  [get_rand_string() for x in range(doc_count)]
        ids =  [get_rand_string() for x in range(doc_count)]
        documents = [dict(user_id=user_ids[x], data=data[x], id=ids[x])
                        for x in range(doc_count)]

        self.conn.add_many(documents)
        self.conn.commit()

        results = []
        for id in ids:
            res = self.query(self.conn, "id:" + id).results
            if not res:
                self.fail("Could not find document (id:%s)" % id)
            results.append(res[0])

        self.assertEqual(len(results), doc_count,
            "Query didn't return all documents. Expected: %d, got: %d" % (
                doc_count, len(results)))

        query_user_ids = [doc["user_id"] for doc in results]
        query_data = [doc["data"] for doc in results]
        query_ids = [doc["id"] for doc in results]

        # Symmetric difference will give us those documents which are neither
        # in original list nor in a fetched one. It's a handy way to check
        # whether all, and only those expected, documents have been returned.

        user_ids_symdiff = set(user_ids) ^ set(query_user_ids)
        data_symdiff = set(data) ^ set(query_data)
        ids_symdiff = set(ids) ^ set(query_ids)

        self.assertEqual(user_ids_symdiff, set([]),
            "User IDs sets differ (difference:%s)" % (user_ids_symdiff))
        self.assertEqual(data_symdiff, set([]),
            "Data sets differ (difference:%s)" % (data_symdiff))
        self.assertEqual(ids_symdiff, set([]),
            "IDs sets differ (difference:%s)" % (ids_symdiff))

    def test_add_many_implicit_commit(self):
        """ Add more than one document and commit changes, in one operation.
        """

        # That one fails in r5 (<commit/> must be made on its own)

        doc_count = 10
        user_ids = [get_rand_string() for x in range(doc_count)]
        data =  [get_rand_string() for x in range(doc_count)]
        ids =  [get_rand_string() for x in range(doc_count)]
        documents = [dict(user_id=user_ids[x], data=data[x], id=ids[x])
                        for x in range(doc_count)]

        # Pass in the commit flag.
        self.conn.add_many(documents, commit=True)

        results = []
        for id in ids:
            res = self.query(self.conn, "id:" + id).results
            if not res:
                self.fail("Could not find document (id:%s)" % id)
            results.append(res[0])

    def test_add_many_no_commit(self):
        """ Add many documents in a single operation without commiting.
        """
        doc_count = 10
        user_ids = [get_rand_string() for x in range(doc_count)]
        data =  [get_rand_string() for x in range(doc_count)]
        ids =  [get_rand_string() for x in range(doc_count)]
        documents = [dict(user_id=user_ids[x], data=data[x], id=ids[x])
                        for x in range(doc_count)]

        self.conn.add_many(documents)

        for user_id in user_ids:
            results = self.query(self.conn, "user_id:" + user_id).results
            self.assertEqual(len(results), 0,
                "Document (id:%s) shouldn't have been fetched" % (id))

    def test_add_unicode(self):
        """ Check whether Unicode data actually works for single document.
        """
        # "bile" in Polish (UTF-8).
        data = b"\xc5\xbc\xc3\xb3\xc5\x82\xc4\x87".decode("utf-8")
        doc = get_rand_userdoc(data=data)

        self.add(**doc)
        self.conn.commit()

        results = self.query(self.conn, "id:" + doc["id"]).results
        if not results:
            self.fail("Could not find document (id:%s)" % id)

        query_user_id = results[0]["user_id"]
        query_data = results[0]["data"]
        query_id = results[0]["id"]

        self.assertEqual(
            doc["user_id"], query_user_id,
            ("Invalid user_id, expected: %s, got: %s"
             % (doc["user_id"], query_user_id)))
        self.assertEqual(
            data, query_data,
            ("Invalid data, expected: %s, got: %s"
             % (repr(data), repr(query_data))))
        self.assertEqual(
            doc["id"], query_id,
            "Invalid id, expected: %s, got: %s" % (doc["id"], query_id))

    def test_add_many_unicode(self):
        """ Check correctness of handling Unicode data when adding many
        documents.
        """
        # Some Polish characters (UTF-8)
        chars = b"\xc4\x99\xc3\xb3\xc4\x85\xc5\x9b\xc5\x82\xc4\x98\xc3\x93\xc4\x84\xc5\x9a\xc5\x81".decode("utf-8")

        documents = [get_rand_userdoc(data=char) for char in chars]

        user_ids = [doc["user_id"] for doc in documents]
        ids = [doc["id"] for doc in documents]

        self.conn.add_many(documents)
        self.conn.commit()

        results = []
        for doc in documents:
            id = doc["id"]
            res = self.query(self.conn, "id:" + id).results
            if not res:
                self.fail("Could not find document (id:%s)" % id)
            results.append(res[0])

        self.assertEqual(len(results), len(chars),
            "Query didn't return all documents. Expected: %d, got: %d" % (
                len(chars), len(results)))

        # Use sets' symmetric difference to check if we have all documents
        # (same way as in TestAddingDocuments.test_add_many)

        query_user_ids = [doc["user_id"] for doc in results]
        query_data = [doc["data"] for doc in results]
        query_ids = [doc["id"] for doc in results]

        user_ids_symdiff = set(user_ids) ^ set(query_user_ids)
        data_symdiff = set(chars) ^ set(query_data)
        ids_symdiff = set(ids) ^ set(query_ids)

        self.assertEqual(user_ids_symdiff, set([]),
            "User IDs sets differ (difference:%s)" % (user_ids_symdiff))
        self.assertEqual(data_symdiff, set([]),
            "Data sets differ (difference:%s)" % (data_symdiff))
        self.assertEqual(ids_symdiff, set([]),
            "IDs sets differ (difference:%s)" % (ids_symdiff))

    def test_add_none_field(self):
        """ Try to add a document with a field of None
        """
        doc = get_rand_userdoc()
        doc["num"] = None

        self.add(**doc)



class TestUpdatingDocuments(SolrConnectionTestCase):

    def setUp(self):
        super(TestUpdatingDocuments, self).setUp()
        self.conn = self.new_connection()

    def test_update_single(self):
        """ Try to add one document, and then update it (readd it)
        """
        user_id = get_rand_string()
        data = get_rand_string()
        updated_data = get_rand_string()
        id = get_rand_string()

        doc = {}
        doc["user_id"] = user_id
        doc["data"] = data
        doc["id"] = id

        self.add(**doc)
        self.conn.commit()

        # we assume this works, being tested elsewhere
        doc["data"] = updated_data
        self.add(**doc)
        self.conn.commit()

        results = self.query(self.conn, "id:" + id).results
        doc = results[0]
        self.assertEqual(doc["data"], updated_data)

    def test_update_many(self):
        """ Try to add more than one document in a single operation, and then
        again to update them all in a single run.
        """
        doc_count = 10
        user_ids = [get_rand_string() for x in range(doc_count)]
        data =  [get_rand_string() for x in range(doc_count)]
        updated_data = [get_rand_string() for x in range(doc_count)]
        ids =  [get_rand_string() for x in range(doc_count)]
        documents = [dict(user_id=user_ids[x], data=data[x], id=ids[x])
                        for x in range(doc_count)]

        self.conn.add_many(documents)
        self.conn.commit()

        # we assume the previous operation went through correctly, since
        # it has a test all for itself.
        for i, doc in enumerate(documents):
            doc["data"] = updated_data[i]

        self.conn.add_many(documents)
        self.conn.commit()

        results = []
        for id in ids:
            res = self.query(self.conn, "id:" + id).results
            if not res:
                self.fail("Could not find document (id:%s)" % id)
            results.append(res[0])

        self.assertEqual(len(results), doc_count,
            "Query didn't return all documents. Expected: %d, got: %d" % (
                doc_count, len(results)))

        query_user_ids = [doc["user_id"] for doc in results]
        query_data = [doc["data"] for doc in results]
        query_ids = [doc["id"] for doc in results]

        # Symmetric difference will give us those documents which are neither
        # in original list nor in a fetched one. It's a handy way to check
        # whether all, and only those expected, documents have been returned.

        user_ids_symdiff = set(user_ids) ^ set(query_user_ids)
        data_symdiff = set(updated_data) ^ set(query_data)
        ids_symdiff = set(ids) ^ set(query_ids)

        self.assertEqual(user_ids_symdiff, set([]),
            "User IDs sets differ (difference:%s)" % (user_ids_symdiff))
        self.assertEqual(data_symdiff, set([]),
            "Data sets differ (difference:%s)" % (data_symdiff))
        self.assertEqual(ids_symdiff, set([]),
            "IDs sets differ (difference:%s)" % (ids_symdiff))



class TestDocumentsDeletion(SolrConnectionTestCase):

    def setUp(self):
        super(TestDocumentsDeletion, self).setUp()
        self.conn = self.new_connection()

    def test_delete_one_document_by_query(self):
        """ Try to delete a single document matching a given query.
        """
        doc = get_rand_userdoc()
        self.add(**doc)
        self.conn.commit()

        id = doc["id"]
        results = self.query(self.conn, "id:" + id).results

        self.conn.delete_query("id:" + id)
        self.conn.commit()

        results = self.query(self.conn, "id:" + id).results
        self.assertEqual(len(results), 0,
            "Document (id:%s) should've been deleted" % id)

    def test_delete_many_documents_by_query(self):
        """ Try to delete many documents matching a given query.
        """
        doc_count = 10
        # Same user ID will be used for all documents.
        user_id = get_rand_string()

        for x in range(doc_count):
            self.add(**get_rand_userdoc(user_id=user_id))

        self.conn.commit()
        results = self.query(self.conn, "user_id:" + user_id).results

        # Make sure the docs were in fact added.
        self.assertEqual(len(results), doc_count,
            "There should be %d documents for user_id:%s" % (doc_count, user_id))

        # Now delete documents and commit the changes
        self.conn.delete_query("user_id:" + user_id)
        self.conn.commit()

        results = self.query(self.conn, "user_id:" + user_id).results

        self.assertEqual(len(results), 0,
            "There should be no documents for user_id:%s" % (user_id))

    def test_delete_many(self):
        """ Delete many documents in one pass.
        """

        # That one fails in r5 (because of improper handling of batches)

        doc_count = 10
        ids = [get_rand_string() for x in range(doc_count)]

        # Same data and user_id for all documents
        data = user_id = get_rand_string()

        for id in ids:
            self.add(id=id, data=data, user_id=user_id)
        self.conn.commit()

        # Make sure they've been added
        for id in ids:
            results = self.query(self.conn, "id:" + id).results
            self.assertEqual(len(results), 1,
                "Document (id:%s) should've been added to index" % id)

        # Delete documents by their ID and commit changes
        self.conn.delete_many(ids)
        self.conn.commit()

        # Make sure they've been deleted
        for id in ids:
            results = self.query(self.conn, "id:" + id).results
            self.assertEqual(len(results), 0,
                "Document (id:%s) should've been deleted from index" % id)

    def test_delete_by_unique_key(self):
        """ Delete a document by its unique key (as defined in Solr's schema).
        """
        id = get_rand_string()

        # Same data and user_id
        user_id = data = get_rand_string()

        self.add(id=id, user_id=user_id, data=data)
        self.conn.commit()

        # Make sure it's been added
        results = self.query(self.conn, "id:" + id).results

        # Make sure the docs were in fact added.
        self.assertEqual(len(results), 1,
            "No results returned for query id:%s"% (id))

        # Delete the document and make sure it's no longer in the index
        self.conn.delete(id)
        self.conn.commit()
        results = self.query(self.conn, "id:" + id).results
        self.assertEqual(len(results), 0,
            "Document (id:%s) should've been deleted"% (id))



class TestCommitingOptimizing(SolrConnectionTestCase):

    def setUp(self):
        super(TestCommitingOptimizing, self).setUp()
        self.conn = self.new_connection()

    def test_commit(self):
        """ Check whether commiting works.
        """
        # Same id, data and user_id
        id = get_rand_string()
        self.add(id=id, user_id=id, data=id)

        # Make sure the changes weren't commited.
        results = self.query(self.conn, "id:" + id).results
        self.assertEqual(len(results), 0,
            ("Changes to index shouldn't be visible without commiting, "
             "results:%s" % (repr(results))))

        # Now commit the changes and check whether it's been successful.
        self.conn.commit()

        results = self.query(self.conn, "id:" + id).results
        self.assertEqual(len(results), 1,
            "No documents returned, results:%s" % (repr(results)))

    def test_optimize(self):
        """ Check whether optimizing works.
        """
        # Same id, data and user_id
        id = get_rand_string()
        self.add(id=id, user_id=id, data=id)

        # Make sure the changes weren't commited.
        results = self.query(self.conn, "id:" + id).results
        self.assertEqual(len(results), 0,
            ("Changes to index shouldn't be visible without call"
             "to optimize first, results:%s" % (repr(results))))

        # Optimizing commits the changes
        self.conn.optimize()

        results = self.query(self.conn, "id:" + id).results
        self.assertEqual(len(results), 1,
            "No documents returned, results:%s" % (repr(results)))

    def test_commit_optimize(self):
        """ Check whether commiting with an optimize flag works.
        Well, actually it's pretty hard (if possible at all) to check it
        remotely, for now, let's just check whether the changes are being
        commited.
        """
        # Same id, data and user_id
        id = get_rand_string()
        self.add(id=id, user_id=id, data=id)

        # Make sure the changes weren't commited.
        results = self.query(self.conn, "id:" + id).results
        self.assertEqual(len(results), 0,
            ("Changes to index shouldn't be visible without commiting, "
             "results:%s" % (repr(results))))

        # Optimizing commits the changes
        self.conn.commit(_optimize=True)

        results = self.query(self.conn, "id:" + id).results
        self.assertEqual(len(results), 1,
            "No documents returned, results:%s" % (repr(results)))



class TestCommitControlAdd(RequestTracking):

    def setUp(self):
        super().setUp()
        self.conn = self.new_connection()

    def test_add_inline_optimize(self):
        doc = get_rand_userdoc()
        self.conn.add(doc, optimize=True)
        self.assertEqual(self.selector(), "/update?optimize=true")
        self.check_added(doc)

    def test_add_many_inline_optimize(self):
        documents = [get_rand_userdoc() for x in range(10)]
        self.conn.add_many(documents, optimize=True)
        self.assertEqual(self.selector(), "/update?optimize=true")
        self.check_added(docs=documents)

    def test_add_noflush(self):
        doc = get_rand_userdoc()
        self.conn.add(doc, commit=True, wait_flush=False)
        self.assertEqual(
            self.selector(),
            "/update?commit=true&waitFlush=false&waitSearcher=false")
        self.assertTrue(b"<add>" in self.postbody())

    def test_add_nosearcher(self):
        doc = get_rand_userdoc()
        self.conn.add(doc, commit=True, wait_searcher=False)
        self.assertEqual(
            self.selector(),
            "/update?commit=true&waitSearcher=false")
        self.assertTrue(b"<add>" in self.postbody())

    def test_add_waitflush_without_commit(self):
        doc = get_rand_userdoc()
        self.assertRaises(TypeError, self.conn.add, doc, wait_flush=False)

    def test_add_waitsearcher_without_commit(self):
        doc = get_rand_userdoc()
        self.assertRaises(TypeError, self.conn.add, doc, wait_searcher=False)

    def test_add_many_commit_noflush(self):
        documents = [get_rand_userdoc() for i in range(3)]
        self.conn.add_many(documents, commit=True, wait_flush=False)
        self.assertEqual(
            self.selector(),
            "/update?commit=true&waitFlush=false&waitSearcher=false")
        self.assertTrue(b"<add>" in self.postbody())

    def test_add_many_commit_nosearcher(self):
        documents = [get_rand_userdoc() for i in range(3)]
        self.conn.add_many(documents, commit=True, wait_searcher=False)
        self.assertEqual(
            self.selector(),
            "/update?commit=true&waitSearcher=false")
        self.assertTrue(b"<add>" in self.postbody())



class TestCommitControlDelete(RequestTracking):

    def setUp(self):
        super().setUp()
        self.conn = self.new_connection()

    def test_delete_inline_commit(self):
        doc = get_rand_userdoc()
        self.conn.add(doc, commit=True)
        self.check_added(doc)
        self.conn.delete_query("id:" + doc["id"], commit=True)
        self.check_removed(doc)

    def test_delete_inline_optimize(self):
        doc = get_rand_userdoc()
        self.conn.add(doc, commit=True)
        self.check_added(doc)
        self.conn.delete(doc["id"], optimize=True)
        self.check_removed(doc)

    def test_delete_noflush(self):
        doc = get_rand_userdoc()
        self.conn.add(doc, commit=True)
        self.check_added(doc)
        self.conn.delete(doc["id"], commit=True, wait_flush=False)
        self.assertEqual(
            self.selector(),
            "/update?commit=true&waitFlush=false&waitSearcher=false")
        self.assertTrue(b"<delete>" in self.postbody())

    def test_delete_nosearcher(self):
        doc = get_rand_userdoc()
        self.conn.add(doc, commit=True)
        self.check_added(doc)
        self.conn.delete(doc["id"], commit=True, wait_searcher=False)
        self.assertEqual(
            self.selector(),
            "/update?commit=true&waitSearcher=false")
        self.assertTrue(b"<delete>" in self.postbody())

    def test_delete_queries_inline_commit(self):
        uid1 = get_rand_string()
        uid2 = get_rand_string()
        documents = (
            [get_rand_userdoc(user_id=uid1) for i in range(3)] +
            [get_rand_userdoc(user_id=uid2) for i in range(3)]
            )
        self.conn.add_many(documents, commit=True)
        self.check_added(docs=documents)
        self.conn.delete(queries=["user_id:" + uid2, "user_id:" + uid1],
                         commit=True)
        self.check_removed(docs=documents)

    def test_delete_combined_inline_commit(self):
        doc1 = get_rand_userdoc()
        doc2 = get_rand_userdoc()
        doc3 = get_rand_userdoc()
        user_id = get_rand_string()
        docs = [get_rand_userdoc(user_id=user_id) for i in range(10)]
        alldocs = [doc1, doc2, doc3] + docs
        self.conn.add_many(alldocs, commit=True)
        self.check_added(docs=alldocs)
        self.conn.delete(id=doc1["id"], ids=[doc2["id"], doc3["id"]],
                         queries=["user_id:" + user_id],
                         commit=True)
        self.check_removed(docs=alldocs)



class TestCommitOptimize(unittest.TestCase):
    """commit(_optimize=True) should actually issue an optimize command."""

    def test_commit_optimize_sends_optimize_verb(self):
        conn = solr.Solr(SOLR_HTTP)
        sent = {}
        original_update = conn._update
        def capture_update(xstr, query=None, **kw):
            sent['xml'] = xstr
            return original_update(xstr, query, **kw)
        conn._update = capture_update
        conn.commit(_optimize=True)
        self.assertIn('<optimize', sent['xml'])
        conn.close()

    def test_commit_default_sends_commit_verb(self):
        conn = solr.Solr(SOLR_HTTP)
        sent = {}
        original_update = conn._update
        def capture_update(xstr, query=None, **kw):
            sent['xml'] = xstr
            return original_update(xstr, query, **kw)
        conn._update = capture_update
        conn.commit()
        self.assertIn('<commit', sent['xml'])
        conn.close()


# ===================================================================
# Version detection tests
# ===================================================================


class TestAlwaysCommit(unittest.TestCase):
    """Test the always_commit constructor option."""

    def test_default_always_commit_is_false(self):
        conn = solr.Solr(SOLR_HTTP)
        self.assertFalse(conn.always_commit)
        conn.close()

    def test_always_commit_true(self):
        conn = solr.Solr(SOLR_HTTP, always_commit=True)
        self.assertTrue(conn.always_commit)
        conn.close()

    def test_always_commit_add_sends_commit(self):
        conn = solr.Solr(SOLR_HTTP, always_commit=True)
        sent = {}
        original_update = conn._update
        def capture_update(content, query=None, **kw):
            sent['query'] = query
            return original_update(content, query, **kw)
        conn._update = capture_update
        conn.add({'id': 'always_commit_test', 'data': 'test'})
        self.assertIn('commit', sent.get('query', {}))
        conn.delete(id='always_commit_test', commit=True)
        conn.close()

    def test_always_commit_override_false(self):
        conn = solr.Solr(SOLR_HTTP, always_commit=True)
        sent = {}
        original_update = conn._update
        def capture_update(content, query=None, **kw):
            sent['query'] = query
            return original_update(content, query, **kw)
        conn._update = capture_update
        conn.add({'id': 'always_commit_test2', 'data': 'test'}, commit=False)
        self.assertEqual(sent.get('query', {}), {})
        conn.delete(id='always_commit_test2', commit=True)
        conn.close()


