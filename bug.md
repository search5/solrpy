# Bug Tracker

## Status Legend
- [ ] Open
- [x] Fixed

## Bugs

### 1. [Critical] `async_solr.py:220` — `time.sleep()` in async (blocks event loop)
- [x] The `_post` retry loop uses synchronous `time.sleep(delay)` inside an async function, blocking the entire event loop.
- **Fix**: Replace with `await asyncio.sleep(delay)`.

### 2. [High] `utils.py:108` — `utc_from_string` inverted validation + IndexError
- [x] Condition `if not value.endswith('Z') and value[10] == 'T'` is inverted. Also, `value[10]` raises IndexError for short strings.
- **Fix**: Change to `if len(value) < 20 or not value.endswith('Z') or value[10] != 'T'`.

### 3. [High] `core.py:699` — `hl_fl` assigned as list instead of string
- [x] `params['hl_fl'] = [fields]` wraps a string in a list. Solr expects a string.
- **Fix**: Change to `params['hl_fl'] = fields`.

### 4. [Medium] `cloud.py:105-112` — Resource leak when ping raises
- [x] If `probe.ping()` raises an exception, `probe.close()` is never called.
- **Fix**: Use `try/finally` to ensure `probe.close()` is always called.

### 5. [Medium] `response.py:326,369` — TypeError when start is None
- [x] `int(self.results.start)` raises TypeError (not AttributeError) when start is None.
- **Fix**: Catch `(AttributeError, TypeError)`.

### 6. [Medium] `stream.py:60` — Pipe operator mutates `other` in place
- [x] `other._args.insert(0, self)` permanently modifies `other`, causing bugs on reuse.
- **Fix**: Create a copy of `other` before inserting.

### 7. [Low] `core.py:114-115` — Malformed SSL cert tuple when only ssl_key provided
- [x] `(ssl_cert, ssl_key)` becomes `(None, ssl_key)` when only ssl_key is given.
- **Fix**: Validate that ssl_cert is provided when ssl_key is given.

### 8. [Low] `facet.py:78` — `query()` method's `name` parameter is unused
- [x] The `name` parameter is accepted but never included in the output dict.
- **Fix**: Accept both legacy `(name, q)` and new `(q)` call forms.

### 9. [High] `async_solr.py:262-266` — timeout leaked into Solr query params
- [x] `timeout` is included in the urlencode'd query string before being popped, sending an unwanted `timeout` parameter to Solr.
- **Fix**: Pop timeout from params before urlencode.

### 10. [High] `compat.py:60-66` — Double commit in add()/delete()
- [x] `super().add(docs)` goes through `@committing` decorator which already commits. Then `PysolrCompat.add()` calls `self.commit()` again.
- **Fix**: Pass `commit=commit` to super calls, remove separate commit call.

### 11. [Medium] `suggest.py:88-89` — Duplicate `wt=json` in URL
- [x] `query_params` already contains `'wt': 'json'`, and `DualTransport.get_json()` appends `wt=json` again.
- **Fix**: Remove `'wt': 'json'` from `query_params`.

### 12. [Medium] `core.py:184-189` — Unnecessary client creation on close()
- [x] `close()` creates a new `httpx.Client` just to close it if never used.
- **Fix**: Won't fix — kept for `is_closed` consistency required by existing tests and API contract.

### 13. [Medium] `core.py:724` — `endswith("asc")` false positive on field names
- [x] Field names like `"classic"` match `endswith("asc")`, skipping sort direction.
- **Fix**: Check `endswith(" asc")` or `endswith(" desc")` with space prefix.

### 14. [Medium] `core.py:10` — Duplicate import of urllib.parse
- [x] `import urllib.parse as urlparse` and `import urllib.parse as urllib` import the same module twice.
- **Fix**: Remove the duplicate and unify to one alias.

### 15. [Medium] `paginator.py:88` — `_fetch_page` may lose `q` parameter
- [x] `self.query(**new_params)` passes `q` inside `**new_params` as a keyword, but `SearchHandler.__call__` has `q` as a positional arg. If `q` is missing from params, query is None.
- **Fix**: Pop `q` from new_params and pass it as first positional arg.

### 16. [Medium] `response.py:376` — Wrong path for `rows` in header
- [x] `self.header.get('rows', ...)` looks at top-level header, but `rows` is nested under `header['params']`.
- **Fix**: Use `self.header.get('params', self.header).get('rows', ...)`.

### 17. [Low] `core.py:563` — Loop variable `id` shadows parameter
- [x] `for id in ids:` shadows both the function parameter and the builtin `id()`.
- **Fix**: Rename loop variable to `doc_id`.

### 18. [Low] `knn.py:163` — `v=` syntax inconsistency in hybrid query
- [x] `build_hybrid_query` uses `v="[...]"` inside local params, while `build_similarity_query` puts the vector in the query body. Inconsistent API and may fail on some Solr versions.
- **Fix**: Use the body-style format consistent with `build_similarity_query`.
