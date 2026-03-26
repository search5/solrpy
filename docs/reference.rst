API Reference
=============

.. module:: solr
   :synopsis: Python client for Apache Solr.


Data representation
-------------------

Solr documents are modeled as Python dictionaries with field names as keys
and field values as values.

- Multi-valued fields use ``list``, ``tuple``, or ``set`` as values.
- ``datetime.datetime`` values are converted to UTC.
- ``datetime.date`` values are converted to ``datetime.datetime`` at
  00:00:00 UTC.
- ``bool`` values are converted to ``'true'`` or ``'false'``.
- ``None`` values are omitted from the document sent to Solr.


Exceptions
----------

.. autoclass:: solr.SolrException
   :members: httpcode, reason, body
   :show-inheritance:

.. class:: solr.core.SolrVersionError(feature, required, actual)

   Raised when a feature requires a higher Solr version than connected.
   Subclass of :class:`Exception`.

   .. attribute:: feature

      Name of the feature that was called (string).

   .. attribute:: required

      Minimum version required as a tuple, e.g. ``(4, 0)``.

   .. attribute:: actual

      Detected server version as a tuple, e.g. ``(3, 6, 2)``.


Solr class
----------

.. class:: Solr(url, persistent=True, timeout=None, ssl_key=None, ssl_cert=None, http_user=None, http_pass=None, post_headers=None, max_retries=3, debug=False)

   Connect to the Solr instance at *url*. If the Solr instance provides
   multiple cores, *url* should point to a specific core.

   **Constructor parameters:**

   .. list-table::
      :widths: 20 80
      :header-rows: 1

      * - Parameter
        - Description
      * - ``url``
        - URI pointing to the Solr instance (e.g. ``http://localhost:8983/solr/mycore``)
      * - ``persistent``
        - Keep a persistent HTTP connection open. Defaults to ``True``.
      * - ``timeout``
        - Timeout in seconds for server responses.
      * - ``ssl_key``
        - Path to PEM key file for SSL client authentication.
      * - ``ssl_cert``
        - Path to PEM certificate file for SSL client authentication.
      * - ``http_user``
        - Username for HTTP Basic authentication.
      * - ``http_pass``
        - Password for HTTP Basic authentication.
      * - ``post_headers``
        - Dictionary of additional headers to include in all requests.
      * - ``max_retries``
        - Maximum number of automatic retries on connection errors. Defaults to ``3``.
      * - ``debug``
        - If ``True``, log all requests and responses.

   **Attributes:**

   .. attribute:: Solr.server_version

      Tuple representing the detected Solr version, e.g. ``(9, 4, 1)``.
      Automatically populated during initialization.

   .. attribute:: Solr.select

      A :class:`SearchHandler` instance bound to the ``/select`` endpoint.

   **Search methods:**

   The ``select`` attribute is the primary search interface. See
   :class:`SearchHandler` for details::

       response = conn.select('title:lucene')

   **Update methods:**

   .. automethod:: solr.Solr.add(doc)
   .. automethod:: solr.Solr.add_many(docs)

   **Delete methods:**

   .. automethod:: solr.Solr.delete(id=None, ids=None, queries=None)
   .. automethod:: solr.Solr.delete_many(ids)
   .. automethod:: solr.Solr.delete_query(query)

   **Commit and optimize:**

   .. automethod:: solr.Solr.commit
   .. automethod:: solr.Solr.optimize

   **Connection management:**

   .. automethod:: solr.Solr.close


Commit-control arguments
~~~~~~~~~~~~~~~~~~~~~~~~

Several update methods support optional keyword arguments to control
commits. These arguments are always optional; no commit is performed if
they are not provided.

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Argument
     - Description
   * - ``commit``
     - If ``True``, commit changes before returning.
   * - ``optimize``
     - If ``True``, optimize the index before returning (implies ``commit=True``).
   * - ``wait_flush``
     - Block until the commit is flushed to disk. Defaults to ``True``.
   * - ``wait_searcher``
     - Block until searcher objects are warmed. Defaults to ``True``.

If ``wait_flush`` or ``wait_searcher`` are specified without ``commit`` or
``optimize``, a :exc:`TypeError` is raised.

Methods that support commit-control arguments: ``add``, ``add_many``,
``delete``, ``delete_many``, ``delete_query``.


SolrConnection class (legacy)
-----------------------------

.. class:: SolrConnection(url)

   Backward-compatible connection class. New applications should use
   :class:`Solr` instead.

   Inherits all methods from :class:`Solr`, but these methods have
   different signatures:

   .. automethod:: solr.SolrConnection.add
   .. automethod:: solr.SolrConnection.add_many

   .. method:: SolrConnection.query(q, fields=None, highlight=None, score=True, sort=None, sort_order="asc", **params)

      Delegates to ``self.select(...)``.

   .. method:: SolrConnection.raw_query(**params)

      Delegates to ``self.select.raw(...)``.


SearchHandler class
-------------------

.. class:: SearchHandler(connection, path="/select", arg_separator="_")

   Provides access to a named Solr request handler. The ``select``
   attribute on :class:`Solr` instances is a ``SearchHandler`` bound to
   ``/select``.

   Create handlers for custom endpoints::

       import solr

       conn = solr.Solr('http://localhost:8983/solr/mycore')
       my_handler = solr.SearchHandler(conn, '/my_handler')
       response = my_handler('some query')


.. method:: SearchHandler.__call__(q=None, fields=None, highlight=None, score=True, sort=None, sort_order="asc", **params)

   Execute a search query against Solr.

   :param q: Query string.
   :param fields: Fields to return. String or iterable. Defaults to ``'*'``.
   :param highlight: ``False`` (default), ``True``, or a list of field names.
   :param score: Include ``score`` in results. Defaults to ``True``.
   :param sort: Fields to sort by. String or iterable.
   :param sort_order: Default sort direction (``'asc'`` or ``'desc'``).
   :param params: Additional Solr parameters (use underscores for dots).
   :returns: A :class:`Response` instance.
   :raises ValueError: If ``highlight=True`` but no fields are specified,
                        or if ``sort_order`` is invalid.


.. method:: SearchHandler.raw(**params)

   Issue a raw query. No processing is performed on parameters or
   responses. Returns the raw response text.


Response class
--------------

.. class:: Response

   Container for query results.

   **Attributes:**

   .. attribute:: Response.header

      Dictionary containing response header values (status, QTime, params).

   .. attribute:: Response.results

      A :class:`Results` list of matching documents. Each document is a
      dictionary of field names to values.

   .. attribute:: Response.numFound

      Total number of matching documents.

   .. attribute:: Response.start

      Starting offset of the current result set.

   .. attribute:: Response.maxScore

      Maximum relevance score across all matches.

   **Pagination methods:**

   .. method:: Response.next_batch()

      Fetch the next batch of results. Returns a new :class:`Response`,
      or ``None`` if there are no more results.

   .. method:: Response.previous_batch()

      Fetch the previous batch of results. Returns a new :class:`Response`,
      or ``None`` if this is the first batch.

   **Iteration:**

   Response objects support ``len()`` and iteration::

       response = conn.select('*:*')
       print(len(response))
       for doc in response:
           print(doc['id'])
