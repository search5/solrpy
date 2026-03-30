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

## Why solrpy over pysolr?

| Feature | solrpy | pysolr |
|---|:---:|:---:|
| Basic CRUD | ✅ | ✅ |
| Async/await | ✅ | — |
| Streaming Expressions | ✅ | — |
| KNN / Vector search | ✅ | — |
| Schema API (full CRUD) | ✅ | — |
| Pydantic models | ✅ | — |
| SolrCloud + ZooKeeper | ✅ | ✅ |
| JSON Facet API | ✅ | — |
| Structured Field/Sort/Facet builders | ✅ | — |
| Document extraction (Tika) | ✅ | ✅ |
| Solr version auto-detection | ✅ | — |
| Solr 1.2–10.x spanning | ✅ | — |
| Type hints + py.typed | ✅ | — |
| Connection pooling (httpx) | ✅ | ✅ |
| Performance | on par | on par |

### Migrating from pysolr

```python
# Option 1: Drop-in compatibility wrapper
from solr import PysolrCompat as Solr

conn = Solr('http://localhost:8983/solr/mycore')
results = conn.search('title:hello')       # pysolr API
conn.add([doc1, doc2], commit=True)        # accepts list like pysolr
conn.delete(id='1', q='old:*')             # q= maps to delete_query

# Option 2: Native solrpy API (recommended)
from solr import Solr

conn = Solr('http://localhost:8983/solr/mycore')
results = conn.select('title:hello')       # select instead of search
conn.add_many([doc1, doc2], commit=True)   # explicit add_many
conn.delete_query('old:*', commit=True)    # explicit delete_query
```

## Tests

Tests require a running Solr instance. Using Docker:

```bash
docker run -d --name solr-dev -p 8983:8983 solr:6.6 solr-precreate core0
poetry run pytest tests/
```

## Changelog

### 2.0.8a

- **18 bug fixes**: async event-loop blocking (`time.sleep` → `asyncio.sleep`), date validation logic inverted, highlight `hl_fl` list bug, async timeout leak, PysolrCompat double commit, SolrCloud resource leak, stream pipe mutation, sort false positive, paginator `q` loss, and more
- Full details in [changelog](https://search5.github.io/solrpy/latest/changelog.html)

### 2.0.8

- **Decimal support**: `decimal.Decimal` values now serialize correctly in both JSON and XML update paths
- **Security**: all `eval()` usage removed (resolved since 2.x rewrite)
- **No stray `print()`**: debug print statements fully eliminated from all execution paths
- **UTF-8 safe**: `setup.py` replaced with Poetry `pyproject.toml`, no encoding issues
- **`q.op` support**: dotted Solr parameters work via underscore notation (`q_op='AND'` → `q.op=AND`)

### 2.0.7

- **Lazy initialization**: `Solr()` constructor is now instant (~0ms). httpx client and version detection deferred to first use
- **PysolrCompat**: drop-in compatibility wrapper for pysolr migration (`from solr import PysolrCompat`)
- **Select performance**: `json.loads(bytes)` instead of `json.loads(string)` eliminates redundant decode
- Comparison table and migration guide in README

### 2.0.6

- **Async Pydantic models**: `await conn.select('*:*', model=MyDoc)` returns typed results
- `model=` parameter on `AsyncSolr.select()` — same as sync `SearchHandler`

### 2.0.5

- **Async Streaming Expressions**: `async for doc in await conn.stream(expr):`
- **serialize_value() bug fix**: `atomic_update()`, `AsyncSolr.add/add_many` now correctly serialize `datetime`, `date`, `bool`
- **Internal JSON update path**: Solr 4.0+ uses JSON for add/add_many/atomic_update (no user-facing change)
- `solr_json_default()` encoder handles `datetime`, `date`, `set`, `tuple`

### 2.0.4

- **Unified sync/async API**: `SchemaAPI(conn)` works with both `Solr` and `AsyncSolr`
- Single class, dual mode — no need for separate `AsyncSchemaAPI` etc.
- `DualTransport` auto-detects sync vs async connection
- `_chain()` helper for composing sync values and async coroutines
- `AsyncSchemaAPI`, `AsyncKNN`, `AsyncMoreLikeThis`, `AsyncSuggest`, `AsyncExtract` kept as backward-compatible aliases

### 2.0.3

- **Async companion classes**: `AsyncSchemaAPI`, `AsyncKNN`, `AsyncMoreLikeThis`, `AsyncSuggest`, `AsyncExtract`
- Full async support for all companion features

### 2.0.2

- **AsyncSolr**: `async with AsyncSolr(url) as conn: await conn.select('*:*')`
- **AsyncTransport** for async companion classes
- Full async: select, add, add_many, delete, commit, get

### 2.0.1

- **Breaking**: `http.client` replaced with `httpx.Client`
- Automatic **connection pooling** and keep-alive
- `httpx` is now a required dependency
- All public API unchanged — drop-in replacement for 1.x

### 1.12.0

- **Streaming Expressions**: Python builder with pipe (`|`) operator — no other non-Java client has this
- `search`, `merge`, `rollup`, `top`, `unique`, `innerJoin`, etc.
- Aggregate: `count`, `sum`, `avg`, `min`, `max`
- `conn.stream(expr)` → iterator of result dicts
- Pydantic model support via `model=` parameter

### 1.11.0

- **Pydantic response models**: `conn.select('*:*', model=MyDoc)` converts results to Pydantic models
- `Response.as_models(MyDoc)` for post-hoc conversion
- `conn.get(id='1', model=MyDoc)` returns `MyDoc | None`
- `pip install solrpy[pydantic]`

### 1.10.1

- **Field builder**: `Field('price', alias='p')`, `Field.func('sum', 'price', 'tax')`, `Field.transformer('explain')`
- **Sort builder**: `Sort('price', 'desc')`, `Sort.func('geodist()', 'asc')`
- **Facet builder**: `Facet.field('category')`, `Facet.range('price', 0, 100, 10)`, `Facet.query()`, `Facet.pivot()`
- Fully backward compatible — raw strings still work

### 1.10.0

- **SolrCloud**: `SolrCloud(zk, collection)` with ZooKeeper or `SolrCloud.from_urls(urls, collection)` HTTP-only
- Leader-aware writes, automatic failover, collection aliases
- `SolrZooKeeper` class for ZooKeeper node discovery
- `kazoo` optional dependency (`pip install solrpy[cloud]`)
- Docker Compose for local SolrCloud testing

### 1.9.2

- **Solr 6~10 full compatibility**: `wt=xml` on Solr 7+ (`wt=standard` changed in 7.0)
- Tested against Solr 6.6, 7.7, 8.11, 9.7, 10.0 — all 0 failures
- GitHub Actions CI matrix for 5 Solr versions
- KNN live tests version-gated (skip on < 9.0, efSearchScaleFactor skip on < 10.0)
- Test isolation: Paginator no longer deletes all documents

### 1.9.1

- **KNN API overhaul**: `search()`, `similarity()`, `hybrid()`, `rerank()` methods
- Full `{!knn}` parameters: `early_termination`, `seed_query`, `pre_filter`, etc.
- `{!vectorSimilarity}` threshold search (Solr 9.6+)
- Hybrid (lexical OR vector) and re-ranking patterns

### 1.9.0

- **KNN / Dense Vector Search**: `KNN(conn)` for `{!knn}` queries (Solr 9.0+)

### 1.8.1

- **HTTP transport abstraction**: `SolrTransport` decouples companion classes from internal `_get`/`_post`
- SchemaAPI, Suggest, Extract now use `SolrTransport` — prepares for httpx in 2.0.0

### 1.8.0

- **Bearer token auth**: `Solr(url, auth_token='...')`
- **Custom auth callable**: `Solr(url, auth=my_fn)` for OAuth2 dynamic refresh
- Priority: `auth` callable > `auth_token` > `http_user/http_pass`

### 1.7.0

- **Grouping / Field Collapsing**: `resp.grouped['field'].groups` for grouped results (Solr 3.3+)
- `GroupedResult`, `GroupField`, `Group` classes with `groupValue`, `doclist`, `matches`, `ngroups`
- Works in both JSON and XML modes

### 1.6.0

- **Extract**: `Extract(conn)` wrapper class for Solr Cell (Apache Tika) via `/update/extract` (Solr 1.4+).
  Index rich documents (PDF, Word, HTML, …) with optional literal field values.
  `extract_only()` extracts text and metadata without indexing.
  `from_path()` / `extract_from_path()` open files by filesystem path, MIME type guessed automatically.

```python
from solr import Solr, Extract

conn = Solr('http://localhost:8983/solr/mycore')
extract = Extract(conn)

# Index a PDF with metadata
with open('report.pdf', 'rb') as f:
    extract(f, content_type='application/pdf',
            literal_id='report1', literal_title='Annual Report',
            commit=True)

# Extract text only (no indexing)
text, metadata = extract.extract_from_path('report.pdf')
print(text[:200])

# Index from path (MIME type auto-detected)
extract.from_path('document.docx', literal_id='doc1', commit=True)
```

### 1.5.0

- **Suggest**: `Suggest(conn)` wrapper class for Solr's SuggestComponent (Solr 4.7+).
  Returns a flat list of suggestion dicts from the `/suggest` handler.
- **Spellcheck**: `Response.spellcheck` property returns a `SpellcheckResult` object
  with `.collation` and `.suggestions` accessors. Works in both JSON and XML modes (Solr 1.4+).

```python
from solr import Solr, Suggest

conn = Solr('http://localhost:8983/solr/mycore')

# Suggest
suggest = Suggest(conn)
results = suggest('que', dictionary='mySuggester', count=5)
for s in results:
    print(s['term'], s['weight'])

# Spellcheck
resp = conn.select('misspeled query', spellcheck='true', spellcheck_collate='true')
if resp.spellcheck and not resp.spellcheck.correctly_spelled:
    print('Did you mean:', resp.spellcheck.collation)
```

### 1.4.2

- New `MoreLikeThis(conn)` wrapper class — no need to know `/mlt` path

### 1.4.1

- **Breaking**: `conn.schema` and `conn.mlt` removed from auto-initialization
- Use `SchemaAPI(conn)` and `SearchHandler(conn, '/mlt')` explicitly
- Keeps `Solr` class lightweight; optional features created on demand

### 1.4.0

- **Schema API**: `conn.schema.fields()`, `add_field()`, `replace_field()`, `delete_field()`, copy fields, dynamic fields, field types (Solr 4.2+)

### 1.3.0

- **JSON Facet API**: `json_facet` parameter for advanced faceting (Solr 5.0+)

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
