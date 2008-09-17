# -*- coding: utf-8 -*-

""" Test cases for Python Solr client. Meant to be run against Solr 1.2+. 
""" 

# stdlib
import time
import socket
import unittest
from string import digits
from random import choice
from xml.dom.minidom import parseString

# solrpy
from solr import SolrConnection

SOLR_PATH = "/solr"
SOLR_HOST = "localhost"
SOLR_PORT_HTTP = "8983"
SOLR_PORT_HTTPS = "8943"
SOLR_HTTP = "http://" + SOLR_HOST + ":" + SOLR_PORT_HTTP  + SOLR_PATH
SOLR_HTTPS = "https://" + SOLR_HOST + ":" + SOLR_PORT_HTTPS + SOLR_PATH

        
def get_rand_string():
    return "".join(choice(digits)  for x in range(12))

class TestHTTPConnection(unittest.TestCase):
    
    def test_connect(self):
        """ Check if we're really get connected to Solr through HTTP.
        """
        self.conn = SolrConnection(SOLR_HTTP)
        
        try:
            self.conn.conn.request("GET", SOLR_PATH)
        except socket.error, e:
            self.fail("Connection to %s failed" % (SOLR_HTTP))
            
        status = self.conn.conn.getresponse().status
        self.assertEquals(status, 302, "Expected FOUND (302), got: %d" % status)
        
    def test_close_connection(self):
        """ Make sure connections to Solr are being closed properly.
        """
        self.conn2 = SolrConnection(SOLR_HTTP)
        self.conn2.conn.request("GET", SOLR_PATH)
        self.conn2.close()
        
        # Closing the Solr connection should close the underlying 
        # HTTPConnection's socket.
        self.assertEquals(self.conn2.conn.sock, None, "Connection not closed")
        
    def tearDown(self):
        # Connections may as well not exist.
        for conn in ["conn", "conn2"]:
            if hasattr(self, conn):
                getattr(self, conn).close()
        
class TestAddingDocuments(unittest.TestCase):
    
    def setUp(self):
        self.conn = SolrConnection(SOLR_HTTP)
        
    def test_add_one_document(self):
        """ Try to add one document.
        """
        user_id = get_rand_string()
        data = get_rand_string()
        id = get_rand_string()
        
        doc = {}
        doc["user_id"] = user_id
        doc["data"] = data
        doc["id"] = id
        
        self.conn.add(**doc)
        self.conn.commit()
        results = self.conn.query("id:" + id).results
        
        self.assertEquals(len(results), 1, 
            "Could not find expected data (id:%s)" % id)
        
        doc = results[0]
        self.assertEquals(doc["user_id"], user_id)
        self.assertEquals(doc["data"], data)
        
    def test_add_one_document_implicit_commit(self):
        """ Try to add one document and commit changes in one operation.
        """
        
        # That one fails in r5 (<commit/> must be made on its own)
        
        user_id = get_rand_string()
        data = get_rand_string()
        id = get_rand_string()
        
        doc = {}
        doc["user_id"] = user_id
        doc["data"] = data
        doc["id"] = id
        
        # Commit the changes
        self.conn.add(True, **doc)
        results = self.conn.query("id:" + id).results
        
        self.assertEquals(len(results), 1, 
            "Could not find expected data (id:%s)" % id)
        
        doc = results[0]
        self.assertEquals(doc["user_id"], user_id)
        self.assertEquals(doc["data"], data)
        
    def test_add_no_commit(self):
        """ Add one document without commiting the operation.
        """
        user_id = get_rand_string()
        data = get_rand_string()
        id = get_rand_string()
        
        doc = {}
        doc["user_id"] = user_id
        doc["data"] = data
        doc["id"] = id
        
        self.conn.add(**doc)
        results = self.conn.query("user_id:" + user_id).results
        self.assertEquals(len(results), 0, 
            "Document (id:%s) shouldn't have been fetched" % (id))
            
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
            res = self.conn.query("id:" + id).results
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
        """ Try to add more than one document and commit changes, 
        all in one operation.
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
            res = self.conn.query("id:" + id).results
            if not res:
                self.fail("Could not find document (id:%s)" % id)
            results.append(res[0])
            
    def test_add_many_no_commit(self):
        """ Try to add many documents in a single operation without commiting it.
        """
        doc_count = 10
        user_ids = [get_rand_string() for x in range(doc_count)]
        data =  [get_rand_string() for x in range(doc_count)]
        ids =  [get_rand_string() for x in range(doc_count)]
        documents = [dict(user_id=user_ids[x], data=data[x], id=ids[x]) 
                        for x in range(doc_count)]
        
        self.conn.add_many(documents)
        
        for user_id in user_ids:
            results = self.conn.query("user_id:" + user_id).results
            self.assertEquals(len(results), 0, 
                "Document (id:%s) shouldn't have been fetched" % (id))
                
    def test_add_unicode(self):
        """ Check whether adding Unicode data actually works for single
        document.
        """
        # "bile" in Polish (UTF-8).
        data = "\xc5\xbc\xc3\xb3\xc5\x82\xc4\x87".decode("utf-8")
        user_id = get_rand_string()
        id = get_rand_string()
        
        doc = {}
        doc["user_id"] = user_id
        doc["data"] = data
        doc["id"] = id
        
        self.conn.add(**doc)
        self.conn.commit()

        results = self.conn.query("id:" + id).results
        if not results:
            self.fail("Could not find document (id:%s)" % id)
            
        query_user_id = results[0]["user_id"]
        query_data = results[0]["data"]
        query_id = results[0]["id"]
                                                                                                        
        self.assertEquals(user_id, query_user_id,
            "Invalid user_id, expected: %s, got: %s" % (user_id, query_user_id))
        self.assertEquals(data, query_data,
            "Invalid data, expected: %s, got: %s" % (repr(data), 
                                                        repr(query_data)))
        self.assertEquals(id, query_id,
            "Invalid id, expected: %s, got: %s" % (id, query_id))

    def test_add_many_unicode(self):
        """ Check correctness of handling Unicode data when adding many 
        documents.
        """
        # Some Polish characters (UTF-8)
        chars = ("\xc4\x99\xc3\xb3\xc4\x85\xc5\x9b\xc5\x82"
                 "\xc4\x98\xc3\x93\xc4\x84\xc5\x9a\xc5\x81").decode("utf-8")

        documents = []
        for char in chars:
            doc = {}
            doc["data"] = char
            doc["user_id"] = get_rand_string()
            doc["id"] = get_rand_string()
            documents.append(doc)
            
        user_ids = [doc["user_id"] for doc in documents]
        ids = [doc["id"] for doc in documents]

        self.conn.add_many(documents)
        self.conn.commit()

        results = []
        for doc in documents:
            id = doc["id"]
            res = self.conn.query("id:" + id).results
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
            
    def test_batching(self):
        """ To be done.
        """
        self.fail("To be implemented if batch updates stay in solrpy.")

    def tearDown(self):
        self.conn.close()

class TestDocumentsDeletion(unittest.TestCase):
    
    def setUp(self):
        self.conn = SolrConnection(SOLR_HTTP)
        
    def test_delete_one_document_by_query(self):
        """ Try to delete a single document matching a given query.
        """
        user_id = get_rand_string()
        data = get_rand_string()
        id = get_rand_string()
        
        doc = {}
        doc["user_id"] = user_id
        doc["data"] = data
        doc["id"] = data
        
        self.conn.add(**doc)
        self.conn.commit()
        
        results = self.conn.query("id:" + id).results
        
        self.conn.delete_query("id:" + id)
        self.conn.commit()
        
        results = self.conn.query("id:" + id).results
        self.assertEquals(len(results), 0, 
            "Document (id:%s) should've been deleted" % id)
            
    def test_delete_many_documents_by_query(self):
        """ Try to delete many documents matching a given query.
        """
        doc_count = 10
        user_id = get_rand_string() # Same user ID will be used for all documents.
        
        for x in range(doc_count):
            self.conn.add(id=get_rand_string(), data=get_rand_string(), user_id=user_id)
            
        self.conn.commit()
        results = self.conn.query("user_id:" + user_id).results
        
        # Make sure the docs were in fact added.
        self.assertEquals(len(results), doc_count,
            "There should be %d documents for user_id:%s" % (doc_count, user_id))
        
        # Now delete documents and commit the changes
        self.conn.delete_query("user_id:" + user_id)
        self.conn.commit()
        
        results = self.conn.query("user_id:" + user_id).results
        
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
            self.conn.add(id=id, data=data, user_id=user_id)
        self.conn.commit()
        
        # Make sure they've been added
        for id in ids:
            results = self.conn.query("id:" + id).results
            self.assertEquals(len(results), 1,
                "Document (id:%s) should've been added to index" % id)
                
        # Delete documents by their ID and commit changes
        self.conn.delete_many(ids)
        self.conn.commit()
        
        # Make sure they've been deleted
        for id in ids:
            results = self.conn.query("id:" + id).results
            self.assertEquals(len(results), 0,
                "Document (id:%s) should've been deleted from index" % id)
                
    def test_delete_by_unique_key(self):
        """ Delete a document by using its unique key (as defined in Solr's schema).
        """
        id = get_rand_string()
        
        # Same data and user_id 
        user_id = data = get_rand_string()

        self.conn.add(id=id, user_id=user_id, data=data)
        self.conn.commit()
        
        # Make sure it's been added
        results = self.conn.query("id:" + id).results
        
        # Make sure the docs were in fact added.
        self.assertEquals(len(results), 1, 
            "No results returned for query id:%s"% (id))
            
        # Delete the document and make sure it's no longer in the index
        self.conn.delete(id)
        self.conn.commit()
        results = self.conn.query("id:" + id).results
        self.assertEquals(len(results), 0, 
            "Document (id:%s) should've been deleted"% (id))
        
    def tearDown(self):
        self.conn.close()
        
class TestQuerying(unittest.TestCase):
    
    def setUp(self):
        self.conn = SolrConnection(SOLR_HTTP)
        
    def test_query_string(self):
        """ Get documents (all default fields) by a simple query.
        """
        doc_count = 10
        ids = [get_rand_string() for x in range(doc_count)]
        
        # Same user_id and data for all documents
        user_id = get_rand_string()
        data = get_rand_string()
        
        for id in ids:
            self.conn.add(id=id, user_id=user_id, data=data)
        self.conn.commit()
        
        results = self.conn.query("user_id:" + user_id).results
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
            self.conn.add(id=ids[idx], user_id=user_ids[idx], data=data)
        self.conn.commit()
        
        # We want to return only the "id" field
        results = self.conn.query("data:" + data, fields=field_to_return).results
        self.assertEquals(len(results), doc_count, 
            "There should be exactly %d documents returned, got: %d" % (
                doc_count, len(results)))
                
        # Use the symmetric difference to check whether all IDs have been 
        # fetched by a query.
            
        query_ids = [doc[field_to_return] for doc in results]
        ids_symdiff = set(ids) ^ set(query_ids)
        
        self.assertEquals(ids_symdiff, set([]),
            "Query didn't return expected fields (difference:%s)" % (ids_symdiff))
            
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
                    
            self.assertEquals(fields[0], "score",
                "Query returned some other fields then %s and score, result:%s" % (
                    field_to_return,result))
                    
    def test_query_score(self):
        """ Make sure the score field is returned and is a float instance.
        """
        id = get_rand_string()
        
        # Same data and user_id 
        user_id = data = get_rand_string()

        self.conn.add(id=id, user_id=user_id, data=data)
        self.conn.commit()
        
        results = self.conn.query("id:" + id).results
        self.assertEquals(len(results), 1, 
            "No documents fetched, expected id:%s" % (id))
            
        doc = results[0]

        self.assertTrue("score" in doc, "No score returned, doc:%s" % repr(doc))
        self.assertTrue(isinstance(doc["score"], float),
            "Score should be a float instance, doc:%s" % repr(doc))
            
    def test_query_no_score(self):
        """ Check whether the score is not being returned when explicitly
        told not to do so.
        """
        id = get_rand_string()
        
        # Same data and user_id 
        user_id = data = get_rand_string()

        self.conn.add(id=id, user_id=user_id, data=data)
        self.conn.commit()
        
        results = self.conn.query("id:" + id, score=False).results
        
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

        self.conn.add(id=id, user_id=user_id, data=data)
        self.conn.commit()
        
        # Specify the fields to highlight as a string
        response = self.conn.query("id:" + id, highlight=True, fields="id")
        
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
        response = self.conn.query("id:" + id, highlight=True, fields=["id"])
        
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
        
        self.conn.add(id=id, user_id=user_id, data=data)
        self.conn.commit()
        
        # Specify the fields to highlight as a list of fields
        response = self.conn.query("user_id:" + user_id, 
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

        self.conn.add(id=id, user_id=user_id, data=data)
        self.conn.commit()
        
        # Issue a prefix query, return data only (which should be equal 
        # to user_id).
        response = self.conn.raw_query(q="user_id:%s*" % prefix, fl="data")
        
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
        field_to_be_sorted_by = "data"
        prefix = get_rand_string()
        
        data = [prefix + "-" + str(x) for x in range(10)] 
        
        # Same user_id for all documents
        user_id = get_rand_string()
        
        for datum in data:
            self.conn.add(id=get_rand_string(), user_id=user_id, data=datum)
        self.conn.commit()
        
        results = self.conn.query(q="user_id:" + user_id, sort="data").results
        
        self.assertEquals(len(results), doc_count,
            "There should be %d documents returned, got:%d, results:%s" % (
                doc_count, len(results), results))
                
        query_data = [doc["data"] for doc in results]

        for idx, datum in enumerate(sorted(data)):
            self.assertEquals(datum, query_data[idx],
                "Expected %s instead of %s on position %s in query_data:%s" % (
                    datum, query_data[idx], idx, query_data))
                    
    def test_query_sort_nondefault_sort_order(self):
        """ Test whether sorting works (using non-default, descending, sort order).
        """
        doc_count = 10
        field_to_be_sorted_by = "data"
        prefix = get_rand_string()
        
        data = [prefix + "-" + str(x) for x in range(10)] 
        
        # Same user_id for all documents
        user_id = get_rand_string()
        
        for datum in data:
            self.conn.add(id=get_rand_string(), user_id=user_id, data=datum)
        self.conn.commit()
        
        results = self.conn.query(q="user_id:" + user_id, sort="data",
            sort_order="desc").results
        
        self.assertEquals(len(results), doc_count,
            "There should be %d documents returned, got:%d, results:%s" % (
                doc_count, len(results), results))
                
        query_data = [doc["data"] for doc in results]
        
        for idx, datum in enumerate(reversed(sorted(data))):
            self.assertEquals(datum, query_data[idx],
                "Expected %s instead of %s on position %s in query_data:%s" % (
                    datum, query_data[idx], idx, query_data))
        
    def test_query_date_field_parsing_subseconds(self):
        """ Test whether date fields with subsecond precision are being
        handled correctly. See issue #3 for more info.
        """
        id = data = user_id = get_rand_string()
        year, month, day  = "2008", "07", "23"
        hour, minute, second, microsecond = "14", "47", "09", "123"
        
        timestamp = "%s-%s-%sT%s:%s:%s.%sZ" % (year, month, day, hour, minute, 
                                                second, microsecond)
        
        self.conn.add(id=id, user_id=user_id, data=data, 
                        creation_time=timestamp)
        self.conn.commit()
        
        results = self.conn.query("id:" + id).results
        
        self.assertEquals(len(results), 1,
            "Expexted 1 document, got:%d documents" % (len(results)))
            
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
        self.assertTrue(str(query_timestamp.microsecond).startswith(microsecond))
        self.assertTrue(query_timestamp.microsecond/int(microsecond) == 1000)
        
    def tearDown(self):
        self.conn.close()
        
        
class TestCommitingOptimizing(unittest.TestCase):
    
    def setUp(self):
        self.conn = SolrConnection(SOLR_HTTP)
        
    def test_commit(self):
        """ Check whether commiting works.
        """
        # Same id, data and user_id
        id = data = user_id = get_rand_string()
        self.conn.add(id=id, user_id=user_id, data=data)
        
        # Make sure the changes weren't commited.
        results = self.conn.query("id:" + id).results
        self.assertEquals(len(results), 0,
            ("Changes to index shouldn't be visible without commiting, "
             "results:%s" % (repr(results))))
        
        # Now commit the changes and check whether it's been successful.     
        self.conn.commit()
        
        results = self.conn.query("id:" + id).results
        self.assertEquals(len(results), 1,
            "No documents returned, results:%s" % (repr(results)))
            
    def test_optimize(self):
        """ Check whether optimizing works.
        """
        # Same id, data and user_id
        id = data = user_id = get_rand_string()
        self.conn.add(id=id, user_id=user_id, data=data)
        
        # Make sure the changes weren't commited.
        results = self.conn.query("id:" + id).results
        self.assertEquals(len(results), 0,
            ("Changes to index shouldn't be visible without call" 
             "to optimize first, results:%s" % (repr(results))))
        
        # Optimizing commits the changes     
        self.conn.optimize()
        
        results = self.conn.query("id:" + id).results
        self.assertEquals(len(results), 1,
            "No documents returned, results:%s" % (repr(results)))
            
    def test_commit_optimize(self):
        """ Check whether commiting with an optimize flag works.
        Well, actually it's pretty hard (if possible at all) to check it
        remotely, for now, let's just check whether the changes are being
        commited.
        """
        # Same id, data and user_id
        id = data = user_id = get_rand_string()
        self.conn.add(id=id, user_id=user_id, data=data)
        
        # Make sure the changes weren't commited.
        results = self.conn.query("id:" + id).results
        self.assertEquals(len(results), 0,
            ("Changes to index shouldn't be visible without commiting, "
             "results:%s" % (repr(results))))
        
        # Optimizing commits the changes     
        self.conn.commit(_optimize=True)
        
        results = self.conn.query("id:" + id).results
        self.assertEquals(len(results), 1,
            "No documents returned, results:%s" % (repr(results)))
        
    def tearDown(self):
        self.conn.close()
        
class TestExceptions(unittest.TestCase):

    def setUp(self):
        self.conn = SolrConnection(SOLR_HTTP)
        
    def test_exception_highlight_true_no_fields(self):
        """ A ValueError should be raised when querying and highlight is True
        but no fields are given.
        """
        self.assertRaises(ValueError, self.conn.query, "id:" + "abc", 
                            **{"highlight":True})
                            
    def test_exception_invalid_sort_order(self):
        """ A ValueError should be raised when sort_order is other 
        than "asc" or "desc".
        """
        self.assertRaises(ValueError, self.conn.query, "id:" + "abc", 
                            **{"sort":"id", "sort_order":"invalid_sort_order"})

    def tearDown(self):
        self.conn.close()
        
class TestResponse(unittest.TestCase):

    def setUp(self):
        self.conn = SolrConnection(SOLR_HTTP)
   
    def test_response_attributes(self):
        """ Make sure Response objects have all the documented attributes.
        """
        # Same id, data and user_id
        id = data = user_id = get_rand_string()
        self.conn.add(id=id, user_id=user_id, data=data)
        self.conn.commit()
        
        response = self.conn.query(q="id:" + id)
        expected_attrs = ["numFound", "start", "maxScore", "header"]
        
        for attr in expected_attrs:
            self.assertTrue(attr in dir(response), 
                "Attribute %s not found in response. id:%s" % (attr, id))
                
            value = getattr(response, attr)
            self.assertTrue(bool(value), 
                "Attribute %s has no value. id:%s" % (attr,id))

    def tearDown(self):
        self.conn.close()

if __name__ == "__main__":
    unittest.main()
