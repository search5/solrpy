Changelog
=========

2.0.1 (2026-03-27)
-------------------

**Breaking: httpx migration**

- Replaced ``http.client`` with ``httpx.Client`` as the HTTP transport.
- ``httpx`` is now a **required dependency**.
- Automatic **connection pooling** and keep-alive via httpx.
- Gzip decompression handled automatically by httpx.
- Retry exceptions changed: ``socket.error``/``BadStatusLine`` → ``httpx.ConnectError``/``httpx.ReadError``.
- ``Solr.conn`` is now an ``httpx.Client`` instance (was ``http.client.HTTPConnection``).
- All public API unchanged — **drop-in replacement** for 1.x users.


1.12.0 (2026-03-27)
--------------------

**New features (Solr 5.0+):**

- **Streaming Expressions**: Pythonic builder for Solr streaming expressions.
  No other non-Java client supports this.
- Python functions map 1:1 to Solr expression functions: ``search``, ``merge``,
  ``rollup``, ``top``, ``unique``, ``innerJoin``, ``leftOuterJoin``, etc.
- Aggregate functions: ``count``, ``sum``, ``avg``, ``min``, ``max``.
- **Pipe (``|``) operator** for chaining expressions.
- ``Solr.stream(expr)`` executes via ``/stream`` handler, returns iterator.
- ``model=`` parameter for Pydantic conversion on stream results.
- Tested against live SolrCloud 9.7.


1.11.0 (2026-03-27)
--------------------

**New features:**

- **Pydantic response models** (opt-in, ``pip install solrpy[pydantic]``):
  - ``model=`` parameter on ``select()`` and ``get()`` — automatically
    converts result documents to Pydantic ``BaseModel`` instances.
  - ``Response.as_models(model)`` method for post-hoc conversion.
  - Pydantic v2 support (``model_validate()``).
  - Works in both JSON and XML response modes.
  - ``pydantic`` added as optional dependency.


1.10.1 (2026-03-27)
--------------------

**New features:**

- **``Field`` builder** (``solr/field.py``): Structured field list expressions
  for the ``fl`` parameter. Supports aliases (``Field('price', alias='p')``),
  functions (``Field.func('sum', 'price', 'tax')``), document transformers
  (``Field.transformer('explain')``), and score (``Field.score()``).
- **``Sort`` builder** (``solr/sort.py``): Structured sort clauses.
  ``Sort('price', 'desc')``, ``Sort.func('geodist()', 'asc')``.
- **``Facet`` builder** (``solr/facet.py``): Structured traditional facets.
  ``Facet.field('category', mincount=1)``, ``Facet.range('price', 0, 100, 10)``,
  ``Facet.query('cheap', 'price:[0 TO 50]')``, ``Facet.pivot('cat', 'author')``.
- **``facets=`` parameter** on ``SearchHandler.__call__``: accepts list of
  ``Facet`` objects, auto-merges params.
- All builders coexist with raw string parameters — **fully backward compatible**.
- ``Field``, ``Sort``, ``Facet`` exported from top-level ``solr`` package.


1.10.0 (2026-03-27)
--------------------

**New features (Solr 4.0+):**

- **SolrCloud support** with two modes:

  - **ZooKeeper mode**: ``SolrZooKeeper`` class in ``solr/zookeeper.py``
    connects to ZooKeeper for real-time node discovery, leader identification,
    and collection alias resolution. Requires ``kazoo`` (``pip install solrpy[cloud]``).
  - **HTTP mode**: ``SolrCloud.from_urls()`` uses the CLUSTERSTATUS API for
    node discovery without ZooKeeper. No extra dependencies.

- **``SolrCloud`` class** in ``solr/cloud.py``:

  - Leader-aware writes: update requests routed to shard leaders.
  - Automatic failover: on error, retries with a different node (exponential backoff).
  - Same API as ``Solr``: ``select()``, ``add()``, ``delete()``, ``commit()``, etc.

- **``SolrZooKeeper`` class** in ``solr/zookeeper.py``:

  - ``live_nodes()`` — active node list
  - ``collection_state(name)`` — shard/replica state
  - ``leader_urls(collection)`` / ``replica_urls(collection)``
  - ``random_url(collection)`` / ``random_leader_url(collection)``
  - ``aliases()`` — collection alias resolution

- Docker Compose configuration for local SolrCloud testing
  (``docker/docker-compose-cloud.yml``).
- ``kazoo`` added as optional dependency (``extras = ["cloud"]``).


1.9.2 (2026-03-27)
-------------------

**Solr 7~10 compatibility:**

- XML mode now uses ``wt=xml`` on Solr 7+ (``wt=standard`` behavior changed
  in 7.0, removed in 10.0). Solr < 7 continues to use ``wt=standard``.
- All 326 tests pass against live Solr 10.0.
- ``efSearchScaleFactor`` verified on Solr 10.0.
- ``{!vectorSimilarity}`` verified on Solr 10.0.

**Test improvements:**

- KNN live tests self-provision vector data in ``setUp`` (test isolation).
- ``test_raw_query`` uses ``wt=json`` for cross-version portability.
- ``test_select_request`` / ``test_alternate_request`` version-aware assertions.


1.9.1 (2026-03-27)
-------------------

**KNN API overhaul:**

- **``KNN.search()``**: Full ``{!knn}`` parameter support — ``early_termination``,
  ``saturation_threshold``, ``patience``, ``seed_query``, ``pre_filter``,
  ``include_tags``, ``exclude_tags``, ``ef_search_scale_factor``.
- **``KNN.similarity()``**: ``{!vectorSimilarity}`` threshold-based matching
  with ``min_return``, ``min_traverse``, and ``pre_filter`` (Solr 9.6+).
- **``KNN.hybrid()``**: Lexical OR vector combined search.
- **``KNN.rerank()``**: Re-rank lexical results by vector similarity.
- **``build_knn_query()``**, **``build_similarity_query()``**,
  **``build_hybrid_query()``**, **``build_rerank_params()``**: Query string
  builders for custom use cases.
- ``build_query()`` retained as alias for backward compatibility.
- Live integration tests against Solr 9.4 with ``DenseVectorField``.


1.9.0 (2026-03-27)
-------------------

**New features (Solr 9.0+):**

- **KNN / Dense Vector Search**: New ``KNN(conn)`` class in ``solr/knn.py``.
  Builds ``{!knn f=<field> topK=<k>}[v1,v2,...]`` queries and executes them
  via the ``/select`` handler.
- ``KNN.__call__(vector, field, top_k, filters, ...)`` — execute a KNN search.
- ``KNN.build_query(...)`` — build query string without executing.
- ``efSearchScaleFactor`` support for Solr 10.0+ (version-gated).
- All methods version-gated to Solr 9.0+.


1.8.1 (2026-03-27)
-------------------

**Internal refactoring:**

- New ``SolrTransport`` class in ``solr/transport.py``: thin abstraction over
  Solr's HTTP communication (``get_json``, ``post_json``, ``post_raw``).
- ``SchemaAPI``, ``Suggest``, ``Extract`` now use ``SolrTransport`` instead of
  calling ``Solr._get()`` / ``Solr._post()`` directly.
- Eliminates coupling to internal HTTP methods; reduces migration cost for
  the httpx switch planned in 2.0.0.
- No public API changes.


1.8.0 (2026-03-27)
-------------------

**New features:**

- **Bearer token authentication**: ``Solr(url, auth_token='...')`` sends
  ``Authorization: Bearer <token>`` header on every request.
- **Custom auth callable**: ``Solr(url, auth=my_fn)`` calls ``my_fn()`` on
  every request to produce auth headers dynamically. Enables OAuth2 token
  refresh and other dynamic authentication schemes.
- Auth priority: ``auth`` callable > ``auth_token`` > ``http_user/http_pass``.


1.7.0 (2026-03-27)
-------------------

**New features (Solr 3.3+):**

- **Grouping / Field Collapsing**: ``Response.grouped`` attribute returns a
  :class:`GroupedResult` object when grouped results are present.
- :class:`GroupedResult` supports subscript access (``resp.grouped['field']``),
  iteration, ``in`` tests, and ``len()``.
- :class:`GroupField` provides ``.matches``, ``.ngroups``, and ``.groups``
  accessors.
- :class:`Group` provides ``.groupValue`` and ``.doclist`` (a :class:`Results`
  list with ``numFound`` and ``start``).
- Works in both JSON and XML response modes. XML ``<result name="doclist">``
  tags are wrapped into :class:`Results` with normalized integer attributes.


1.6.0 (2026-03-27)
-------------------

**New features (Solr 1.4+):**

- **Extract** class in ``solr/extract.py``: indexes rich documents (PDF, Word,
  HTML, etc.) via Solr Cell (Apache Tika) using the ``/update/extract``
  handler.
- ``Extract.__call__(file_obj, content_type, commit, **params)``: POST binary
  file content to ``/update/extract``. First underscore in each keyword
  argument is replaced with a dot (``literal_id`` → ``literal.id``); field
  names that contain underscores are preserved (``literal_my_field`` →
  ``literal.my_field``).
- ``Extract.extract_only(file_obj, content_type, **params)``: extract text and
  metadata without indexing. Returns ``(text, metadata)`` tuple.
- ``Extract.from_path(file_path, **params)``: open a file by path and index it;
  MIME type guessed via :mod:`mimetypes`.
- ``Extract.extract_from_path(file_path, **params)``: open a file by path and
  extract without indexing.
- ``Extract`` exported from top-level ``solr`` package.


1.5.0 (2026-03-27)
-------------------

**New features:**

- **Suggest** (Solr 4.7+): New ``Suggest(conn)`` wrapper class in ``solr/suggest.py``.
  Queries the ``/suggest`` handler and returns a flat list of suggestion dicts
  (``'term'``, ``'weight'``, ``'payload'``). Supports ``dictionary`` and ``count``
  arguments plus arbitrary extra parameters.
- **SpellcheckResult** (Solr 1.4+): New ``SpellcheckResult`` class exposed as the
  ``Response.spellcheck`` property. Provides ``.correctly_spelled``, ``.collation``,
  and ``.suggestions`` accessors over the raw spellcheck response data.
  Works in both JSON and XML response modes.


1.4.2 (2026-03-27)
-------------------

**Improvements:**

- New ``MoreLikeThis(conn)`` wrapper class in ``solr/mlt.py``.
  Users no longer need to know the ``/mlt`` handler path.
- Replaces previous ``SearchHandler(conn, '/mlt')`` pattern.


1.4.1 (2026-03-27)
-------------------

**Breaking changes:**

- ``conn.schema`` auto-created attribute removed. Create explicitly:
  ``schema = SchemaAPI(conn)``.
- ``conn.mlt`` auto-created attribute removed. Create explicitly:
  ``mlt = SearchHandler(conn, '/mlt')``.
- ``Solr.__init__`` no longer initializes optional features. Only ``select``
  remains as a built-in handler.


1.4.0 (2026-03-27)
-------------------

**New features (Solr 4.2+):**

- **Schema API** via ``conn.schema``:
  - ``get_schema()`` — full schema dump
  - ``fields()`` / ``add_field()`` / ``replace_field()`` / ``delete_field()``
  - ``dynamic_fields()`` / ``add_dynamic_field()`` / ``delete_dynamic_field()``
  - ``field_types()`` / ``add_field_type()`` / ``replace_field_type()`` / ``delete_field_type()``
  - ``copy_fields()`` / ``add_copy_field()`` / ``delete_copy_field()``
  - Version-gated to Solr 4.2+
- New ``solr/schema.py`` module (separated per CLAUDE.md guidelines)


1.3.0 (2026-03-27)
-------------------

**New features (Solr 5.0+):**

- **JSON Facet API**: ``json_facet`` parameter on ``SearchHandler.__call__``.
  Accepts a dict, automatically serialized to ``json.facet`` query parameter.
  Response includes ``facets`` attribute with results.
  Version-gated to Solr 5.0+. Works in both JSON and XML response modes.


1.2.0 (2026-03-27)
-------------------

**New features (Solr 4.7+):**

- **Cursor pagination**: ``Response.cursor_next()`` for cursor-based deep
  pagination. Returns ``None`` when all results are consumed.
- **Cursor iterator**: ``Solr.iter_cursor(q, sort, rows)`` generator that
  yields Response batches, automatically following cursor marks.


1.1.0 (2026-03-27)
-------------------

**New features (Solr 4.0+):**

- **Soft Commit**: ``conn.commit(soft_commit=True)`` makes changes visible
  without flushing to disk. Version-gated to Solr 4.0+.
- **Atomic Update**: ``conn.atomic_update(doc)`` and ``atomic_update_many(docs)``
  for partial document updates. Supports ``set``, ``add``, ``remove``,
  ``removeregex`` (Solr 5.0+), and ``inc`` modifiers. ``{'set': None}``
  removes a field.
- **Real-time Get**: ``conn.get(id=...)`` retrieves documents directly from the
  transaction log via ``/get`` handler without waiting for a commit.
- **MoreLikeThis**: ``conn.mlt`` SearchHandler bound to ``/mlt`` endpoint
  for finding similar documents.


1.0.9 (2026-03-27)
-------------------

**New features:**

- Per-request timeout override via ``timeout`` keyword argument.
  Applies to ``select()``, ``select.raw()``, ``add()``, ``add_many()``,
  ``delete()``, ``delete_many()``, ``delete_query()``, and ``commit()``.
  The connection-level timeout is restored after each request.


1.0.8 (2026-03-27)
-------------------

**New features:**

- Exponential backoff on connection retries. Base delay configurable via
  ``retry_delay`` constructor parameter (default ``0.1`` seconds).
  First retry waits ``retry_delay``, second waits ``retry_delay * 2``, etc.
- Each retry attempt is logged at WARNING level to the ``solr`` logger.


1.0.7 (2026-03-27)
-------------------

**Breaking changes:**

- ``EmptyPage`` no longer inherits from ``SolrException``; now subclasses
  ``ValueError``.
- New ``PageNotAnInteger`` exception (subclass of ``TypeError``) replaces
  the previous ``SolrException('PageNotAnInteger')`` pattern.
- Paginator module no longer depends on ``SolrException`` for flow control.


1.0.6 (2026-03-27)
-------------------

**New features:**

- ``Solr`` constructor now validates the URL path. A ``UserWarning`` is issued
  if the path does not contain ``/solr``, preparing for Solr 10.0+ which
  requires the URL to end with ``/solr``.


1.0.5 (2026-03-27)
-------------------

**Breaking changes:**

- Removed ``SolrConnection`` class. Use ``Solr`` instead.
- Migration: ``SolrConnection.add(**fields)`` → ``Solr.add(fields)``,
  ``SolrConnection.query()`` → ``Solr.select()``,
  ``SolrConnection.raw_query()`` → ``Solr.select.raw()``.


1.0.4 (2026-03-27)
-------------------

**Breaking changes:**

- Default ``response_format`` changed from ``'xml'`` to ``'json'``.
  Existing code that relies on XML-specific behavior should pass
  ``response_format='xml'`` explicitly.


1.0.3 (2026-03-27)
-------------------

**New features:**

- ``response_format`` constructor option: ``Solr(url, response_format='json')``
  switches the query pipeline to use ``wt=json`` and the JSON parser.
  Default is ``'xml'`` for backward compatibility.
- ``SearchHandler`` automatically selects ``wt`` and parser based on the
  connection's ``response_format`` setting.

**Refactoring:**

- Split ``solr/core.py`` (1287 lines) into five focused modules:
  ``exceptions.py``, ``utils.py``, ``response.py``, ``parsers.py``, ``core.py``.
- All existing import paths continue to work via re-exports in ``__init__.py``.


1.0.2 (2026-03-27)
-------------------

**Type safety:**

- ``mypy --strict`` now passes with zero errors on the entire ``solr/`` package.
- Added type annotations to all internal classes: ``ResponseContentHandler``,
  ``Node``, ``Results``, ``UTC``.
- Added type annotations to all ``@committing``-decorated methods (``add``,
  ``add_many``, ``delete``, ``delete_many``, ``delete_query``).
- Fixed ``endElement`` variable shadowing (``name`` → ``tag``) for type safety.
- Removed unnecessary ``type: ignore`` comments.


1.0.1 (2026-03-27)
-------------------

**New features:**

- Added type annotations to all public methods across ``solr/core.py``
  and ``solr/paginator.py``.
- Added ``solr/py.typed`` marker file for PEP 561 type checker discovery.
- Added ``mypy`` to dev dependencies; ``mypy solr/`` passes with zero errors.

**Internal:**

- Replaced mutable default ``post_headers={}`` with ``None`` to avoid
  shared mutable state.
- Fixed ``paginator.py`` ``try/except`` import with direct relative import.


0.9.11 (2026-03-26)
--------------------

**New features:**

- ``parse_json_response()`` function for parsing JSON responses from Solr.
  Supports all standard response fields: results, header, highlighting,
  facet_counts, maxScore, and arbitrary top-level keys.
- ``Solr.ping()`` convenience method. Returns ``True`` if the Solr server
  is reachable, ``False`` otherwise.
- ``always_commit`` constructor option. When ``True``, all add/delete
  operations automatically commit. Individual calls can override with
  ``commit=False``.
- Gzip response support. ``Accept-Encoding: gzip`` header is now sent on
  all requests. Compressed responses are decompressed transparently via
  the new ``read_response()`` helper.


0.9.10 (2026-03-26)
--------------------

**Documentation:**

- Added Sphinx-based documentation: quick start guide, full API reference,
  version detection guide, and changelog.
- Rewrote ``README.md`` with current API examples, Docker-based test
  instructions, and changelog section.
- Updated ``CLAUDE.md`` development guidelines.

**Packaging:**

- Added ``pyproject.toml`` metadata: authors, maintainers, classifiers,
  keywords, homepage, repository URL.
- Added Sphinx and sphinx-rtd-theme as docs dependencies.
- Added pytest and mypy configuration sections.
- Excluded ``tests/`` and ``docs/`` from distribution packages.


0.9.9 (2026-03-26)
-------------------

**Breaking changes:**

- Python 3.10+ is now required. All Python 2 compatibility code has been removed.
- The deprecated ``encoder`` and ``decoder`` attributes on ``Solr`` instances
  have been removed.
- Migrated from setuptools (``setup.py``) to Poetry (``pyproject.toml``).

**New features:**

- Automatic Solr version detection via ``server_version`` attribute.
- ``SolrVersionError`` exception raised when a feature requires a higher Solr
  version than connected.
- ``requires_version`` decorator for runtime version gating.

**Bug fixes:**

- ``commit(_optimize=True)`` now correctly issues an ``<optimize/>`` command.
  Previously it always issued ``<commit/>`` regardless of the flag.

**Tests:**

- Added dedicated tests for ``<double>`` XML type parsing.
- Added tests for named ``<result>`` tag handling in XML responses.
- Added tests for version detection, ``SolrVersionError``, and
  ``requires_version`` decorator.
- Fixed all tests for Python 3.12 compatibility: ``assertEquals`` replaced
  with ``assertEqual``, ``assert_`` replaced with ``assertTrue``.
- Fixed legacy pickle tests to use bytes literals.

**Internal:**

- Removed ``codecs`` and ``sys`` imports (no longer needed).
- Removed ``_python_version`` and all associated conditional branches.
- Replaced ``unicode`` with ``str``, ``basestring`` with ``str``,
  ``long`` with ``int`` throughout the codebase.
- Simplified ``isinstance(data, bytes)`` checks to direct ``.decode('utf-8')``.


0.9.8
-----

- Bump version to 0.9.8.
- Fix Python 2/3 compatibility issues and multiple bugs.


0.9.7
-----

- Fixed basic authentication to work properly in Python 3.


Prior versions
--------------

See the `GitHub commit history
<https://github.com/search5/solrpy/commits/master>`_ for details on
earlier releases.
