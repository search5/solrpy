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

.. class:: Solr(url, persistent=True, timeout=None, ssl_key=None, ssl_cert=None, http_user=None, http_pass=None, post_headers=None, max_retries=3, always_commit=False, debug=False)

   Connect to the Solr instance at *url*. If the Solr instance provides
   multiple cores, *url* should point to a specific core.

   **Constructor parameters:**

   .. list-table::
      :widths: 20 80
      :header-rows: 1

      * - Parameter
        - Description
      * - ``url``
        - URI pointing to the Solr instance (e.g. ``http://localhost:8983/solr/mycore``).
          A ``UserWarning`` is issued if the path does not contain ``/solr``.
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
      * - ``retry_delay``
        - Base delay in seconds between retries. Uses exponential backoff:
          first retry waits ``retry_delay``, second waits ``retry_delay * 2``,
          etc. Defaults to ``0.1``. Each retry is logged at WARNING level.
      * - ``always_commit``
        - If ``True``, all update methods (``add``, ``add_many``, ``delete``, etc.)
          will automatically commit changes. Individual calls can override this by
          passing ``commit=False``. Defaults to ``False``.
      * - ``response_format``
        - Response format for queries: ``'json'`` (default) or ``'xml'``.
          When ``'json'``, queries use ``wt=json`` and the JSON parser.
          Use ``'xml'`` for legacy compatibility with older code.
      * - ``auth_token``
        - Bearer token string. Sends ``Authorization: Bearer <token>`` header.
          Takes priority over ``http_user``/``http_pass``.
      * - ``auth``
        - A callable returning a ``dict[str, str]`` of headers. Called on every
          request, enabling dynamic token refresh (e.g., OAuth2). Takes priority
          over ``auth_token`` and ``http_user``/``http_pass``.
      * - ``debug``
        - If ``True``, log all requests and responses.

   **Attributes:**

   .. attribute:: Solr.server_version

      Tuple representing the detected Solr version, e.g. ``(9, 4, 1)``.
      Automatically populated during initialization.

   .. attribute:: Solr.always_commit

      Boolean indicating whether update methods auto-commit by default.

   .. attribute:: Solr.select

      A :class:`SearchHandler` instance bound to the ``/select`` endpoint.

   **Health check:**

   .. method:: Solr.ping()

      Ping the Solr server to check if it is reachable.

      Returns ``True`` if the server responds to ``/admin/ping``,
      ``False`` otherwise. Tries both the core path and its parent path.

      Works on all Solr versions (1.2+).

      Example::

          conn = solr.Solr('http://localhost:8983/solr/mycore')
          if conn.ping():
              print('Solr is up')

   **Search methods:**

   The ``select`` attribute is the primary search interface. See
   :class:`SearchHandler` for details::

       response = conn.select('title:lucene')

   **Update methods:**

   .. automethod:: solr.Solr.add(doc)
   .. automethod:: solr.Solr.add_many(docs)

   **Atomic update methods (Solr 4.0+):**

   .. method:: Solr.atomic_update(doc, commit=False)

      Partial update of a single document. Field values can be plain values
      or dicts with a modifier key: ``set``, ``add``, ``remove``,
      ``removeregex`` (Solr 5.0+), ``inc``. Use ``{'set': None}`` to remove
      a field.

      Example::

          conn.atomic_update({
              'id': 'doc1',
              'title': {'set': 'New Title'},
              'count': {'inc': 1},
              'old_field': {'set': None},  # remove field
          }, commit=True)

   .. method:: Solr.atomic_update_many(docs, commit=False)

      Partial update of multiple documents. Same modifier syntax as
      ``atomic_update``.

   **Real-time Get (Solr 4.0+):**

   .. method:: Solr.get(id=None, ids=None, fields=None)

      Retrieve documents directly from the transaction log without waiting
      for a commit. Returns a dict for single ``id`` (or ``None`` if not
      found), or a list for ``ids``.

      :param id: Single document ID.
      :param ids: List of document IDs.
      :param fields: Optional list of fields to return.

   **Cursor pagination (Solr 4.7+):**

   .. method:: Solr.iter_cursor(q, sort, rows=100, **params)

      Generator that yields :class:`Response` objects for each batch of
      cursor-paginated results. Stops when all results are consumed.

      :param q: Query string.
      :param sort: Sort clause (must include uniqueKey field).
      :param rows: Batch size per request.
      :raises ValueError: If ``sort`` is not provided.

   **MoreLikeThis (Solr 4.0+):**

   Create a :class:`MoreLikeThis` instance::

       from solr import MoreLikeThis

       mlt = MoreLikeThis(conn)
       response = mlt('interesting text', fl='title,body')

.. class:: MoreLikeThis(conn)

   Find similar documents using Solr's ``/mlt`` handler.

   :param conn: A :class:`Solr` instance.

   .. method:: __call__(q=None, **params)

      Query the MLT handler. Same parameters as :class:`SearchHandler`.

   .. method:: raw(**params)

      Issue a raw MLT query.

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
commits. These arguments are always optional; when ``always_commit`` is
``False`` (the default), no commit is performed unless explicitly requested.

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Argument
     - Description
   * - ``commit``
     - If ``True``, commit changes before returning. When ``always_commit``
       is ``True`` on the connection, this defaults to ``True`` but can be
       overridden with ``commit=False``.
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

All update methods and ``SearchHandler`` calls also accept a ``timeout``
keyword argument to override the connection-level timeout for that
individual request.


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
   :param json_facet: JSON Facet API dict (Solr 5.0+). Serialized to ``json.facet``
                      query parameter automatically.
   :param params: Additional Solr parameters (use underscores for dots).
   :param timeout: Per-request timeout in seconds (overrides connection-level timeout).
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

   **Cursor pagination (Solr 4.7+):**

   .. method:: Response.cursor_next()

      Follow cursor-based pagination. Returns the next page of results,
      or ``None`` if no more results (``nextCursorMark == cursorMark``)
      or if the query did not use ``cursorMark``.

      Example::

          resp = conn.select('*:*', sort='id asc', cursorMark='*', rows=100)
          while resp:
              process(resp.results)
              resp = resp.cursor_next()

   **Offset pagination methods:**

   .. method:: Response.next_batch()

      Fetch the next batch of results. Returns a new :class:`Response`,
      or ``None`` if there are no more results.

   .. method:: Response.previous_batch()

      Fetch the previous batch of results. Returns a new :class:`Response`,
      or ``None`` if this is the first batch.

   **Grouping (Solr 3.3+):**

   .. attribute:: Response.grouped

      A :class:`GroupedResult` object when the response contains grouped
      results, otherwise not present. Enable grouping with ``group='true'``
      and ``group_field='field'``.

      Example::

          resp = conn.select('*:*', group='true', group_field='category',
                             group_limit=5, group_ngroups='true')
          for group in resp.grouped['category'].groups:
              print(group.groupValue, len(group.doclist))

   **Spellcheck (Solr 1.4+):**

   .. attribute:: Response.spellcheck

      A :class:`SpellcheckResult` object if the response contains spellcheck
      data, otherwise ``None``. Spellcheck data is returned when you include
      ``spellcheck='true'`` in the query parameters.

      Example::

          resp = conn.select('misspeled query', spellcheck='true',
                             spellcheck_collate='true')
          if resp.spellcheck and not resp.spellcheck.correctly_spelled:
              print('Did you mean:', resp.spellcheck.collation)

   **Iteration:**

   Response objects support ``len()`` and iteration::

       response = conn.select('*:*')
       print(len(response))
       for doc in response:
           print(doc['id'])


SpellcheckResult class (Solr 1.4+)
------------------------------------

.. class:: SpellcheckResult(raw)

   Wrapper around the raw spellcheck response dict. Returned by
   ``Response.spellcheck`` when the query includes ``spellcheck=true``.

   :param raw: The raw spellcheck dict from the Solr response.

   .. attribute:: SpellcheckResult.correctly_spelled

      ``True`` if all query terms were spelled correctly.

   .. attribute:: SpellcheckResult.collation

      The corrected full query string suggested by Solr (collation), or
      ``None`` if not present. Requires ``spellcheck.collate=true`` on the
      request.

   .. attribute:: SpellcheckResult.suggestions

      List of per-word suggestion entries. Each entry is a dict that includes
      an ``'original'`` key (the misspelled word) merged with the Solr info
      dict (``'numFound'``, ``'startOffset'``, ``'endOffset'``,
      ``'suggestion'`` list, etc.).

      Example::

          for entry in resp.spellcheck.suggestions:
              print(entry['original'], '->', entry.get('suggestion', []))


Extract class (Solr 1.4+)
--------------------------

.. class:: Extract(conn)

   Index or extract rich documents via Solr Cell (Apache Tika) using the
   ``/update/extract`` handler. The handler must be configured in
   ``solrconfig.xml``.

   :param conn: A :class:`Solr` instance.

   .. method:: __call__(file_obj, content_type='application/octet-stream', commit=False, **params)

      Index a rich document.

      :param file_obj: Binary file-like object (opened in ``'rb'`` mode).
      :param content_type: MIME type of the document. Defaults to
          ``'application/octet-stream'``.
      :param commit: Commit to the index immediately. Defaults to ``False``.
      :param params: Additional Solr parameters. The **first** underscore in
          each key is replaced with a dot: ``literal_id='x'`` →
          ``literal.id=x``. Field names with underscores are preserved:
          ``literal_my_field='v'`` → ``literal.my_field=v``.
      :returns: Parsed JSON response dict (contains ``responseHeader``).
      :raises SolrVersionError: If the server is older than Solr 1.4.

      Example::

          from solr import Solr, Extract

          conn = Solr('http://localhost:8983/solr/mycore')
          ext = Extract(conn)

          with open('report.pdf', 'rb') as f:
              ext(f, content_type='application/pdf',
                  literal_id='report1', literal_title='Annual Report',
                  commit=True)

   .. method:: extract_only(file_obj, content_type='application/octet-stream', **params)

      Extract text and metadata without indexing.

      Calls ``/update/extract`` with ``extractOnly=true``.

      :returns: ``(text, metadata)`` tuple. *text* is the extracted plain
          text; *metadata* is a dict of Tika metadata (e.g.
          ``'Content-Type'``, ``'Author'``, ``'title'``).

   .. method:: from_path(file_path, **params)

      Index a document from a filesystem path. MIME type is guessed from
      the file extension via :mod:`mimetypes`; falls back to
      ``'application/octet-stream'``.

      :param file_path: Path to the file.
      :param params: Forwarded to :meth:`__call__` (``commit``,
          ``literal_*``, etc.).

   .. method:: extract_from_path(file_path, **params)

      Extract text and metadata from a file path without indexing.

      :returns: ``(text, metadata)`` tuple (same as :meth:`extract_only`).


Suggest class (Solr 4.7+)
---------------------------

.. class:: Suggest(conn)

   Query Solr's SuggestComponent via the ``/suggest`` handler.

   The ``/suggest`` handler and at least one ``SuggestComponent`` must be
   configured in ``solrconfig.xml``.

   :param conn: A :class:`Solr` instance.

   .. method:: __call__(q, dictionary=None, count=10, **params)

      Return a flat list of suggestion dicts for the query term.

      :param q: Partial query string to suggest for.
      :param dictionary: Name of the suggester dictionary to use. If ``None``,
          Solr uses the default suggester.
      :param count: Maximum number of suggestions to return. Defaults to ``10``.
      :param params: Extra parameters forwarded verbatim to ``/suggest``.
      :returns: List of suggestion dicts. Each dict typically has ``'term'``,
          ``'weight'``, and ``'payload'`` keys.
      :raises SolrVersionError: If the server is older than Solr 4.7.

      Example::

          from solr import Solr, Suggest

          conn = Solr('http://localhost:8983/solr/mycore')
          suggest = Suggest(conn)
          results = suggest('que', dictionary='mySuggester', count=5)
          for s in results:
              print(s['term'], s['weight'])


Grouping classes (Solr 3.3+)
-----------------------------

.. class:: GroupedResult(raw)

   Wrapper around a Solr grouped response. Supports subscript access
   by field name, iteration, ``in``, and ``len()``.

   .. method:: __getitem__(field)

      Return a :class:`GroupField` for the given field name.

.. class:: GroupField(raw)

   Grouped results for a single field.

   .. attribute:: matches

      Total number of documents matching the query across all groups.

   .. attribute:: ngroups

      Number of distinct groups, or ``None`` if ``group.ngroups`` was not
      requested.

   .. attribute:: groups

      List of :class:`Group` objects.

.. class:: Group(raw)

   A single group.

   .. attribute:: groupValue

      The field value that defines this group, or ``None``.

   .. attribute:: doclist

      A :class:`Results` list of matching documents, with ``numFound``
      and ``start`` attributes.


KNN / Dense Vector Search (Solr 9.0+)
---------------------------------------

.. class:: KNN(conn)

   Dense Vector / KNN Search using Solr's ``{!knn}`` query parser.
   Created explicitly by the user.

   :param conn: A :class:`Solr` instance.

   .. method:: __call__(vector, field, top_k, filters=None, ef_search_scale_factor=None, **params)

      Execute a KNN search query.

      :param vector: Dense vector as a sequence of floats.
      :param field: Name of the ``DenseVectorField`` to search.
      :param top_k: Number of nearest neighbors to retrieve.
      :param filters: Optional filter query (``fq`` parameter).
      :param ef_search_scale_factor: Solr 10.0+ parameter to tune search
          accuracy independently from result count.
      :returns: A :class:`Response` instance.
      :raises SolrVersionError: If connected Solr is older than 9.0.

   .. method:: build_query(vector, field, top_k, ef_search_scale_factor=None)

      Build a ``{!knn}`` query string without executing it.

   Example::

       from solr import Solr, KNN

       conn = Solr('http://localhost:8983/solr/mycore')
       knn = KNN(conn)
       response = knn([0.1, 0.2, 0.3, ...], field='embedding', top_k=10)
       for doc in response.results:
           print(doc['id'], doc.get('score'))

       # Solr 10.0+: tune search accuracy
       response = knn([0.1, 0.2], field='embedding', top_k=10,
                      ef_search_scale_factor=2.0)


Schema API (Solr 4.2+)
-----------------------

.. class:: SchemaAPI

   Created explicitly by the user. All methods require Solr 4.2+.

   Example::

       from solr import Solr, SchemaAPI

       conn = Solr('http://localhost:8983/solr/mycore')
       schema = SchemaAPI(conn)
       fields = schema.fields()

   **Full schema:**

   .. method:: SchemaAPI.get_schema()

      Return the full schema definition as a dict.

   **Field operations:**

   .. method:: SchemaAPI.fields()

      List all fields. Returns a list of field definition dicts.

   .. method:: SchemaAPI.add_field(name, field_type, **opts)

      Add a new field. Example::

          conn.schema.add_field('title', 'text_general', stored=True, indexed=True)

   .. method:: SchemaAPI.replace_field(name, field_type, **opts)

      Replace an existing field definition.

   .. method:: SchemaAPI.delete_field(name)

      Delete a field by name.

   **Dynamic field operations:**

   .. method:: SchemaAPI.dynamic_fields()
   .. method:: SchemaAPI.add_dynamic_field(name, field_type, **opts)
   .. method:: SchemaAPI.delete_dynamic_field(name)

   **Field type operations:**

   .. method:: SchemaAPI.field_types()
   .. method:: SchemaAPI.add_field_type(**definition)
   .. method:: SchemaAPI.replace_field_type(**definition)
   .. method:: SchemaAPI.delete_field_type(name)

   **Copy field operations:**

   .. method:: SchemaAPI.copy_fields()
   .. method:: SchemaAPI.add_copy_field(source, dest, max_chars=None)
   .. method:: SchemaAPI.delete_copy_field(source, dest)


Paginator
---------

.. class:: SolrPaginator(result, default_page_size=None)

   Paginator for a Solr response object. Provides Django-like pagination
   without any Django dependency.

   :param result: A :class:`Response` instance from a query.
   :param default_page_size: Override the page size. If not given, uses the
                              ``rows`` parameter from the query, or the number
                              of results returned.

   .. attribute:: count

      Total number of matching documents.

   .. attribute:: num_pages

      Total number of pages.

   .. attribute:: page_range

      A ``range`` of valid page numbers.

   .. method:: page(page_num=1)

      Return a :class:`SolrPage` for the given page number.

      :raises PageNotAnInteger: If ``page_num`` cannot be converted to int.
      :raises EmptyPage: If ``page_num`` is out of range.

.. class:: SolrPage

   A single page of results.

   .. attribute:: object_list

      List of documents on this page.

   .. method:: has_next()
   .. method:: has_previous()
   .. method:: has_other_pages()
   .. method:: next_page_number()
   .. method:: previous_page_number()
   .. method:: start_index()
   .. method:: end_index()

.. class:: EmptyPage

   Raised when the requested page is out of range. Subclass of :class:`ValueError`.

.. class:: PageNotAnInteger

   Raised when the page number is not an integer. Subclass of :class:`TypeError`.


Response parsing
----------------

solrpy provides two response parsers:

.. function:: solr.core.parse_query_response(data, params, query)

   Parse an XML response from Solr (``wt=standard`` or ``wt=xml``).

   :param data: A file-like object containing the XML response.
   :param params: Dictionary of query parameters used for the request.
   :param query: The :class:`SearchHandler` that issued the query (used for
                 ``next_batch()`` / ``previous_batch()``).
   :returns: A :class:`Response` instance, or ``None`` if the response is empty.

   This is the default parser used by :class:`SearchHandler`.

.. function:: solr.core.parse_json_response(data, params, query)

   Parse a JSON response dict from Solr (``wt=json``).

   :param data: A dictionary (already deserialized from JSON).
   :param params: Dictionary of query parameters used for the request.
   :param query: The :class:`SearchHandler` that issued the query.
   :returns: A :class:`Response` instance.

   Handles all standard Solr response fields: ``responseHeader``,
   ``response`` (docs, numFound, start, maxScore), and any additional
   top-level keys such as ``highlighting``, ``facet_counts``, ``stats``,
   ``debug``, etc. Extra keys are attached directly as Response attributes.

   Example usage with a raw JSON query::

       import json
       import solr
       from solr.core import parse_json_response

       conn = solr.Solr('http://localhost:8983/solr/mycore')
       raw = conn.select.raw(q='*:*', wt='json')
       data = json.loads(raw)
       response = parse_json_response(data, {'q': '*:*'}, conn.select)


Gzip compression
----------------

All requests include an ``Accept-Encoding: gzip`` header. When the Solr
server returns a gzip-compressed response, it is transparently decompressed
before parsing.

This reduces network transfer size, especially for large result sets.
No configuration is needed; gzip support is always enabled.

.. function:: solr.core.read_response(response)

   Read an HTTP response body, decompressing gzip if the
   ``Content-Encoding`` header indicates compression.

   :param response: An :class:`http.client.HTTPResponse` object.
   :returns: Decoded string (UTF-8).
