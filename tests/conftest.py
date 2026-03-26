"""Shared test fixtures and base classes for solrpy tests."""

import socket
import unittest
import http.client
import http.client as httplib
from string import digits
from random import choice

import solr
import solr.core

SOLR_PATH = "/solr/core0"
SOLR_HOST = "localhost"
SOLR_PORT_HTTP = "8983"
SOLR_PORT_HTTPS = "8943"
SOLR_HTTP = "http://" + SOLR_HOST + ":" + SOLR_PORT_HTTP + SOLR_PATH
SOLR_HTTPS = "https://" + SOLR_HOST + ":" + SOLR_PORT_HTTPS + SOLR_PATH


def get_rand_string():
    return "".join(choice(digits) for x in range(12))


def get_rand_userdoc(id=None, user_id=None, data=None):
    return {
        "user_id": user_id or get_rand_string(),
        "data": data or get_rand_string(),
        "id": id or get_rand_string(),
    }


class SolrConnectionTestCase(unittest.TestCase):

    connection_factory = solr.Solr

    def setUp(self):
        self._connections = []

    def tearDown(self):
        for conn in self._connections:
            conn.close()

    def new_connection(self, **kw):
        kw.setdefault('response_format', 'xml')
        conn = self.connection_factory(SOLR_HTTP, **kw)
        self._connections.append(conn)
        return conn

    def add(self, **doc):
        self._connections[-1].add(doc)

    def query(self, conn, *args, **params):
        return conn.select(*args, **params)

    def raw_query(self, conn, **params):
        return conn.select.raw(**params)

    def check_added(self, doc=None, docs=None):
        if docs is None:
            docs = []
        if doc is not None:
            docs.append(doc)
        conn = self._connections[-1]
        for doc in docs:
            results = self.query(conn, "id:" + doc["id"]).results
            self.assertEqual(
                len(results), 1,
                "Could not find expected data (id:%s)" % doc["id"])
            self.assertEqual(results[0]["user_id"], doc["user_id"])
            self.assertEqual(results[0]["data"], doc["data"])

    def check_removed(self, doc=None, docs=None):
        if docs is None:
            docs = []
        if doc is not None:
            docs.append(doc)
        conn = self._connections[-1]
        for doc in docs:
            results = self.query(conn, "id:" + doc["id"]).results
            self.assertEqual(
                len(results), 0,
                "Document (id:%s) should have been deleted" % doc["id"])


# Alias for backward compatibility in test class hierarchy
SolrBased = SolrConnectionTestCase


class RequestTracking(SolrConnectionTestCase):
    """Mix in request tracking for tests."""

    def new_connection(self, **kw):
        conn = super().new_connection(**kw)
        request = conn.conn.request

        def wrap(*args, **kw):
            self._update = args, kw
            return request(*args, **kw)

        conn.conn.request = wrap
        return conn

    def method(self):
        return self._update[0][0]

    def selector(self):
        s = self._update[0][1]
        if s.startswith(SOLR_PATH):
            return s[len(SOLR_PATH):]
        self.fail("URL path doesn't start with expected prefix")

    def postbody(self):
        return self._update[0][2]


class ThrowBadStatusLineExceptions:
    """Helper that forces BadStatusLine exceptions for retry testing."""

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


class EmptyResponse:

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
        return self._empty_results.encode('utf-8')
