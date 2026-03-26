Quick Start
===========

Installation
------------

Install via pip::

    pip install solrpy

Or with Poetry::

    poetry add solrpy


Connecting to Solr
------------------

Create a connection by providing the URL to your Solr core::

    import solr

    conn = solr.Solr('http://localhost:8983/solr/mycore')

The connected Solr version is auto-detected::

    print(conn.server_version)  # e.g. (9, 4, 1)

.. note::

   If the URL does not contain ``/solr`` in its path, a ``UserWarning``
   is issued. Solr 10.0+ requires the URL to end with ``/solr``.


Health check
------------

Check if the server is reachable::

    if conn.ping():
        print('Solr is up')
    else:
        print('Solr is unreachable')


Adding documents
----------------

Add a single document::

    doc = {
        'id': '1',
        'title': 'Lucene in Action',
        'author': ['Erik Hatcher', 'Otis Gospodnetić'],
    }
    conn.add(doc, commit=True)

Add multiple documents at once::

    docs = [
        {'id': '2', 'title': 'Solr in Action'},
        {'id': '3', 'title': 'Elasticsearch: The Definitive Guide'},
    ]
    conn.add_many(docs, commit=True)


Auto-commit mode
~~~~~~~~~~~~~~~~

If you want all updates to commit automatically, use the ``always_commit``
option::

    conn = solr.Solr('http://localhost:8983/solr/mycore', always_commit=True)

    # these will auto-commit without passing commit=True
    conn.add({'id': '4', 'title': 'Auto-committed document'})
    conn.delete(id='4')

You can override on individual calls::

    # suppress auto-commit for this one call
    conn.add({'id': '5', 'title': 'Deferred'}, commit=False)


Searching
---------

Perform a query using the ``select`` handler::

    response = conn.select('title:lucene')

    print(response.numFound)       # total matches
    print(response.results.start)  # starting offset

    for doc in response.results:
        print(doc['id'], doc['title'])


Faceting
~~~~~~~~

Pass Solr parameters using underscore notation (dots become underscores)::

    response = conn.select(
        'title:lucene',
        facet='true',
        facet_field='subject',
    )

For parameters that accept multiple values, pass a list::

    response = conn.select(
        'title:lucene',
        facet='true',
        facet_field=['subject', 'publisher'],
    )


Highlighting
~~~~~~~~~~~~

Enable highlighting for specific fields::

    response = conn.select(
        'title:lucene',
        highlight=['title', 'body'],
    )

    # highlighting data is available on the response
    print(response.highlighting)

Or highlight all returned fields by passing ``True``::

    response = conn.select(
        'title:lucene',
        fields=['title', 'body'],
        highlight=True,
    )


Sorting
~~~~~~~

Sort results by one or more fields::

    response = conn.select('*:*', sort='title asc')

    # multiple sort fields
    response = conn.select('*:*', sort=['date desc', 'title asc'])


Pagination
~~~~~~~~~~

Use ``next_batch()`` and ``previous_batch()`` for offset-based pagination::

    response = conn.select('*:*', rows=10)

    # get the next 10 results
    next_page = response.next_batch()

    # go back
    prev_page = next_page.previous_batch()


Atomic update (Solr 4.0+)
--------------------------

Update specific fields without resending the entire document::

    conn.atomic_update({
        'id': 'doc1',
        'title': {'set': 'Updated Title'},
        'view_count': {'inc': 1},
        'old_field': {'set': None},  # remove field
    }, commit=True)

Batch atomic updates::

    conn.atomic_update_many([
        {'id': 'doc1', 'status': {'set': 'published'}},
        {'id': 'doc2', 'status': {'set': 'draft'}},
    ], commit=True)


Real-time Get (Solr 4.0+)
--------------------------

Retrieve documents directly from the transaction log without waiting for
a commit::

    doc = conn.get(id='doc1')
    docs = conn.get(ids=['doc1', 'doc2'], fields=['id', 'title'])


Soft Commit (Solr 4.0+)
-------------------------

Make changes visible without flushing to disk::

    conn.commit(soft_commit=True)


MoreLikeThis (Solr 4.0+)
--------------------------

Find similar documents by creating a handler for ``/mlt``::

    mlt = solr.SearchHandler(conn, '/mlt')
    response = mlt('interesting text', fl='title,body')


JSON Facet API (Solr 5.0+)
---------------------------

Use the ``json_facet`` parameter for advanced faceting::

    response = conn.select('*:*', json_facet={
        'categories': {
            'type': 'terms',
            'field': 'category',
            'limit': 10,
        },
    })

    # Access facet results
    print(response.facets['categories'])

Works in both JSON and XML response modes.


Cursor pagination (Solr 4.7+)
------------------------------

For large result sets, use cursor-based deep pagination::

    resp = conn.select('*:*', sort='id asc', cursorMark='*', rows=100)
    while resp:
        for doc in resp.results:
            process(doc)
        resp = resp.cursor_next()

Or use the convenience generator::

    for batch in conn.iter_cursor('*:*', sort='id asc', rows=100):
        for doc in batch.results:
            process(doc)

.. note::

   The ``sort`` clause must include the uniqueKey field (usually ``id``).


Deleting documents
------------------

Delete by ID::

    conn.delete(id='1', commit=True)

Delete multiple IDs::

    conn.delete(ids=['1', '2', '3'], commit=True)

Delete by query::

    conn.delete_query('title:obsolete', commit=True)


Committing and optimizing
--------------------------

Issue a commit to make changes visible::

    conn.commit()

Commit with optimization::

    conn.commit(_optimize=True)

Or call optimize directly::

    conn.optimize()


Response format
---------------

Since v1.0.4, solrpy uses JSON (``wt=json``) by default. This matches
Solr 7.0+ where JSON is the native default format.

If you need XML mode for legacy compatibility::

    conn = solr.Solr('http://localhost:8983/solr/mycore', response_format='xml')

The ``Response`` object API is identical regardless of format
(``results``, ``header``, ``numFound``, ``highlighting``, etc.).


Using SearchHandler
-------------------

The ``select`` attribute on a ``Solr`` instance is a :class:`~solr.SearchHandler`.
You can create additional handlers for custom Solr request handlers::

    import solr

    conn = solr.Solr('http://localhost:8983/solr/mycore')

    # use the default /select handler
    response = conn.select('title:lucene')

    # create a handler for a custom endpoint
    find_stuff = solr.SearchHandler(conn, '/find_stuff')
    response = find_stuff('title:lucene')

For raw, unprocessed queries::

    xml = conn.select.raw(q='id:1', wt='xml', indent='on')


Schema API (Solr 4.2+)
-----------------------

Create a ``SchemaAPI`` instance to manage schema programmatically::

    from solr import SchemaAPI

    schema = SchemaAPI(conn)

    # List fields
    fields = schema.fields()

    # Add a field
    schema.add_field('title', 'text_general', stored=True, indexed=True)

    # Replace a field type
    schema.replace_field('title', 'string')

    # Delete a field
    schema.delete_field('title')

    # Copy fields
    schema.add_copy_field('title', 'title_str')
    schema.delete_copy_field('title', 'title_str')

    # Full schema dump
    full = schema.get_schema()


Closing the connection
----------------------

When you are done, close the connection::

    conn.close()
