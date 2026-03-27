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

Find similar documents::

    from solr import MoreLikeThis

    mlt = MoreLikeThis(conn)
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


Grouping / Field Collapsing (Solr 3.3+)
-----------------------------------------

Group results by a field value::

    resp = conn.select('*:*', group='true', group_field='category',
                       group_limit=5, group_ngroups='true')

    for group in resp.grouped['category'].groups:
        print(group.groupValue, ':', len(group.doclist), 'docs')
        for doc in group.doclist:
            print('  ', doc['id'])

    print('Total matches:', resp.grouped['category'].matches)
    print('Distinct groups:', resp.grouped['category'].ngroups)


KNN / Dense Vector Search (Solr 9.0+)
---------------------------------------

Search by vector similarity using Solr's ``DenseVectorField``::

    from solr import KNN

    knn = KNN(conn)
    response = knn(
        [0.1, 0.2, 0.3, 0.4, 0.5],
        field='embedding',
        top_k=10,
    )
    for doc in response.results:
        print(doc['id'], doc.get('score'))

With filter queries::

    response = knn([0.1, 0.2, 0.3], field='embedding', top_k=10,
                   filters='category:books')

Solr 10.0+ accuracy tuning::

    response = knn([0.1, 0.2], field='embedding', top_k=10,
                   ef_search_scale_factor=2.0)


Query builders (Field, Sort, Facet)
------------------------------------

Use builder objects for structured query parameters, or keep using raw strings::

    from solr import Field, Sort, Facet

    response = conn.select('*:*',
        fields=[
            Field('id'),
            Field('price', alias='price_usd'),
            Field.func('sum', 'price', 'tax'),
            Field.score(),
        ],
        sort=[Sort('price', 'desc'), Sort('id', 'asc')],
        facets=[
            Facet.field('category', mincount=1, limit=10),
            Facet.range('price', start=0, end=100, gap=10),
        ],
    )

Raw strings still work — builders are an optional alternative::

    # This is equivalent and will always be supported
    conn.select('*:*', fl='id,price_usd:price,sum(price,tax),score',
                sort='price desc,id asc',
                facet='true', facet_field='category')


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


Solr Extract / Rich Documents (Solr 1.4+)
------------------------------------------

Index rich documents (PDF, Word, HTML, etc.) using Solr Cell (Apache Tika).
The ``/update/extract`` handler must be configured in ``solrconfig.xml``::

    from solr import Extract

    extract = Extract(conn)

    # Index a PDF with literal field values; use underscore for dot notation
    with open('report.pdf', 'rb') as f:
        extract(f, content_type='application/pdf',
                literal_id='report1',
                literal_title='Annual Report',
                commit=True)

    # Extract text and metadata without indexing
    with open('report.pdf', 'rb') as f:
        text, metadata = extract.extract_only(f, content_type='application/pdf')
    print(text[:200])
    print(metadata.get('Content-Type'))

    # Open a file by path — MIME type is guessed from the extension
    extract.from_path('document.docx', literal_id='doc1', commit=True)
    text, metadata = extract.extract_from_path('notes.txt')

Use ``commit=True`` to commit after indexing, or call ``conn.commit()`` later.
Field names with underscores are preserved: ``literal_my_field='v'`` →
``literal.my_field=v``.


Suggest (Solr 4.7+)
--------------------

Query Solr's SuggestComponent for auto-complete suggestions. The ``/suggest``
handler and a ``SuggestComponent`` must be configured in ``solrconfig.xml``::

    from solr import Suggest

    suggest = Suggest(conn)
    results = suggest('que', dictionary='mySuggester', count=5)
    for s in results:
        print(s['term'], s['weight'])

Omit ``dictionary`` to use the Solr default suggester. Pass extra parameters
as keyword arguments (forwarded verbatim to the ``/suggest`` handler)::

    results = suggest('q', count=10, suggest_build='true')


Spellcheck (Solr 1.4+)
------------------------

Activate the SpellCheckComponent by adding ``spellcheck=true`` to a query.
The response exposes a ``SpellcheckResult`` via ``response.spellcheck``::

    resp = conn.select(
        'misspeled query',
        spellcheck='true',
        spellcheck_collate='true',
        spellcheck_count='5',
    )

    if resp.spellcheck:
        if not resp.spellcheck.correctly_spelled:
            print('Did you mean:', resp.spellcheck.collation)
        for entry in resp.spellcheck.suggestions:
            print(entry['original'], '->', entry.get('suggestion', []))

Works in both JSON and XML response modes.


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


Authentication
--------------

**Basic auth** (username/password)::

    conn = solr.Solr(url, http_user='admin', http_pass='secret')

**Bearer token** (JWT, API key, etc.)::

    conn = solr.Solr(url, auth_token='my-jwt-token')

**Custom auth callable** (OAuth2 with dynamic refresh)::

    def get_oauth_headers():
        token = refresh_my_token()  # your logic
        return {'Authorization': 'Bearer ' + token}

    conn = solr.Solr(url, auth=get_oauth_headers)

Priority: ``auth`` callable > ``auth_token`` > ``http_user/http_pass``.


SolrCloud
---------

Install ZooKeeper support::

    pip install solrpy[cloud]

**With ZooKeeper** (real-time node discovery via ``kazoo``)::

    from solr import SolrZooKeeper, SolrCloud

    zk = SolrZooKeeper('zk1:2181,zk2:2181,zk3:2181')
    cloud = SolrCloud(zk, collection='products')

    # Reads go to any active replica (automatic failover)
    response = cloud.select('category:books', rows=20)

    # Writes are routed to shard leaders
    cloud.add({'id': '1', 'title': 'Solr in Action'}, commit=True)
    cloud.delete(id='1', commit=True)

    cloud.close()
    zk.close()

**Without ZooKeeper** (HTTP-only, no extra dependencies)::

    from solr import SolrCloud

    cloud = SolrCloud.from_urls(
        ['http://solr1:8983/solr', 'http://solr2:8983/solr'],
        collection='products')

    response = cloud.select('*:*')
    cloud.close()

Pass connection options (timeout, auth, SSL) via ``**solr_kwargs``::

    cloud = SolrCloud(zk, collection='secure',
                      timeout=10,
                      auth_token='my-jwt-token')

Failover retries default to 3 with exponential backoff::

    # Customize retry behavior
    cloud = SolrCloud(zk, collection='products',
                      retry_count=5, retry_delay=1.0)


Using SolrZooKeeper directly
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can also use ``SolrZooKeeper`` independently for cluster inspection::

    from solr import SolrZooKeeper

    zk = SolrZooKeeper('zk1:2181,zk2:2181')

    # List active nodes
    print(zk.live_nodes())
    # ['solr1:8983_solr', 'solr2:8983_solr', 'solr3:8983_solr']

    # Get all replica URLs for a collection
    replicas = zk.replica_urls('products')
    # ['http://solr1:8983/solr', 'http://solr2:8983/solr']

    # Get shard leader URLs (one per shard)
    leaders = zk.leader_urls('products')
    # ['http://solr1:8983/solr']

    # Check collection aliases
    aliases = zk.aliases()
    # {'prod': 'products_v2', 'staging': 'products_v1'}

    # Aliases are resolved automatically in replica_urls/leader_urls
    zk.replica_urls('prod')  # same as zk.replica_urls('products_v2')

    # Inspect collection state (shards, replicas, router)
    state = zk.collection_state('products')
    for shard, data in state['shards'].items():
        print(shard, len(data['replicas']), 'replicas')

    zk.close()


Pydantic response models
-------------------------

Convert search results to typed Pydantic models (``pip install solrpy[pydantic]``)::

    from pydantic import BaseModel

    class Product(BaseModel):
        id: str
        title: str
        price: float
        category: str | None = None

    # Automatic conversion via model= parameter
    resp = conn.select('category:books', model=Product)
    for p in resp.results:
        print(p.title, p.price)  # IDE autocomplete, type safe

    # Real-time Get
    doc = conn.get(id='prod1', model=Product)  # Product | None

    # Post-hoc conversion
    resp = conn.select('*:*')
    products = resp.as_models(Product)


Async usage
-----------

Use ``AsyncSolr`` for async/await support (e.g. in FastAPI, aiohttp)::

    from solr import AsyncSolr

    async with AsyncSolr('http://localhost:8983/solr/mycore') as conn:
        response = await conn.select('*:*')
        for doc in response.results:
            print(doc['id'])

Unified sync/async companions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since 2.0.4, all companion classes work with both ``Solr`` and ``AsyncSolr``.
No need for separate ``AsyncSchemaAPI``, ``AsyncKNN``, etc.::

    from solr import Solr, AsyncSolr, SchemaAPI, KNN

    # Sync
    conn = Solr('http://localhost:8983/solr/mycore')
    schema = SchemaAPI(conn)
    fields = schema.fields()

    # Async — same class, returns coroutines
    async with AsyncSolr('http://localhost:8983/solr/mycore') as conn:
        schema = SchemaAPI(conn)
        fields = await schema.fields()

The ``AsyncSchemaAPI``, ``AsyncKNN``, ``AsyncMoreLikeThis``,
``AsyncSuggest``, and ``AsyncExtract`` names are kept as backward-compatible
aliases.


Closing the connection
----------------------

When you are done, close the connection::

    conn.close()
