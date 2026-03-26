# solrpy

solrpy is a Python client for [Solr], an enterprise search server
built on top of [Lucene]. solrpy allows you to add documents to a
Solr instance, and then to perform queries and gather search results
from Solr using Python.

- **Supports Solr 1.2 through 10.x**
- **Automatic Solr version detection** with runtime feature gating
- **Python 3.10+** required

## Installation

```bash
pip install solrpy
```

Or with Poetry:

```bash
poetry add solrpy
```

## Overview

```python
import solr

# create a connection to a solr server
s = solr.Solr('http://localhost:8983/solr/mycore')

# the server version is auto-detected
print(s.server_version)  # e.g. (9, 4, 1)

# check if the server is reachable
print(s.ping())  # True

# add a document to the index
doc = {
    "id": 1,
    "title": "Lucene in Action",
    "author": ["Erik Hatcher", "Otis Gospodnetić"],
}
s.add(doc, commit=True)

# do a search
response = s.select('title:lucene')
for hit in response.results:
    print(hit['title'])
```

## Response format

Since v1.0.4, solrpy uses JSON (`wt=json`) by default, matching Solr 7.0+ behavior.

For legacy XML mode:

```python
s = solr.Solr('http://localhost:8983/solr/mycore', response_format='xml')
```

The `Response` object API is identical regardless of format.

## More powerful queries

Optional parameters for query, faceting, highlighting, and more like this
can be passed in as Python parameters to the query method. Convert the
dot notation (e.g. `facet.field`) to underscore notation (e.g. `facet_field`)
so that they can be used as parameter names.

```python
response = s.select('title:lucene', facet='true', facet_field='subject')
```

If the parameter takes multiple values, pass them in as a list:

```python
response = s.select('title:lucene', facet='true', facet_field=['subject', 'publisher'])
```

## Version detection

solrpy automatically detects the connected Solr version and gates features
accordingly. If a feature requires a newer Solr version than what is
connected, a `SolrVersionError` is raised with a clear message.

```python
import solr

s = solr.Solr('http://localhost:8983/solr/mycore')
print(s.server_version)  # (6, 6, 6)
```

## Tests

Tests require a running Solr instance. Using Docker:

```bash
docker run -d --name solr-dev -p 8983:8983 solr:6.6 solr-precreate core0
poetry run pytest tests/
```

## Changelog

### 1.2.0

- **Cursor pagination**: `resp.cursor_next()` and `conn.iter_cursor()` for deep pagination (Solr 4.7+)

### 1.1.0

- **Soft Commit**: `conn.commit(soft_commit=True)` (Solr 4.0+)
- **Atomic Update**: `conn.atomic_update(doc)` with `set`/`add`/`remove`/`inc` modifiers (Solr 4.0+)
- **Real-time Get**: `conn.get(id='doc1')` via `/get` handler (Solr 4.0+)
- **MoreLikeThis**: `conn.mlt` handler for similar document search (Solr 4.0+)

### 1.0.9

- Per-request timeout override: `conn.select('*:*', timeout=5)`

### 1.0.8

- Exponential backoff on connection retries with configurable `retry_delay`
- Each retry logged at WARNING level

### 1.0.7

- **Breaking**: `EmptyPage` now inherits `ValueError` (was `SolrException`)
- New `PageNotAnInteger` exception (inherits `TypeError`)
- Paginator module no longer depends on `SolrException`

### 1.0.6

- URL validation: warns if URL path doesn't contain `/solr` (Solr 10.0+ preparation)

### 1.0.5

- **Breaking**: Removed `SolrConnection` class. Use `Solr` instead
- Migration: `add(**fields)` → `add(dict)`, `query()` → `select()`, `raw_query()` → `select.raw()`

### 1.0.4

- **Breaking**: Default `response_format` changed from `'xml'` to `'json'`
- Pass `response_format='xml'` explicitly for legacy XML behavior

### 1.0.3

- Added `response_format` constructor option (`'xml'` or `'json'`)
- Split `solr/core.py` into `exceptions.py`, `utils.py`, `response.py`, `parsers.py`
- All existing imports continue to work (re-exported via `__init__.py`)

### 1.0.2

- `mypy --strict` passes with zero errors on `solr/` package
- Added type hints to all internal classes (`ResponseContentHandler`, `Node`, `Results`, `UTC`)
- Fixed `endElement` variable shadowing for type safety

### 1.0.1

- Added type hints to all public methods in `solr/core.py` and `solr/paginator.py`
- Added `solr/py.typed` marker file for PEP 561 compatibility
- Added `mypy` to dev dependencies
- mypy passes with zero errors on `solr/` package

### 0.9.11

- Added JSON response parser (`parse_json_response`)
- Added `Solr.ping()` convenience method
- Added `always_commit` constructor option for auto-commit behavior
- Added gzip response support (`Accept-Encoding: gzip`)

### 0.9.10

- Added pyproject.toml metadata (authors, maintainers, classifiers, keywords)
- Added Sphinx documentation (quickstart, API reference, version detection, changelog)
- Rewrote README.md with current API examples and Docker test instructions
- Updated CLAUDE.md development guidelines

### 0.9.9

- Removed deprecated `encoder`/`decoder` attributes and `codecs` import
- Fixed `commit(_optimize=True)` to correctly issue `<optimize/>` command
- Added test coverage for `<double>` XML type parsing
- Added test coverage for named `<result>` tag handling
- Added Solr version auto-detection (`server_version`)
- Added `SolrVersionError` exception and `requires_version` decorator
- Removed all Python 2 compatibility code (Python 3.10+ only)
- Migrated from setuptools to Poetry
- Bumped version to 0.9.9

## License

[Apache License 2.0](http://www.apache.org/licenses/LICENSE-2.0)

[Solr]: https://solr.apache.org/
[Lucene]: https://lucene.apache.org/
