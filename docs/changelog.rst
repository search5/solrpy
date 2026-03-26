Changelog
=========

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
