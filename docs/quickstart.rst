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


Legacy SolrConnection
---------------------

The ``SolrConnection`` class provides backward compatibility with older
applications. New code should use ``Solr`` instead.

==================== ==============================
SolrConnection       Solr equivalent
==================== ==============================
``conn.add(**doc)``  ``conn.add(doc)``
``conn.query(q)``    ``conn.select(q)``
``conn.raw_query()`` ``conn.select.raw()``
==================== ==============================


Closing the connection
----------------------

When you are done, close the connection::

    conn.close()
