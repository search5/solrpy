# -*- coding: utf-8 -*-

"""
Test cases for the Python Solr client.

Meant to be run against Solr 1.2+.
"""

# stdlib
import socket
import datetime
import unittest
import httplib
from string import digits
from random import choice
from xml.dom.minidom import parseString

# solrpy
import solr
import solr.core

SOLR_PATH = "/solr"
SOLR_HOST = "localhost"
SOLR_PORT_HTTP = "8983"
SOLR_PORT_HTTPS = "8943"
SOLR_HTTP = "http://" + SOLR_HOST + ":" + SOLR_PORT_HTTP  + SOLR_PATH
SOLR_HTTPS = "https://" + SOLR_HOST + ":" + SOLR_PORT_HTTPS + SOLR_PATH


def get_rand_string():
    return "".join(choice(digits)  for x in range(12))


def get_rand_userdoc(id=None, user_id=None, data=None):
    return {
        "user_id": user_id or get_rand_string(),
        "data": data or get_rand_string(),
        "id": id or get_rand_string(),
        }


# The names of the following two classes relate specifically to the
# class names in solr.core.

class SolrConnectionTestCase(unittest.TestCase):

    connection_factory = solr.SolrConnection

    def setUp(self):
        self._connections = []

    def tearDown(self):
        for conn in self._connections:
            conn.close()

    def new_connection(self, **kw):
        conn = self.connection_factory(SOLR_HTTP, **kw)
        self._connections.append(conn)
        return conn

    def add(self, **doc):
        # This is used to abstract away the differences in the ``add``
        # method for the two connection APIs; this is overridden for use
        # with the ``solr.Solr`` connection class.
        self._connections[-1].add(**doc)

    def query(self, conn, *args, **params):
        return conn.query(*args, **params)

    def raw_query(self, conn, **params):
        return conn.raw_query(**params)

    def check_added(self, doc=None, docs=None):
        if docs is None:
            docs = []
        if doc is not None:
            docs.append(doc)
        conn = self._connections[-1]
        for doc in docs:
            # Search for a single document and verify the fields.
            results = self.query(conn, "id:" + doc["id"]).results
            self.assertEquals(
                len(results), 1,
                "Could not find expected data (id:%s)" % doc["id"])
            self.assertEquals(results[0]["user_id"], doc["user_id"])
            self.assertEquals(results[0]["data"], doc["data"])

    def check_removed(self, doc=None, docs=None):
        if docs is None:
            docs = []
        if doc is not None:
            docs.append(doc)
        conn = self._connections[-1]
        for doc in docs:
            results = self.query(conn, "id:" + doc["id"]).results
            self.assertEquals(
                len(results), 0,
                "Document (id:%s) should've been deleted" % doc["id"])


class SolrBased(SolrConnectionTestCase):

    connection_factory = solr.Solr

    def add(self, **doc):
        self._connections[-1].add(doc)

    def query(self, conn, *args, **params):
        return conn.select(*args, **params)

    def raw_query(self, conn, **params):
        return conn.select.raw(**params)


class RequestTracking(SolrConnectionTestCase):
    """ Mix in request tracking for tests.

    After each request, the ``method``, ``selector`` and ``postbody``
    methods will returned the indicated information about the last request.

    """

    def new_connection(self, **kw):
        conn = super(RequestTracking, self).new_connection(**kw)
        request = conn.conn.request

        def wrap(*args, **kw):
            self._update = args, kw
            return request(*args, **kw)

        conn.conn.request = wrap
        return conn

    # Access information from the most recent request:

    def method(self):
        return self._update[0][0]

    def selector(self):
        s = self._update[0][1]
        if s.startswith(SOLR_PATH):
            return s[len(SOLR_PATH):]
        self.fail("URL path doesn't start with expected prefix: ")

    def postbody(self):
        return self._update[0][2]


class TestHTTPConnection(SolrConnectionTestCase):

    def test_connect(self):
        """ Check if we're really get connected to Solr through HTTP.
        """
        conn = self.new_connection()

        try:
            conn.conn.request("GET", SOLR_PATH)
        except socket.error:
            self.fail("Connection to %s failed" % (SOLR_HTTP))

        status = conn.conn.getresponse().status
        self.assertEquals(status, 302,
                          "Expected FOUND (302), got: %d" % status)

    def test_close_connection(self):
        """ Make sure connections to Solr are being closed properly.
        """
        conn = self.new_connection()
        conn.conn.request("GET", SOLR_PATH)
        conn.close()

        # Closing the Solr connection should close the underlying
        # HTTPConnection's socket.
        self.assertEquals(conn.conn.sock, None, "Connection not closed")

    def test_invalid_max_retries(self):
        """ Passing something that can't be cast as an integer for max_retries
        should raise a ValueError and a value less than 0 should raise an
        AssertionError """
        self.assertRaises(ValueError, self.new_connection,
                          max_retries='asdf')
        self.assertRaises(AssertionError, self.new_connection,
                          max_retries=-5)


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

        self.assertEquals(len(results), 1,
            "Could not find expected data (id:%s)" % id)

        self.assertEquals(results[0]["user_id"], doc["user_id"])
        self.assertEquals(results[0]["data"], doc["data"])

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

        self.assertEquals(len(results), 3,
            "Could not find expected data (user_id:%s)" % user_id)

        for i, doc in enumerate(results):
            self.assertEquals(doc["user_id"], user_id)
            self.assertEquals(doc["data"], data)
            self.assertEquals(doc["letters"], list(letters[i]))

    def test_add_one_document_implicit_commit(self):
        """ Try to add one document and commit changes in one operation.
        """

        # That one fails in r5 (<commit/> must be made on its own)

        doc = get_rand_userdoc()

        # Commit the changes
        self.conn.add(True, **doc)
        self.check_added(doc)

    def test_add_no_commit(self):
        """ Add one document without commiting the operation.
        """
        doc = get_rand_userdoc()
        self.add(**doc)
        results = self.query(self.conn, "user_id:" + doc["user_id"]).results
        self.assertEquals(len(results), 0,
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

        self.assertEquals(len(results), doc_count,
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
        self.conn.add_many(documents, True)

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
            self.assertEquals(len(results), 0,
                "Document (id:%s) shouldn't have been fetched" % (id))

    def test_add_unicode(self):
        """ Check whether Unicode data actually works for single document.
        """
        # "bile" in Polish (UTF-8).
        data = "\xc5\xbc\xc3\xb3\xc5\x82\xc4\x87".decode("utf-8")
        doc = get_rand_userdoc(data=data)

        self.add(**doc)
        self.conn.commit()

        results = self.query(self.conn, "id:" + doc["id"]).results
        if not results:
            self.fail("Could not find document (id:%s)" % id)

        query_user_id = results[0]["user_id"]
        query_data = results[0]["data"]
        query_id = results[0]["id"]

        self.assertEquals(
            doc["user_id"], query_user_id,
            ("Invalid user_id, expected: %s, got: %s"
             % (doc["user_id"], query_user_id)))
        self.assertEquals(
            data, query_data,
            ("Invalid data, expected: %s, got: %s"
             % (repr(data), repr(query_data))))
        self.assertEquals(
            doc["id"], query_id,
            "Invalid id, expected: %s, got: %s" % (doc["id"], query_id))

    def test_add_many_unicode(self):
        """ Check correctness of handling Unicode data when adding many
        documents.
        """
        # Some Polish characters (UTF-8)
        chars = ("\xc4\x99\xc3\xb3\xc4\x85\xc5\x9b\xc5\x82"
                 "\xc4\x98\xc3\x93\xc4\x84\xc5\x9a\xc5\x81").decode("utf-8")

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

        self.assertEquals(len(results), len(chars),
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
        self.assertEquals(doc["data"], updated_data)

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

        self.assertEquals(len(results), doc_count,
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
        self.assertEquals(len(results), 0,
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
        self.assertEquals(len(results), doc_count,
            "There should be %d documents for user_id:%s" % (doc_count, user_id))

        # Now delete documents and commit the changes
        self.conn.delete_query("user_id:" + user_id)
        self.conn.commit()

        results = self.query(self.conn, "user_id:" + user_id).results

        self.assertEquals(len(results), 0,
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
            self.assertEquals(len(results), 1,
                "Document (id:%s) should've been added to index" % id)

        # Delete documents by their ID and commit changes
        self.conn.delete_many(ids)
        self.conn.commit()

        # Make sure they've been deleted
        for id in ids:
            results = self.query(self.conn, "id:" + id).results
            self.assertEquals(len(results), 0,
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
        self.assertEquals(len(results), 1,
            "No results returned for query id:%s"% (id))

        # Delete the document and make sure it's no longer in the index
        self.conn.delete(id)
        self.conn.commit()
        results = self.query(self.conn, "id:" + id).results
        self.assertEquals(len(results), 0,
            "Document (id:%s) should've been deleted"% (id))


class TestQuerying(SolrConnectionTestCase):

    def setUp(self):
        super(TestQuerying, self).setUp()
        self.conn = self.new_connection(timeout=1)

    def test_query_string(self):
        """ Get documents (all default fields) by a simple query.
        """
        doc_count = 10
        ids = [get_rand_string() for x in range(doc_count)]

        # Same user_id and data for all documents
        user_id = get_rand_string()
        data = get_rand_string()

        for id in ids:
            self.add(id=id, user_id=user_id, data=data)
        self.conn.commit()

        results = self.query(self.conn, "user_id:" + user_id).results
        self.assertEquals(len(results), doc_count,
            "There should be exactly %d documents returned, got: %d" % (
                doc_count, len(results)))

        for result in results:
            for field in ["user_id", "id", "data", "score"]:
                self.assertTrue(field in result,
                    "No %s field returned, doc:%s" % (field, repr(result)))

                self.assertTrue(result[field],
                    "Field %s has no value,  doc:%s" % (field, repr(result)))

        # Use the symmetric difference to check whether all IDs have been
        # fetched by a query.

        query_ids = [doc["id"] for doc in results]
        ids_symdiff = set(ids) ^ set(query_ids)

        self.assertEquals(ids_symdiff, set([]),
            "IDs sets differ (difference:%s)" % (ids_symdiff))

        # Now loop through results and check whether fields are okay
        for result in results:
            for id in ids:
                if result["id"] == id:
                    self.assertEquals(result["data"], data,
                        "Data differs, expected:%s, got:%s" % (
                            data, result["data"]))
                    self.assertEquals(result["user_id"], user_id,
                        "User ID differs, expected:%s, got:%s" % (
                            data, result["user_id"]))

                    # We don't know the exact score, although we know it does
                    # exist and should be a float instance.
                    score = result["score"]
                    self.assertTrue(isinstance(score, float),
                        "Score should be a float instance, score:%s" % (
                            repr(score)))

    def test_query_specific_field(self):
        """ Try to return only a specific field.
        """
        field_to_return = "id"
        doc_count = 10
        ids = [get_rand_string() for x in range(doc_count)]
        user_ids = [get_rand_string() for x in range(doc_count)]

        # Same data for all documents
        data = get_rand_string()

        for idx, id in enumerate(ids):
            self.add(id=ids[idx], user_id=user_ids[idx], data=data)
        self.conn.commit()

        # We want to return only the "id" field
        results = self.query(
            self.conn, "data:" + data, fields=field_to_return).results
        self.assertEquals(len(results), doc_count,
            "There should be exactly %d documents returned, got: %d" % (
                doc_count, len(results)))

        # Use the symmetric difference to check whether all IDs have been
        # fetched by a query.

        query_ids = [doc[field_to_return] for doc in results]
        ids_symdiff = set(ids) ^ set(query_ids)

        self.assertEquals(
            ids_symdiff, set([]),
            "Query didn't return expected fields (difference:%s)"
            % (ids_symdiff))

        # Make sure no other field has been returned, note: by default
        # queries also return score for each document.

        for result in results:
            fields = result.keys()
            fields.remove(field_to_return)

            # Now there should only a score field
            self.assertEquals(len(fields), 1,
                ("More fields returned than expected, "
                "expected:%s and score, the result is:%s)" % (
                    field_to_return,result)))

            self.assertEquals(
                fields[0], "score",
                "Query returned some other fields then %s and score, result:%s"
                % (field_to_return,result))

    def test_query_score(self):
        """ Make sure the score field is returned and is a float instance.
        """
        id = get_rand_string()

        # Same data and user_id
        user_id = data = get_rand_string()

        self.add(id=id, user_id=user_id, data=data)
        self.conn.commit()

        results = self.query(self.conn, "id:" + id).results
        self.assertEquals(len(results), 1,
            "No documents fetched, expected id:%s" % (id))

        doc = results[0]

        self.assertTrue(
            "score" in doc, "No score returned, doc:%s" % repr(doc))
        self.assertTrue(isinstance(doc["score"], float),
            "Score should be a float instance, doc:%s" % repr(doc))

    def test_query_no_score(self):
        """ Check whether the score is not being returned when explicitly
        told not to do so.
        """
        id = get_rand_string()

        # Same data and user_id
        user_id = data = get_rand_string()

        self.add(id=id, user_id=user_id, data=data)
        self.conn.commit()

        results = self.query(self.conn, "id:" + id, score=False).results

        self.assertEquals(len(results), 1,
            "No documents fetched, expected id:%s" % (id))

        doc = results[0]

        self.assertTrue("score" not in doc,
            "No score should be returned, doc:%s" % repr(doc))

    def test_query_highlight_boolean_one_field(self):
        """ Test whether highlighting works for one field when given
        a highlight=True parameter.
        """
        id = get_rand_string()

        # Same data and user_id
        user_id = data = get_rand_string()

        self.add(id=id, user_id=user_id, data=data)
        self.conn.commit()

        # Specify the fields to highlight as a string
        response = self.query(
            self.conn, "id:" + id, highlight=True, fields="id")

        self.assertTrue(hasattr(response, "highlighting"),
            ("No fields have been highlighted "
            "(exptected a 'highlighting' attribute), id:%s") % (id))

        highlighting = response.highlighting

        self.assertTrue(id in highlighting,
            "Document (id:%s) should've been highlighted")

        self.assertTrue(len(highlighting[id]) == 1,
            ("There should be exactly one document highlighted, "
             "id:%s, highlighting:%s" % (id, highlighting)))

        self.assertTrue("id" in highlighting[id],
            "id should be highlighted, highlighting:%s" % (highlighting))

        content = parseString(highlighting[id]["id"][0])
        highlighting_id = content.firstChild.firstChild.nodeValue
        self.assertEquals(highlighting_id, id,
            "Highlighting didn't return id value, expected:%s, got:%s" % (
                id, highlighting_id))

        # Now do the same but use a list instead
        response = self.query(
            self.conn, "id:" + id, highlight=True, fields=["id"])

        self.assertTrue(hasattr(response, "highlighting"),
            "No fields have been highlighted, id:%s" % (id))

        highlighting = response.highlighting

        self.assertTrue(id in highlighting,
            "Document (id:%s) should've been highlighted")

        self.assertTrue(len(highlighting[id]) == 1,
            ("There should be exactly one document highlighted, "
             "id:%s, highlighting:%s" % (id, highlighting)))

        self.assertTrue("id" in highlighting[id],
            "id should be highlighted, highlighting:%s" % (highlighting))

        content = parseString(highlighting[id]["id"][0])
        highlighting_id = content.firstChild.firstChild.nodeValue
        self.assertEquals(highlighting_id, id,
            "Highlighting didn't return id value, expected:%s, got:%s" % (
                id, highlighting_id))

    def test_query_highlight_list_of_fields(self):
        """ Test whether highlighting works for a list of fields.
        """
        fields_to_highlight = ["user_id", "data"]
        id = get_rand_string()

        # Same data and user_id
        user_id = data = get_rand_string()

        self.add(id=id, user_id=user_id, data=data)
        self.conn.commit()

        # Specify the fields to highlight as a list of fields
        response = self.query(self.conn, "user_id:" + user_id,
            highlight=fields_to_highlight)

        self.assertTrue(hasattr(response, "highlighting"),
            ("No fields have been highlighted "
            "(exptected a 'highlighting' attribute), id:%s") % (id))

        highlighting = response.highlighting

        self.assertTrue(id in highlighting,
            "Document (id:%s) should've been highlighted")

        self.assertTrue(len(highlighting[id]) == 2,
            ("There should be two documents highlighted, "
             "id:%s, highlighting:%s" % (id, highlighting)))

        for field in fields_to_highlight:
            self.assertTrue(field in highlighting[id],
                "%s should be highlighted, highlighting:%s" % (
                field,highlighting))

            # user_id and data are equal
            content = parseString(highlighting[id][field][0])
            highlighting_value = content.firstChild.firstChild.nodeValue
            self.assertEquals(highlighting_value, data,
                "Highlighting didn't return %s value, expected:%s, got:%s" % (
                    field, data, highlighting_value))

    def test_raw_query(self):
        """ Try to send a raw query, in Solr format.
        """
        id = get_rand_string()
        prefix = get_rand_string()

        # Same data and user_id
        user_id = data = prefix + "-" + get_rand_string()

        self.add(id=id, user_id=user_id, data=data)
        self.conn.commit()

        # Issue a prefix query, return data only (which should be equal
        # to user_id).
        response = self.raw_query(
            self.conn, q="user_id:%s*" % prefix, fl="data")

        # raw_query returns a string
        xml = parseString(response)

        doc_elem = xml.getElementsByTagName("doc")

        self.assertEquals(len(doc_elem), 1,
            "raw_query didn't return the document, id:%s, the response is:%s" %
                (id, repr(response)))

        query_data = doc_elem[0].firstChild.firstChild.nodeValue

        self.assertEquals(query_data, data,
            ("raw_query returned wrong value for data field, "
            "expected %s, got:%s" % (data, query_data)))

    def test_query_sort_default_sort_order(self):
        """ Test whether sorting works (using default, ascending, sort order).
        """
        doc_count = 10
        prefix = get_rand_string()

        data = [prefix + "-" + str(x) for x in range(10)]

        # Same user_id for all documents
        user_id = get_rand_string()

        for datum in data:
            self.add(id=get_rand_string(), user_id=user_id, data=datum)
        self.conn.commit()

        results = self.query(
            self.conn, q="user_id:" + user_id, sort="data").results

        self.assertEquals(len(results), doc_count,
            "There should be %d documents returned, got:%d, results:%s" % (
                doc_count, len(results), results))

        query_data = [doc["data"] for doc in results]

        for idx, datum in enumerate(sorted(data)):
            self.assertEquals(datum, query_data[idx],
                "Expected %s instead of %s on position %s in query_data:%s" % (
                    datum, query_data[idx], idx, query_data))

    def test_query_sort_nondefault_sort_order(self):
        """ Test sorting (using non-default, descending, sort order).
        """
        doc_count = 10
        prefix = get_rand_string()

        data = [prefix + "-" + str(x) for x in range(10)]

        # Same user_id for all documents
        user_id = get_rand_string()

        for datum in data:
            self.add(id=get_rand_string(), user_id=user_id, data=datum)
        self.conn.commit()

        results = self.query(self.conn, q="user_id:" + user_id, sort="data",
            sort_order="desc").results

        self.assertEquals(len(results), doc_count,
            "There should be %d documents returned, got:%d, results:%s" % (
                doc_count, len(results), results))

        query_data = [doc["data"] for doc in results]

        for idx, datum in enumerate(reversed(sorted(data))):
            self.assertEquals(datum, query_data[idx],
                "Expected %s instead of %s on position %s in query_data:%s" % (
                    datum, query_data[idx], idx, query_data))

    def test_query_sort_complex_sort_order(self):
        """ Test sorting (using non-default, descending, sort order).
        """
        doc_count = 10
        prefix = get_rand_string()

        data = [prefix + "-" + str(x) for x in range(5)]

        # Two user ids
        user_ids = [get_rand_string(), get_rand_string()]
        # We sort 'em
        user_ids.sort()

        for user_id in user_ids:
            for datum in data:
                self.add(id=get_rand_string(), user_id=user_id, data=datum)
        self.conn.commit()

        results = self.query(self.conn, 
            q="user_id:%s OR user_id:%s" % (user_ids[0], user_ids[1]),
            sort=["user_id asc", "data desc"]).results

        self.assertEquals(len(results), doc_count,
            "There should be %d documents returned, got:%d, results:%s" % (
                doc_count, len(results), results))

        data.reverse()
        # I'm not entirely sure wheter Python 2.3 supports this
        # expected = [(a,b) for a in user_ids for b in data]
        # If it does substitute to below
        expected = []
        for user_id in user_ids:
            for d in data:
                expected.append((user_id, d))

        for idx, result in enumerate(results):
            params =  (result['user_id'], result['data']) + expected[idx] + \
                (idx, results, expected)
            self.assertEquals(
                (result['user_id'], result['data']),
                expected[idx],
                ("Expected %s, %s instead of %s, %s at position %s"
                " in %s (expected %s)") % params
            )

    def test_date(self):
        id = data = user_id = get_rand_string()
        date = datetime.date(1969, 5, 28)
        self.add(id=id, user_id=user_id, data=data, creation_time=date)
        self.conn.commit()
        results = self.query(self.conn, "id:%s" % id).results
        self.assertEqual(len(results), 1)
        self.assertTrue(isinstance(results[0]['creation_time'],
                                   datetime.datetime))
        self.assertEqual(str(results[0]['creation_time']),
                         '1969-05-28 00:00:00+00:00')

    def test_datetime_utc(self):
        id = data = user_id = get_rand_string()
        dt = datetime.datetime(
            1969, 5, 28, 12, 24, 42, tzinfo=solr.core.UTC())
        self.add(id=id, user_id=user_id, data=data, creation_time=dt)
        self.conn.commit()
        results = self.query(self.conn, "id:%s" % id).results
        self.assertEqual(len(results), 1)
        self.assertTrue(isinstance(results[0]['creation_time'],
                                   datetime.datetime))
        self.assertEqual(str(results[0]['creation_time']),
                         '1969-05-28 12:24:42+00:00')

    def test_multi_date(self):
        id = data = user_id = get_rand_string()
        dates = [datetime.date(1969, 5, 28), datetime.date(2009, 1, 30)]
        self.add(id=id, user_id=user_id, data=data, multi_time=dates)
        self.conn.commit()
        results = self.query(self.conn, "id:%s" % id).results
        self.assertEqual(len(results), 1)
        times = results[0]['multi_time']
        self.assertEqual(len(times), 2)
        self.assertTrue(isinstance(times[0], datetime.datetime))
        self.assertEqual(str(times[0]), '1969-05-28 00:00:00+00:00')
        self.assertTrue(isinstance(times[1], datetime.datetime))
        self.assertEqual(str(times[1]), '2009-01-30 00:00:00+00:00')

    def test_query_date_field_parsing_subseconds(self):
        """ Test whether date fields with subsecond precision are being
        handled correctly. See issue #3 for more info.
        """
        id = data = user_id = get_rand_string()
        year, month, day  = "2008", "07", "23"
        hour, minute, second, microsecond = "14", "47", "09", "123"

        timestamp = "%s-%s-%sT%s:%s:%s.%sZ" % (year, month, day, hour, minute,
                                                second, microsecond)

        self.add(id=id, user_id=user_id, data=data, creation_time=timestamp)
        self.conn.commit()

        results = self.query(self.conn, "id:" + id).results

        self.assertEquals(len(results), 1,
            "Expected 1 document, got:%d documents" % (len(results)))

        results = results[0]

        self.assertTrue("creation_time" in results,
            "Query didn't return creation_time field. results:%s" % (results))

        query_timestamp = results["creation_time"]

        self.assertTrue(int(year) == query_timestamp.year)
        self.assertTrue(int(month) == query_timestamp.month)
        self.assertTrue(int(day) == query_timestamp.day)
        self.assertTrue(int(hour) == query_timestamp.hour)
        self.assertTrue(int(minute) == query_timestamp.minute)
        self.assertTrue(int(second) == query_timestamp.second)

        # solr.utc_from_string adds "000" which doesn't seem to be actually
        # needed but removing it would break the backward compatibility with
        # solrpy 0.1
        self.assertTrue(
            str(query_timestamp.microsecond).startswith(microsecond))
        self.assertTrue(query_timestamp.microsecond/int(microsecond) == 1000)

    def test_facet_field(self):
        """ Test basic facet fields and make sure they are included in the
        response properly """

        self.conn.delete_query('id:[* TO *]')
        self.conn.optimize()

        for i in range(0,12):
            self.add(id=i,user_id=i%3,data=get_rand_string(),num=10)

        self.conn.optimize()

        results = self.query(self.conn, 'id:[* TO *]',facet='true',
                                  facet_field=['user_id','num'])

        self.assertTrue(hasattr(results,'facet_counts'))
        self.assertTrue(u'facet_fields' in results.facet_counts)
        self.assertTrue(u'num' in results.facet_counts[u'facet_fields'])
        self.assertTrue(u'user_id' in results.facet_counts[u'facet_fields'])
        self.assertEqual(len(results.facet_counts[u'facet_fields'][u'num']),1)
        self.assertEqual(
            len(results.facet_counts[u'facet_fields'][u'user_id']),
            3)
        self.assertEqual(
            results.facet_counts[u'facet_fields'][u'num'],
            {u'10':12})
        self.assertEqual(
            results.facet_counts[u'facet_fields'][u'user_id'],
            {u'0':4,u'1':4,u'2':4})


    # Exception tests

    def test_exception_highlight_true_no_fields(self):
        """ A ValueError should be raised when querying and highlight is True
        but no fields are given.
        """
        self.assertRaises(ValueError, self.query, self.conn, "id:" + "abc",
                            **{"highlight":True})

    def test_exception_invalid_sort_order(self):
        """ A ValueError should be raised when sort_order is other
        than "asc" or "desc".
        """
        self.assertRaises(ValueError, self.query, self.conn, "id:" + "abc",
                          **{"sort":"id", "sort_order":"invalid_sort_order"})


class EmptyResponse(object):

    _empty_results = '''\
<response> 
<lst name="responseHeader"> 
 <int name="status">0</int> 
 <int name="QTime">2</int> 
 <lst name="params"> 
  <str name="q">keyword:ttestdocument</str> 
  <str name="wt">standard</str> 
 </lst> 
</lst> 
<result name="response" numFound="0" start="0"/> 
</response> 
'''

    _headers = {
        "server": "Apache-Coyote/1.1",
        "content-type": "text/xml;charset=UTF-8",
        "content-length": "307",
        "connection": "close",
        }

    getheaders = _headers.items
    status = 200
    reason = "Ok"
    version = 11

    def getheader(self, name, default=None):
        return self._headers.get(name.lower, default)

    def read(self):
        return self._empty_results


class TestSolrConnectionSearchHandler(SolrConnectionTestCase):

    def new_connection(self):
        # Whenever we create a connection, we want to hook the _post
        # method to capture information about the request, and suppress
        # sending it to the server.

        def post(selector, body, headers):
            self.request_selector = selector
            self.request_body = body
            return EmptyResponse()

        conn = super(TestSolrConnectionSearchHandler, self).new_connection()
        conn._post = post
        return conn

    def test_select_request(self):
        conn = self.new_connection()
        conn.select("id:foobar", score=False)
        self.assertEqual(self.request_selector, SOLR_PATH + "/select")
        self.assertEqual(self.request_body,
                         "q=id%3Afoobar&version=2.2&fl=%2A&wt=standard")

    def test_select_raw_request(self):
        conn = self.new_connection()
        conn.select.raw(q="id:foobar")
        self.assertEqual(self.request_selector, SOLR_PATH + "/select")
        self.assertEqual(self.request_body, "q=id%3Afoobar")

    def test_alternate_request(self):
        conn = self.new_connection()
        alternate = solr.SearchHandler(conn, "/alternate/path")
        alternate("id:foobar", score=False)
        self.assertEqual(self.request_selector, SOLR_PATH + "/alternate/path")
        self.assertEqual(self.request_body,
                         "q=id%3Afoobar&version=2.2&fl=%2A&wt=standard")

    def test_alternate_raw_request(self):
        conn = self.new_connection()
        alternate = solr.SearchHandler(conn, "/alternate/path")
        alternate.raw(q="id:foobar")
        self.assertEqual(self.request_selector, SOLR_PATH + "/alternate/path")
        self.assertEqual(self.request_body, "q=id%3Afoobar")


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
        self.assertEquals(len(results), 0,
            ("Changes to index shouldn't be visible without commiting, "
             "results:%s" % (repr(results))))

        # Now commit the changes and check whether it's been successful.
        self.conn.commit()

        results = self.query(self.conn, "id:" + id).results
        self.assertEquals(len(results), 1,
            "No documents returned, results:%s" % (repr(results)))

    def test_optimize(self):
        """ Check whether optimizing works.
        """
        # Same id, data and user_id
        id = get_rand_string()
        self.add(id=id, user_id=id, data=id)

        # Make sure the changes weren't commited.
        results = self.query(self.conn, "id:" + id).results
        self.assertEquals(len(results), 0,
            ("Changes to index shouldn't be visible without call"
             "to optimize first, results:%s" % (repr(results))))

        # Optimizing commits the changes
        self.conn.optimize()

        results = self.query(self.conn, "id:" + id).results
        self.assertEquals(len(results), 1,
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
        self.assertEquals(len(results), 0,
            ("Changes to index shouldn't be visible without commiting, "
             "results:%s" % (repr(results))))

        # Optimizing commits the changes
        self.conn.commit(_optimize=True)

        results = self.query(self.conn, "id:" + id).results
        self.assertEquals(len(results), 1,
            "No documents returned, results:%s" % (repr(results)))


class TestResponse(SolrConnectionTestCase):

    def setUp(self):
        super(TestResponse, self).setUp()
        self.conn = self.new_connection()

    def test_response_attributes(self):
        """ Make sure Response objects have all the documented attributes,
        and also checks that they are of the correct type
        """
        # Same id, data and user_id
        id = get_rand_string()
        self.conn.add(id=id, user_id=id, data=id)
        self.conn.commit()

        response = self.query(self.conn, q="id:" + id)
        # here we also check the type of the attribute
        expected_attrs = {
            "numFound": long,
            "start": long,
            "maxScore": float,
            "header": dict,
            }

        for attr, attr_type in expected_attrs.items():
            self.assertTrue(hasattr(response, attr),
                "Attribute %s not found in response. id:%s" % (attr, id))

            value = getattr(response, attr)
            # check type
            self.assertTrue(isinstance(value, attr_type),
                "Attribute %s has wrong type. id:%s" % (attr,id))


class TestPaginator(SolrConnectionTestCase):
    # This only needs to use one of the connection classes since the
    # paginator relies only on the results, not the connection that
    # produced them.

    def setUp(self):
        super(TestPaginator, self).setUp()
        self.conn = self.new_connection()
        self.conn.delete_query('*:*')
        for i in range(0,15):
            self.conn.add(id=i, data='data_%02i' % i)
        self.conn.commit()
        self.result = self.query(
            self.conn, '*:*', sort='data', sort_order='desc')

    def test_num_pages(self):
        """ Check the number of pages reported by the paginator """
        paginator = solr.SolrPaginator(self.result)
        self.assertEqual(paginator.num_pages, 2)

    def test_count(self):
        """ Check the result count reported by the paginator """
        paginator = solr.SolrPaginator(self.result)
        self.assertEqual(paginator.count, 15)

    def test_page_range(self):
        """ Check the page range returned by the paginator """
        paginator = solr.SolrPaginator(self.result)
        self.assertEqual(paginator.page_range, [1,2])

    def test_default_page_size(self):
        """ Test invalid/impproper default page sizes for paginator """
        self.assertRaises(ValueError,solr.SolrPaginator,self.result,'asdf')
        self.assertRaises(ValueError,solr.SolrPaginator,self.result,5)

    def test_page_one(self):
        """ Test the first page from a paginator """
        paginator = solr.SolrPaginator(self.result)
        page = paginator.page(1)
        self.assertEqual(page.has_other_pages(), True)
        self.assertEqual(page.has_next(), True)
        self.assertEqual(page.has_previous(), False)
        self.assertEqual(page.next_page_number(), 2)
        self.assertEqual(page.start_index(), 0)
        self.assertEqual(page.end_index(), 9)
        self.assertEqual(len(page.object_list), 10)
        self.assertEqual(page.object_list[0]['data'], 'data_14')

    def test_page_two(self):
        """ Test the second/last page from a paginator """
        paginator = solr.SolrPaginator(self.result,default_page_size=10)
        page = paginator.page(2)
        self.assertEqual(page.has_other_pages(), True)
        self.assertEqual(page.has_next(), False)
        self.assertEqual(page.has_previous(), True)
        self.assertEqual(page.previous_page_number(), 1)
        self.assertEqual(page.start_index(), 10)
        self.assertEqual(page.end_index(), 14)
        self.assertEqual(len(page.object_list), 5)
        self.assertEqual(page.object_list[0]['data'], 'data_04')

    def test_unicode_query(self):
        """ Test for unicode support in subsequent paginator queries """
        chinese_data = '\xe6\xb3\xb0\xe5\x9b\xbd'.decode('utf-8')
        self.conn.add(id=100, data=chinese_data)
        self.conn.commit()
        result = self.query(self.conn, chinese_data.encode('utf-8'))
        paginator = solr.SolrPaginator(result, default_page_size=10)
        try:
            paginator.page(1)
        except solr.SolrException:
            self.fail('Unicode not encoded correctly in paginator')


class ThrowBadStatusLineExceptions(object):

    def __init__(self, conn, max=None):
        self.calls = 0
        self.max = max
        self.wrap = conn.conn.request
        conn.conn.request = self

    def __call__(self, *args, **kwargs):
        self.calls += 1
        if self.max is None or self.calls <= self.max:
            raise httplib.BadStatusLine('Dummy status line exception')
        return self.wrap(*args, **kwargs)


class TestRetries(SolrConnectionTestCase):

    def setUp(self):
        super(TestRetries, self).setUp()
        self.conn = self.new_connection()

    def test_badstatusline(self):
        """ Replace the low level connection request with a dummy function that
        raises an exception. Verify that the request method is called 4 times
        and still raises the exception """
        t = ThrowBadStatusLineExceptions(self.conn)

        self.assertRaises(httplib.BadStatusLine, self.query,
                          self.conn, "user_id:12345")

        self.assertEqual(t.calls, 4)

    def test_success_after_failure(self):
        """ Wrap the calls the the lower level request and throw only 1
        exception and then proceed normally. It should result in two calls to
        self.conn.conn.request. """
        t = ThrowBadStatusLineExceptions(self.conn, max=1)

        self.query(self.conn, "user_id:12345")

        self.assertEqual(t.calls, 2)


# Now let's do the same thing again, but with the solr.Solr connection.
# Some tests are overridden, and many more are added.

class TestSolrHTTPConnection(SolrBased, TestHTTPConnection):
    pass

class TestSolrAddingDocuments(SolrBased, RequestTracking, TestAddingDocuments):

    # Override tests that are affected by API differences:

    def test_add_one_document_implicit_commit(self):
        """ Try to add one document and commit changes in one operation.
        """
        doc = get_rand_userdoc()
        # Add with commit:
        self.conn.add(doc, commit=True)
        self.assertEqual(self.selector(), "/update?commit=true")
        self.assertEqual(self.method(), "POST")
        self.check_added(doc)

    def test_add_many_implicit_commit(self):
        """ Try to add more than one document and commit changes,
        all in one operation.
        """
        doc_count = 10
        documents = [get_rand_userdoc() for x in range(doc_count)]

        # Pass in the commit flag.
        self.conn.add_many(documents, commit=True)
        self.assertEqual(self.selector(), "/update?commit=true")
        self.assertEqual(self.method(), "POST")
        self.check_added(docs=documents)

    # Additional tests related to the solr.Solr API:

    def test_add_inline_optimize(self):
        """ Try to add one document and commit changes, with optimization,
        in one operation.
        """
        doc = get_rand_userdoc()
        # Add with optimize:
        self.conn.add(doc, optimize=True)
        self.assertEqual(self.selector(), "/update?optimize=true")
        self.assertEqual(self.method(), "POST")
        self.check_added(doc)

    def test_add_many_inline_optimize(self):
        """ Try to add more than one document and commit changes,
        with optimization, all in one operation.
        """
        doc_count = 10
        documents = [get_rand_userdoc() for x in range(doc_count)]

        # Pass in the commit flag.
        self.conn.add_many(documents, optimize=True)
        self.assertEqual(self.selector(), "/update?optimize=true")
        self.assertEqual(self.method(), "POST")
        self.check_added(docs=documents)

    def test_add_noflush(self):
        doc = get_rand_userdoc()
        # Add with commit:
        self.conn.add(doc, commit=True, wait_flush=False)
        self.assertEqual(
            self.selector(),
            "/update?commit=true&waitFlush=false&waitSearcher=false")
        # Can't verify the add since we said we weren't going to wait
        # for the flush.
        self.assert_("<add>" in self.postbody())

    def test_add_nosearcher(self):
        doc = get_rand_userdoc()
        # Add with commit:
        self.conn.add(doc, commit=True, wait_searcher=False)
        self.assertEqual(
            self.selector(),
            "/update?commit=true&waitSearcher=false")
        # Can't verify the add since we said we weren't going to wait
        # for a searcher.
        self.assert_("<add>" in self.postbody())

    def test_add_waitflush_without_commit(self):
        doc = get_rand_userdoc()
        self.assertRaises(TypeError, self.conn.add, doc, wait_flush=False)

    def test_add_waitsearcher_without_commit(self):
        doc = get_rand_userdoc()
        self.assertRaises(TypeError, self.conn.add, doc, wait_searcher=False)

    def test_add_many_commit_noflush(self):
        documents = [get_rand_userdoc() for i in range(3)]
        # Add with optimize:
        self.conn.add_many(documents, commit=True, wait_flush=False)
        self.assertEqual(
            self.selector(),
            "/update?commit=true&waitFlush=false&waitSearcher=false")
        # Can't verify the add since we said we weren't going to wait
        # for the flush.
        self.assert_("<add>" in self.postbody())

    def test_add_many_commit_nosearcher(self):
        documents = [get_rand_userdoc() for i in range(3)]
        # Add with optimize:
        self.conn.add_many(documents, commit=True, wait_searcher=False)
        self.assertEqual(
            self.selector(),
            "/update?commit=true&waitSearcher=false")
        # Can't verify the add since we said we weren't going to wait
        # for a searcher.
        self.assert_("<add>" in self.postbody())

    def test_add_many_waitflush_without_commit(self):
        docs = [get_rand_userdoc(), get_rand_userdoc()]
        self.assertRaises(
            TypeError, self.conn.add_many, docs, wait_flush=False)

    def test_add_many_waitsearcher_without_commit(self):
        docs = [get_rand_userdoc(), get_rand_userdoc()]
        self.assertRaises(
            TypeError, self.conn.add_many, docs, wait_searcher=False)

class TestSolrUpdatingDocuments(SolrBased, TestUpdatingDocuments):
    pass

class TestSolrDocumentDeletion(SolrBased, RequestTracking,
                               TestDocumentsDeletion):

    def test_delete_one_document_by_query_inline_commit(self, what="commit"):
        """ Try to delete a single document matching a given query.
        """
        doc = get_rand_userdoc()
        self.conn.add(doc, commit=True)
        self.check_added(doc)
        id = doc["id"]

        self.conn.delete_query("id:" + id, **{what: True})
        self.check_removed(doc)
        results = self.query(self.conn, "id:" + id).results
        self.assertEquals(len(results), 0,
            "Document (id:%s) should've been deleted" % id)

    def test_delete_many_documents_by_query_inline_commit(self, what="commit"):
        """ Try to delete many documents matching a given query.
        """
        doc_count = 10
        # Same user ID will be used for all documents.
        user_id = get_rand_string()
        documents = [get_rand_userdoc(user_id=user_id)
                     for i in range(doc_count)]
        self.conn.add_many(documents, commit=True)

        # Make sure the docs were in fact added.
        results = self.query(self.conn, "user_id:" + user_id).results
        self.assertEquals(
            len(results), doc_count,
            ("There should be %d documents for user_id:%s"
             % (doc_count, user_id)))

        # Now delete documents and commit the changes
        self.conn.delete_query("user_id:" + user_id, **{what: True})

        results = self.query(self.conn, "user_id:" + user_id).results
        self.assertEquals(len(results), 0,
            "There should be no documents for user_id:%s" % (user_id))
        self.check_removed(docs=documents)

    def test_delete_many_inline_commit(self, what="commit"):
        """ Delete many documents in one pass.
        """
        doc_count = 10
        ids = [get_rand_string() for x in range(doc_count)]
        # Same data and user_id for all documents
        data = get_rand_string()
        documents = [dict(id=id, user_id=data, data=data) for id in ids]
        self.conn.add_many(documents, commit=True)

        # Make sure they've been added
        self.check_added(docs=documents)

        # Delete documents by their ID and commit changes
        self.conn.delete_many(ids, **{what: True})

        # Make sure they've been deleted
        self.check_removed(docs=documents)

    def test_delete_by_unique_key_inline_commit(self, what="commit"):
        """ Delete a document by using its unique key.
        """
        id = get_rand_string()
        # Same data and user_id
        user_id = get_rand_string()
        doc = dict(id=id, user_id=user_id, data=user_id)
        self.conn.add(doc, commit=True)

        # Make sure it's been added
        results = self.query(self.conn, "id:" + id).results

        # Make sure the docs were in fact added.
        self.assertEquals(len(results), 1,
            "No results returned for query id:%s"% (id))

        # Delete the document and make sure it's no longer in the index
        self.conn.delete(id, **{what: True})
        self.check_removed(doc)

    def test_delete_noflush(self):
        doc = get_rand_userdoc()
        # Add with commit:
        self.conn.add(doc, commit=True)
        self.check_added(doc)
        self.conn.delete(doc["id"], commit=True, wait_flush=False)
        self.assertEqual(
            self.selector(),
            "/update?commit=true&waitFlush=false&waitSearcher=false")
        # Can't verify the add since we said we weren't going to wait
        # for the flush.
        self.assert_("<delete>" in self.postbody())

    def test_delete_nosearcher(self):
        doc = get_rand_userdoc()
        # Add with commit:
        self.conn.add(doc, commit=True)
        self.check_added(doc)
        self.conn.delete(doc["id"], commit=True, wait_searcher=False)
        self.assertEqual(
            self.selector(),
            "/update?commit=true&waitSearcher=false")
        # Can't verify the add since we said we weren't going to wait
        # for the flush.
        self.assert_("<delete>" in self.postbody())

    def test_delete_waitflush_without_commit(self):
        doc = get_rand_userdoc()
        self.conn.add(doc, commit=True)
        self.assertRaises(
            TypeError, self.conn.delete, doc["id"], wait_flush=False)

    def test_delete_waitsearcher_without_commit(self):
        doc = get_rand_userdoc()
        self.conn.add(doc, commit=True)
        self.assertRaises(
            TypeError, self.conn.delete, doc["id"], wait_searcher=False)

    def test_delete_one_document_by_query_inline_optimize(self):
        self.test_delete_one_document_by_query_inline_commit(what="optimize")

    def test_delete_many_documents_by_query_inline_optimize(self):
        self.test_delete_many_documents_by_query_inline_commit(what="optimize")

    def test_delete_many_inline_optimize(self):
        self.test_delete_many_inline_commit(what="optimize")

    def test_delete_by_unique_key_inline_optimize(self):
        self.test_delete_by_unique_key_inline_commit(what="optimize")

    def test_delete_many_waitflush_without_commit(self):
        documents = [get_rand_userdoc(), get_rand_userdoc()]
        self.conn.add_many(documents, commit=True)
        ids = [doc["id"] for doc in documents]
        self.assertRaises(
            TypeError, self.conn.delete_many, ids, wait_flush=False)

    def test_delete_many_waitsearcher_without_commit(self):
        documents = [get_rand_userdoc(), get_rand_userdoc()]
        self.conn.add_many(documents, commit=True)
        ids = [doc["id"] for doc in documents]
        self.assertRaises(
            TypeError, self.conn.delete_many, ids, wait_searcher=False)

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

        # Let's combine the three flavors of the delete method, just to
        # make sure it all works together:
        self.conn.delete(id=doc1["id"], ids=[doc2["id"], doc3["id"]],
                         queries=["user_id:" + user_id],
                         commit=True)

        self.check_removed(docs=alldocs)


class TestSolrQuerying(SolrBased, TestQuerying):
    pass

class TestSolrSearchHandler(SolrBased, TestSolrConnectionSearchHandler):
    pass

class TestSolrCommitingOptimizing(SolrBased, TestCommitingOptimizing):
    pass

class TestSolrRetries(SolrBased, TestRetries):
    pass


if __name__ == "__main__":
    unittest.main()
