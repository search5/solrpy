# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# $Id$
"""

A simple Solr client for python.


Features
--------
 * Supports SOLR 1.2+
 * Supports http/https and SSL client-side certificates
 * Uses persistent HTTP connections by default
 * Properly converts to/from SOLR data types, including datetime objects
 * Supports both querying and update commands (add, delete).
 * Supports batching of commands
 * Requires Python 2.3+


Connections
-----------
`SolrConnection` can be passed in the following parameters.
Only `url` is required,.

    url -- URI pointing to the SOLR instance. Examples:

        http://localhost:8080/solr
        https://solr-server/solr

        Your python install must be compiled with SSL support for the
        https:// schemes to work. (Most pre-packaged pythons are.)

    persistent -- Keep a persistent HTTP connection open.
        Defaults to true.

    timeout -- Timeout, in seconds, for the server to response.
        By default, use the python default timeout (of none?)
        NOTE: This changes the python-wide timeout.

    ssl_key, ssl_cert -- If using client-side key files for
        SSL authentication,  these should be, respectively,
        your PEM key file and certificate file

Once created, a connection object has the following public methods:

    query (q, fields=None, highlight=None,
           score=True, sort=None, **params)

            q -- the query string.

            fields -- optional list of fields to include. It can be either
                a string in the format that SOLR expects ('id,f1,f2'), or
                a python list/tuple of field names.   Defaults to returning
                all fields. ("*")

            score -- boolean indicating whether "score" should be included
                in the field list.  Note that if you explicitly list
                "score" in your fields value, then this parameter is
                effectively ignored.  Defaults to true.

            highlight -- indicates whether highlighting should be included.
                `highlight` can either be `False`, indicating "No" (the
                default),  `True`, incidating to highlight any fields
                included in "fields", or a list of field names.

            sort -- list of fields to sort by.

            Any parameters available to SOLR 'select' calls can also be
            passed in as named parameters (e.g., fq='...', rows=20, etc).

            Many SOLR parameters are in a dotted notation (e.g.,
            `hl.simple.post`).  For such parameters, replace the dots with
            underscores when calling this method. (e.g.,
            hl_simple_post='</pre'>)

            Returns a Response object

    add(**params)

            Add a document.  Pass in all document fields as
            keyword parameters:

                add(id='foo', notes='bar')

            You must "commit" for the addition to be saved.
            This command honors begin_batch/end_batch.

    add_many(lst)

            Add a series of documents at once.  Pass in a list of
            dictionaries, where each dictionary is a mapping of document
            fields:

                add_many( [ {'id': 'foo1', 'notes': 'foo'},
                            {'id': 'foo2', 'notes': 'w00t'} ] )

            You must "commit" for the addition to be saved.
            This command honors begin_batch/end_batch.

    delete(id)

            Delete a document by id.

            You must "commit" for the deletion to be saved.
            This command honors begin_batch/end_batch.

    delete_many(lst)

            Delete a series of documents.  Pass in a list of ids.

            You must "commit" for the deletion to be saved.
            This command honors begin_batch/end_batch.

    delete_query(query)

            Delete any documents returned by issuing a query.

            You must "commit" for the deletion to be saved.
            This command honors begin_batch/end_batch.


    commit(wait_flush=True, wait_searcher=True)

            Issue a commit command.

            This command honors begin_batch/end_batch.

    optimize(wait_flush=True, wait_searcher=True)

            Issue an optimize command.

            This command honors begin_batch/end_batch.

    begin_batch()

            Begin "batch" mode, in which all commands to be sent
            to the SOLR server are queued up and sent all at once.

            No update commands will be sent to the backend server
            until end_batch() is called. Not that "query" commands
            are not batched.

            begin_batch/end_batch transactions can be nested.
            The transaction will not be sent to the backend server
            until as many end_batch() calls have been made as
            begin_batch()s.

            Batching is completely optional. Any update commands
            issued outside of a begin_batch()/end_batch() pair will
            be immediately processed.

    end_batch(commit=False)

            End a batching pair.  Any pending commands are sent
            to the backend server.  If "True" is passed in to
            end_batch, a <commit> is also sent.

    raw_query(**params)

            Send a query command (unprocessed by this library) to
            the SOLR server. The resulting text is returned un-parsed.

                raw_query(q='id:1', wt='python', indent='on')

            Many SOLR parameters are in a dotted notation (e.g.,
            `hl.simple.post`).  For such parameters, replace the dots with
            underscores when calling this method. (e.g.,
            hl_simple_post='</pre'>)

    close()
            Close the underlying HTTP(S) connection.


Query Responses
---------------

    Calls to connection.query() return a Response object.

    Response objects always have the following properties:

        results -- A list of matching documents. Each document will be a
            dict of field values.

        results.start -- An integer indicating the starting # of documents

        results.numFound -- An integer indicating the total # of matches.

        results.maxScore -- An integer indicating the maximum score assigned
                            to a document. Takes into account all of documents
                            found by the query, not only the current batch.

        header -- A dict containing any responseHeaders.  Usually:

            header['params'] -- dictionary of original parameters used to
                        create this response set.

            header['QTime'] -- time spent on the query

            header['status'] -- status code.

            See SOLR documentation for other/typical return values.
            This may be settable at the SOLR-level in your config files.


        next_batch() -- If only a partial set of matches were returned
            (by default, 10 documents at a time), then calling
            .next_batch() will return a new Response object containing
            the next set of matching documents. Returns None if no
            more matches.

            This works by re-issuing the same query to the backend server,
            with a new 'start' value.

        previous_batch() -- Same as next_batch, but return the previous
            set of matches.  Returns None if this is the first batch.

    Response objects also support __len__ and iteration. So, the following
    shortcuts work:

        responses = connection.query('q=foo')
        print len(responses)
        for document in responses:
            print document['id'], document['score']


    If you pass in `highlight` to the SolrConnection.query call,
    then the response object will also have a "highlighting" property,
    which will be a dictionary.


Quick examples on use:
----------------------

Example showing basic connection/transactions

    >>> from solr import *
    >>> c = SolrConnection('http://localhost:8983/solr')
    >>> c.add(id='500', name='python test doc', inStock=True)
    >>> c.delete('123')
    >>> c.commit()


Examples showing the search wrapper

    >>> response = c.query('test', rows=20)
    >>> print response.results.start
     0
    >>> for match in response:
    ...     print match['id'],
      0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19
    >>> response = response.next_batch()
    >>> print response.results.start
     20

Add 3 documents and delete 1, but send all of them as a single transaction.

    >>> c.begin_batch()
    >>> c.add(id="1")
    >>> c.add(id="2")
    >>> c.add(id="3")
    >>> c.delete(id="0")
    >>> c.end_batch(True)

Enter a raw query, without processing the returned HTML contents.

    >>> print c.raw_query(q='id:[* TO *]', wt='python', rows='10')

"""
import sys
import socket
import httplib
import urlparse
import codecs
import urllib
import datetime
from StringIO import StringIO
from xml.sax import make_parser
from xml.sax.handler import ContentHandler
from xml.sax.saxutils import escape, quoteattr
from xml.dom.minidom import parseString

__version__ = "1.2.0"

__all__ = ['SolrException', 'SolrConnection', 'Response']


# ===================================================================
# Exceptions
# ===================================================================
class SolrException(Exception):
    """ An exception thrown by solr connections """
    def __init__(self, httpcode, reason=None, body=None):
        self.httpcode = httpcode
        self.reason = reason
        self.body = body

    def __repr__(self):
        return 'HTTP code=%s, Reason=%s, body=%s' % (
                    self.httpcode, self.reason, self.body)

    def __str__(self):
        return 'HTTP code=%s, reason=%s' % (self.httpcode, self.reason)


# ===================================================================
# Connection Object
# ===================================================================
class SolrConnection:
    """
    Represents a Solr connection.

    Designed to work with the 2.2 response format (SOLR 1.2+).
    (though 2.1 will likely work.)
    """

    def __init__(self, url,
                 persistent=True,
                 timeout=None,
                 ssl_key=None,
                 ssl_cert=None,
                 post_headers={}):

        """
            url -- URI pointing to the SOLR instance. Examples:

                http://localhost:8080/solr
                https://solr-server/solr

                Your python install must be compiled with SSL support for the
                https:// schemes to work. (Most pre-packaged pythons are.)

            persistent -- Keep a persistent HTTP connection open.
                Defaults to true

            timeout -- Timeout, in seconds, for the server to response.
                By default, use the python default timeout (of none?)
                NOTE: This changes the python-wide timeout.

            ssl_key, ssl_cert -- If using client-side key files for
                SSL authentication,  these should be, respectively,
                your PEM key file and certificate file

        """

        self.scheme, self.host, self.path = urlparse.urlparse(url, 'http')[:3]
        self.url = url

        assert self.scheme in ('http','https')

        self.persistent = persistent
        self.reconnects = 0
        self.timeout = timeout
        self.ssl_key = ssl_key
        self.ssl_cert = ssl_cert

        if self.scheme == 'https':
            self.conn = httplib.HTTPSConnection(self.host,
                   key_file=ssl_key, cert_file=ssl_cert)
        else:
            self.conn = httplib.HTTPConnection(self.host)

        self.batch_cnt = 0  #  this is int, not bool!
        self.response_version = 2.2
        self.encoder = codecs.getencoder('utf-8')

        # Responses from Solr will always be in UTF-8
        self.decoder = codecs.getdecoder('utf-8')

        # Set timeout, if applicable.
        if timeout:
            socket.setdefaulttimeout(timeout)

        self.xmlheaders = {'Content-Type': 'text/xml; charset=utf-8'}
        self.xmlheaders.update(post_headers)
        if not self.persistent:
            self.xmlheaders['Connection'] = 'close'

        self.form_headers = {
                'Content-Type':
                'application/x-www-form-urlencoded; charset=utf-8'}

        if not self.persistent:
            self.form_headers['Connection'] = 'close'

    def close(self):
        self.conn.close()

    def query(self, q, fields=None, highlight=None,
              score=True, sort=None, sort_order="asc", **params):
        """
        q is the query string.

        fields is an optional list of fields to include. It can
        be either a string in the format that SOLR expects, or
        a python list/tuple of field names.   Defaults to
        all fields. ("*")

        score indicates whether "score" should be included
        in the field list.  Note that if you explicitly list
        "score" in your fields value, then score is
        effectively ignored.  Defaults to true.

        highlight indicates whether highlighting should be included.
        highlight can either be False, indicating "No" (the default),
        a list of fields in the same format as "fields" or True, indicating
        to highlight any fields included in "fields". If True and no "fields"
        are given, raise a ValueError.

        sort is a list of fields to sort by. See "fields" for
        formatting.

        sort_order defaults to "asc" and specifies the order to sort the fields
        in. sort_order must be "asc" or "desc", otherwise a ValueError is raised.

        Optional parameters can also be passed in.  Many SOLR
        parameters are in a dotted notation (e.g., hl.simple.post).
        For such parameters, replace the dots with underscores when
        calling this method. (e.g., hl_simple_post='</pre'>)

        Returns a Response instance.
        """

        # Clean up optional parameters to match SOLR spec.
        params = dict([(key.replace('_','.'), unicode(value))
                      for key, value in params.items()])

        if highlight:
            params['hl'] = 'true'
            if not isinstance(highlight, (bool, int, float)):
                if not isinstance(highlight, basestring):
                    highlight = ",".join(highlight)
                params['hl.fl'] = highlight
            else:
                if not fields:
                    raise ValueError("highlight is True and no fields were given")
                elif isinstance(fields, basestring):
                    params['hl.fl'] = [fields]
                else:
                    params['hl.fl'] = ",".join(fields)

        if q is not None:
            params['q'] = q

        if fields:
            if not isinstance(fields, basestring):
                fields = ",".join(fields)
        if not fields:
            fields = '*'

        if sort:
            if not sort_order or sort_order not in ("asc", "desc"):
                raise ValueError("sort_order must be 'asc' or 'desc'")
            if not isinstance(sort, basestring):
                sort = ",".join(sort)
            params['sort'] = "%s %s" % (sort, sort_order)

        if score and not 'score' in fields.replace(',',' ').split():
            fields += ',score'

        params['fl'] = fields
        params['version'] = self.response_version
        params['wt'] = 'standard'

        request = urllib.urlencode(params, doseq=True)

        try:
            rsp = self._post(self.path + '/select',
                              request, self.form_headers)
            # If we pass in rsp directly, instead of using rsp.read())
            # and creating a StringIO, then Persistence breaks with
            # an internal python error.
            xml = StringIO(rsp.read())
            data = parse_query_response(xml,  params=params, connection=self)

        finally:
            if not self.persistent:
                self.close()

        return data

    def begin_batch(self):
        """
        Denote the beginning of a batch update.

        No update commands will be sent to the backend server
        until end_batch() is called.

        Any update commands issued outside of a begin_batch()/
        end_batch() series will be immediately processed.

        begin_batch/end_batch transactions can be nested.
        The transaction will not be sent to the backend server
        until as many end_batch() calls have been made as
        begin_batch()s.
        """
        if not self.batch_cnt:
            self.__batch_queue = []

        self.batch_cnt += 1

        return self.batch_cnt

    def end_batch(self, commit=False):
        """
        Denote the end of a batch update.

        Sends any queued commands to the backend server.

        If `commit` is True, then a <commit/> command is included
        at the end of the list of commands sent.
        """
        batch_cnt = self.batch_cnt - 1
        if batch_cnt < 0:
            raise SolrException(
                "end_batch called without a corresponding begin_batch")

        self.batch_cnt = batch_cnt
        if batch_cnt:
            return False

        if commit:
            self.__batch_queue.append('<commit/>')

        return self._update("".join(self.__batch_queue))

    def delete(self, id):
        """
        Delete a specific document by id.
        """
        xstr = u'<delete><id>%s</id></delete>' % escape(unicode(id))
        return self._update(xstr)

    def delete_many(self, ids):
        """
        Delete documents using a list of IDs.
        """
        [self.delete(id) for id in ids]

    def delete_query(self, query):
        """
        Delete all documents returned by a query.
        """
        xstr = u'<delete><query>%s</query></delete>' % escape(query)
        return self._update(xstr)

    def add(self, _commit=False, **fields):
        """
        Add a document to the SOLR server.  Document fields
        should be specified as arguments to this function

        Example:
            connection.add(id="mydoc", author="Me")
        """
        lst = [u'<add>']
        self.__add(lst, fields)
        lst.append(u'</add>')
        xstr = ''.join(lst)
        if not _commit:
            return self._update(xstr)
        else:
            self._update(xstr)
            return self.commit()

    def add_many(self, docs, _commit=False):
        """
        Add several documents to the SOLR server.

        docs -- a list of dicts, where each dict is a document to add
            to SOLR.
        """
        lst = [u'<add>']
        for doc in docs:
            self.__add(lst, doc)
        lst.append(u'</add>')
        xstr = ''.join(lst)
        if not _commit:
            return self._update(xstr)
        else:
            self._update(xstr)
            return self.commit()

    def commit(self, wait_flush=True, wait_searcher=True, _optimize=False):
        """
        Issue a commit command to the SOLR server.
        """
        if not wait_searcher:  #just handle deviations from the default
            if not wait_flush:
                options = 'waitFlush="false" waitSearcher="false"'
            else:
                options = 'waitSearcher="false"'
        else:
            options = ''

        if _optimize:
            xstr = u'<optimize %s/>' % options
        else:
            xstr = u'<commit %s/>' % options

        return self._update(xstr)

    def optimize(self, wait_flush=True, wait_searcher=True, ):
        """
        Issue an optimize command to the SOLR server.
        """
        self.commit(wait_flush, wait_searcher, _optimize=True)

    def raw_query(self, **params):
        """
        Issue a query against a SOLR server.

        Return the raw result.  No pre-processing or
        post-processing happends to either
        input parameters or responses
        """

        # Clean up optional parameters to match SOLR spec.
        params = dict([(key.replace('_','.'), unicode(value))
                       for key, value in params.items()])

        request = urllib.urlencode(params, doseq=True)

        try:
            rsp = self._post(self.path+'/select',
                              request, self.form_headers)
            data = rsp.read()
        finally:
            if not self.persistent:
                self.close()

        return data

    def _update(self, request):

        # If we're in batching mode, just queue up the requests for later.
        if self.batch_cnt:
            self.__batch_queue.append(request)
            return

        try:
            rsp = self._post(self.path + '/update',
                              request, self.xmlheaders)
            data = rsp.read()
        finally:
            if not self.persistent:
                self.close()

        # Detect old-style error response (HTTP response code
        # of 200 with a non-zero status.
        if data.startswith('<result status="') and not data.startswith('<result status="0"'):
            data = self.decoder(data)[0]
            parsed = parseString(data)
            status = parsed.documentElement.getAttribute('status')
            if status != 0:
                reason = parsed.documentElement.firstChild.nodeValue
                raise SolrException(rsp.status, reason)
        return data

    def __add(self, lst, fields):
        lst.append(u'<doc>')
        for field, value in fields.items():
            # Do some basic data conversion
            if isinstance(value, datetime.datetime):
                value = utc_to_string(value)

            elif isinstance(value, bool):
                value = value and 'true' or 'false'

            # Handle multi-valued fields if values
            # is passed in as a list/tuple
            if not isinstance(value, (list, tuple)):
                values = [value]
            else:
                values = value

            for value in values:
                lst.append('<field name=%s>%s</field>' % (
                    (quoteattr(field),
                    escape(unicode(value)))))
        lst.append('</doc>')

    def __repr__(self):
        return ('<SolrConnection (url=%s, '
                'persistent=%s, post_headers=%s, reconnects=%s)>') % (
            self.url, self.persistent,
            self.xmlheaders, self.reconnects)

    def _reconnect(self):
        self.reconnects += 1
        self.close()
        self.conn.connect()

    def _post(self, url, body, headers):
        attempts = 1
        while attempts:
            try:
                self.conn.request('POST', url, body.encode('UTF-8'), headers)
                return check_response_status(self.conn.getresponse())
            except (socket.error,
                    httplib.ImproperConnectionState,
                    httplib.BadStatusLine):
                    # We include BadStatusLine as they are spurious
                    # and may randomly happen on an otherwise fine
                    # SOLR connection (though not often)
                self._reconnect()
                attempts -= 1
                if not attempts:
                    raise


# ===================================================================
# Response objects
# ===================================================================
class Response(object):
    """
    A container class for a

    A Response object will have the following properties:

          header -- a dict containing any responseHeader values

          results -- a list of matching documents. Each list item will
              be a dict.
    """
    def __init__(self, connection):
        # These are set in ResponseContentHandler.endElement()
        self.header = {}
        self.results = []

        # These are set by parse_query_response().
        # Used only if .next_batch()/previous_batch() is called
        self._connection = connection
        self._params = {}

    def __len__(self):
        """
        Return the number of matching documents contained in this set.
        """
        return len(self.results)

    def __iter__(self):
        """
        Return an iterator of matching documents.
        """
        return iter(self.results)

    def next_batch(self):
        """
        Load the next set of matches.

        By default, SOLR returns 10 at a time.
        """
        try:
            start = int(self.results.start)
        except AttributeError:
            start = 0

        start += len(self.results)
        params = dict(self._params)
        params['start'] = start
        q = params['q']
        del params['q']
        return self._connection.query(q, **params)

    def previous_batch(self):
        """
        Return the previous set of matches
        """
        try:
            start = int(self.results.start)
        except AttributeError:
            start = 0

        if not start:
            return None

        rows = int(self.header.get('rows', len(self.results)))
        start = max(0, start - rows)
        params = dict(self._params)
        params['start'] = start
        params['rows'] = rows
        q = params['q']
        del params['q']
        return self._connection.query(q, **params)


# ===================================================================
# XML Parsing support
# ===================================================================
def parse_query_response(data, params, connection):
    """
    Parse the XML results of a /select call.
    """
    parser = make_parser()
    handler = ResponseContentHandler()
    parser.setContentHandler(handler)
    parser.parse(data)
    if handler.stack[0].children:
        response = handler.stack[0].children[0].final
        response._params = params
        response._connection = connection
        return response
    else:
        return None


class ResponseContentHandler(ContentHandler):
    """
    ContentHandler for the XML results of a /select call.
    (Versions 2.2 (and possibly 2.1))
    """
    def __init__(self):
        self.stack = [Node(None, {})]
        self.in_tree = False

    def startElement(self, name, attrs):
        if not self.in_tree:
            if name != 'response':
                raise SolrException(
                    "Unknown XML response from server: <%s ..." % (
                        name))
            self.in_tree = True

        element = Node(name, attrs)

        # Keep track of new node
        self.stack.append(element)

        # Keep track of children
        self.stack[-2].children.append(element)


    def characters (self, ch):
        self.stack[-1].chars.append(ch)


    def endElement(self, name):
        node = self.stack.pop()

        name = node.name
        value = "".join(node.chars)

        if name == 'int':
            node.final = int(value.strip())

        elif name == 'str':
            node.final = value

        elif name == 'null':
            node.final = None

        elif name == 'long':
            node.final = long(value.strip())

        elif name == 'bool':
            node.final = value.strip().lower().startswith('t')

        elif name == 'date':
             node.final = utc_from_string(value.strip())

        elif name in ('float','double', 'status','QTime'):
            node.final = float(value.strip())

        elif name == 'response':
            node.final = response = Response(self)
            for child in node.children:
                name = child.attrs.get('name', child.name)
                if name == 'responseHeader':
                    name = 'header'
                elif child.name == 'result':

                    name = 'results'
                    for attr_name in child.attrs.getNames():
                        # We already know it is a response
                        if attr_name != "name":
                            setattr(response, attr_name, child.attrs.get(attr_name))

                setattr(response, name, child.final)

        elif name in ('lst','doc'):
            # Represent these with a dict
            node.final = dict(
                    [(cnode.attrs['name'], cnode.final)
                        for cnode in node.children])

        elif name in ('arr',):
            node.final = [cnode.final for cnode in node.children]

        elif name == 'result':
            node.final = Results([cnode.final for cnode in node.children])


        elif name in ('responseHeader',):
            node.final = dict([(cnode.name, cnode.final)
                        for cnode in node.children])

        else:
            raise SolrException("Unknown tag: %s" % name)

        for attr, val in node.attrs.items():
            if attr != 'name':
                setattr(node.final, attr, val)


class Results(list):
    """
    Convenience class containing <result> items
    """
    pass


class Node(object):
    """
    A temporary object used in XML processing. Not seen by end user.
    """
    def __init__(self, name, attrs):
        """
        Final will eventually be the "final" representation of
        this node, whether an int, list, dict, etc.
        """
        self.chars = []
        self.name = name
        self.attrs = attrs
        self.final = None
        self.children = []

    def __repr__(self):
        return '<%s val="%s" %s>' % (
            self.name,
            "".join(self.chars).strip(),
            ' '.join(['%s="%s"' % (attr, val)
                            for attr, val in self.attrs.items()]))


# ===================================================================
# Misc utils
# ===================================================================
def check_response_status(response):
    if response.status != 200:
        ex = SolrException(response.status, response.reason)
        try:
            ex.body = response.read()
        except:
            pass
        raise ex
    return response


# -------------------------------------------------------------------
# Datetime extensions to parse/generate SOLR date formats
# -------------------------------------------------------------------
# A UTC class, for parsing SOLR's returned dates.
class UTC(datetime.tzinfo):
    """
    UTC timezone.
    """
    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return datetime.timedelta(0)


utc = UTC()

def utc_to_string(value):
    """
    Convert datetimes to the subset of ISO 8601 that SOLR expects.
    """
    value = value.astimezone(utc).isoformat()
    if '+' in value:
        value = value.split('+')[0]
    value += 'Z'
    return value

def utc_from_string(value):
    """
    Parse a string representing an ISO 8601 date.
    Note: this doesn't process the entire ISO 8601 standard,
    onle the specific format SOLR promises to generate.
    """
    try:
        if not value.endswith('Z') and value[10] == 'T':
            raise ValueError(value)
        year = int(value[0:4])
        month = int(value[5:7])
        day = int(value[8:10])
        hour = int(value[11:13])
        minute = int(value[14:16])
        microseconds = int(float(value[17:-1]) * 1000000.0)
        second, microsecond = divmod(microseconds, 1000000)
        return datetime.datetime(year, month, day, hour,
            minute, second, microsecond, utc)
    except ValueError:
        raise ValueError ("'%s' is not a valid ISO 8601 SOLR date" % value)
