Changelog
=========

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
