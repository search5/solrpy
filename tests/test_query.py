"""Auto-split from test_all.py"""

import datetime
import unittest
from xml.dom.minidom import parseString
import solr
import solr.core
from tests.conftest import (
    SolrConnectionTestCase, RequestTracking, EmptyResponse,
    SOLR_HTTP, SOLR_PATH, get_rand_string, get_rand_userdoc,
)


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
        self.assertEqual(len(results), doc_count,
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

        self.assertEqual(ids_symdiff, set([]),
            "IDs sets differ (difference:%s)" % (ids_symdiff))

        # Now loop through results and check whether fields are okay
        for result in results:
            for id in ids:
                if result["id"] == id:
                    self.assertEqual(result["data"], data,
                        "Data differs, expected:%s, got:%s" % (
                            data, result["data"]))
                    self.assertEqual(result["user_id"], user_id,
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
        self.assertEqual(len(results), doc_count,
            "There should be exactly %d documents returned, got: %d" % (
                doc_count, len(results)))

        # Use the symmetric difference to check whether all IDs have been
        # fetched by a query.

        query_ids = [doc[field_to_return] for doc in results]
        ids_symdiff = set(ids) ^ set(query_ids)

        self.assertEqual(
            ids_symdiff, set([]),
            "Query didn't return expected fields (difference:%s)"
            % (ids_symdiff))

        # Make sure no other field has been returned, note: by default
        # queries also return score for each document.

        for result in results:
            fields = list(result.keys())
            fields.remove(field_to_return)

            # Now there should only a score field
            self.assertEqual(len(fields), 1,
                ("More fields returned than expected, "
                "expected:%s and score, the result is:%s)" % (
                    field_to_return,result)))

            self.assertEqual(
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
        self.assertEqual(len(results), 1,
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

        self.assertEqual(len(results), 1,
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
        self.assertEqual(highlighting_id, id,
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
        self.assertEqual(highlighting_id, id,
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
            self.assertEqual(highlighting_value, data,
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
        if self.conn.server_version >= (7, 0):
            # Solr 7+ changed wt=standard behavior; use wt=xml explicitly
            response = self.raw_query(
                self.conn, q="user_id:%s*" % prefix, fl="data", wt="xml")
        else:
            response = self.raw_query(
                self.conn, q="user_id:%s*" % prefix, fl="data")

        # raw_query returns a string — verify via XML parsing
        xml = parseString(response)
        doc_elem = xml.getElementsByTagName("doc")

        self.assertEqual(len(doc_elem), 1,
            "raw_query didn't return the document, id:%s, the response is:%s" %
                (id, repr(response)))

        # Extract field value from XML (handles both <str> and <arr><str> tags)
        data_nodes = doc_elem[0].getElementsByTagName("str")
        query_data = None
        for node in data_nodes:
            if node.firstChild:
                query_data = node.firstChild.nodeValue
                break

        self.assertEqual(query_data, data,
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

        self.assertEqual(len(results), doc_count,
            "There should be %d documents returned, got:%d, results:%s" % (
                doc_count, len(results), results))

        query_data = [doc["data"] for doc in results]

        for idx, datum in enumerate(sorted(data)):
            self.assertEqual(datum, query_data[idx],
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

        results = self.query(self.conn, q="user_id:" + user_id, sort="data_sort",
            sort_order="desc").results

        self.assertEqual(len(results), doc_count,
            "There should be %d documents returned, got:%d, results:%s" % (
                doc_count, len(results), results))

        query_data = [doc["data"] for doc in results]

        for idx, datum in enumerate(reversed(sorted(data))):
            self.assertEqual(datum, query_data[idx],
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
            sort=["user_id asc", "data_sort desc"]).results

        self.assertEqual(len(results), doc_count,
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
            self.assertEqual(
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

        self.assertEqual(len(results), 1,
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



class TestSearchHandler(SolrConnectionTestCase):

    def new_connection(self):
        # Whenever we create a connection, we want to hook the _post
        # method to capture information about the request, and suppress
        # sending it to the server.

        def post(selector, body, headers, **kw):
            self.request_selector = selector
            self.request_body = body
            return EmptyResponse()

        conn = super(TestSearchHandler, self).new_connection()
        conn._post = post
        return conn

    def test_select_request(self):
        conn = self.new_connection()
        conn.select("id:foobar", score=False)
        self.assertEqual(self.request_selector, SOLR_PATH + "/select")
        if conn.server_version >= (7, 0):
            self.assertEqual(self.request_body,
                             "q=id%3Afoobar&fl=%2A&wt=xml")
        else:
            self.assertEqual(self.request_body,
                             "q=id%3Afoobar&fl=%2A&version=2.2&wt=standard")

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
        if conn.server_version >= (7, 0):
            self.assertEqual(self.request_body,
                             "q=id%3Afoobar&fl=%2A&wt=xml")
        else:
            self.assertEqual(self.request_body,
                             "q=id%3Afoobar&fl=%2A&version=2.2&wt=standard")

    def test_alternate_raw_request(self):
        conn = self.new_connection()
        alternate = solr.SearchHandler(conn, "/alternate/path")
        alternate.raw(q="id:foobar")
        self.assertEqual(self.request_selector, SOLR_PATH + "/alternate/path")
        self.assertEqual(self.request_body, "q=id%3Afoobar")



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
        self.conn.add({'id': id, 'user_id': id, 'data': id})
        self.conn.commit()

        response = self.query(self.conn, q="id:" + id)
        # here we also check the type of the attribute
        expected_attrs = {
            "numFound": int,
            "start": int,
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

    _PREFIX = 'pag_'

    def setUp(self):
        super(TestPaginator, self).setUp()
        self.conn = self.new_connection()
        # Clean up only paginator test data, not all documents
        self.conn.delete_query('id:%s*' % self._PREFIX, commit=True)
        for i in range(0, 15):
            self.conn.add({'id': '%s%02i' % (self._PREFIX, i),
                           'data': 'data_%02i' % i})
        self.conn.commit()
        self.result = self.query(
            self.conn, 'id:%s*' % self._PREFIX, sort='data', sort_order='desc')

    def tearDown(self):
        try:
            self.conn.delete_query('id:%s*' % self._PREFIX, commit=True)
        except Exception:
            pass
        super().tearDown()

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
        self.assertEqual(list(paginator.page_range), [1,2])

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
        chinese_data = b'\xe6\xb3\xb0\xe5\x9b\xbd'.decode('utf-8')
        uid = 'pag_unicode_test'
        self.conn.add({'id': uid, 'data': chinese_data})
        self.conn.commit()
        result = self.query(self.conn, 'data:' + chinese_data)
        paginator = solr.SolrPaginator(result, default_page_size=10)
        try:
            paginator.page(1)
        except (solr.SolrException, ValueError, TypeError):
            self.fail('Unicode not encoded correctly in paginator')
        finally:
            self.conn.delete(id=uid, commit=True)



class TestResponseFormat(unittest.TestCase):
    """Test the response_format constructor option."""

    def test_default_format_is_json(self):
        conn = solr.Solr(SOLR_HTTP)
        self.assertEqual(conn.response_format, 'json')
        conn.close()

    def test_explicit_xml_format(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        self.assertEqual(conn.response_format, 'xml')
        conn.close()

    def test_json_format(self):
        conn = solr.Solr(SOLR_HTTP, response_format='json')
        self.assertEqual(conn.response_format, 'json')
        conn.close()

    def test_invalid_format_raises(self):
        with self.assertRaises(ValueError):
            solr.Solr(SOLR_HTTP, response_format='csv')

    def test_xml_query_returns_response(self):
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        conn.add({'id': 'fmt_xml_test', 'data': 'hello'}, commit=True)
        resp = conn.select('id:fmt_xml_test')
        self.assertEqual(resp.numFound, 1)
        self.assertEqual(resp.results[0]['id'], 'fmt_xml_test')
        conn.delete(id='fmt_xml_test', commit=True)
        conn.close()

    def test_json_query_returns_response(self):
        conn = solr.Solr(SOLR_HTTP, response_format='json')
        conn.add({'id': 'fmt_json_test', 'data': 'hello'}, commit=True)
        resp = conn.select('id:fmt_json_test')
        self.assertEqual(resp.numFound, 1)
        self.assertEqual(resp.results[0]['id'], 'fmt_json_test')
        conn.delete(id='fmt_json_test', commit=True)
        conn.close()

    def test_json_query_has_header(self):
        conn = solr.Solr(SOLR_HTTP, response_format='json')
        conn.add({'id': 'fmt_json_hdr', 'data': 'test'}, commit=True)
        resp = conn.select('id:fmt_json_hdr')
        self.assertIn('status', resp.header)
        self.assertEqual(resp.header['status'], 0)
        conn.delete(id='fmt_json_hdr', commit=True)
        conn.close()


# ===================================================================
# 1.0.6 tests — URL validation
# ===================================================================


class TestPaginatorExceptions(unittest.TestCase):
    """EmptyPage and PageNotAnInteger should be standard exceptions."""

    def test_empty_page_is_not_solr_exception(self):
        from solr.paginator import EmptyPage
        self.assertFalse(issubclass(EmptyPage, solr.SolrException))

    def test_empty_page_is_value_error(self):
        from solr.paginator import EmptyPage
        self.assertTrue(issubclass(EmptyPage, ValueError))

    def test_page_not_an_integer_exists(self):
        from solr.paginator import PageNotAnInteger
        self.assertTrue(issubclass(PageNotAnInteger, TypeError))

    def test_page_not_an_integer_raised(self):
        from solr.paginator import PageNotAnInteger
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        conn.add({'id': 'pagerr_test', 'data': 'x'}, commit=True)
        result = conn.select('id:pagerr_test')
        paginator = solr.SolrPaginator(result, default_page_size=10)
        with self.assertRaises(PageNotAnInteger):
            paginator.page('abc')  # type: ignore
        conn.delete(id='pagerr_test', commit=True)
        conn.close()

    def test_empty_page_raised(self):
        from solr.paginator import EmptyPage
        conn = solr.Solr(SOLR_HTTP, response_format='xml')
        conn.add({'id': 'pagemp_test', 'data': 'x'}, commit=True)
        result = conn.select('id:pagemp_test')
        paginator = solr.SolrPaginator(result, default_page_size=10)
        with self.assertRaises(EmptyPage):
            paginator.page(999)
        conn.delete(id='pagemp_test', commit=True)
        conn.close()


# ===================================================================
# 1.0.8 tests — retry improvements
# ===================================================================

