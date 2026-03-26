Version Detection
=================

solrpy automatically detects the Solr version at connection time and uses it
to gate features at runtime.


How it works
------------

When a ``Solr`` instance is created, ``_detect_version()`` is called during
initialization:

1. **JSON API** (Solr 4.0+): ``GET /admin/info/system?wt=json``
2. **XML fallback** (Solr 3.x): ``GET /admin/info/system?wt=xml``
3. **Default**: ``(1, 2, 0)`` with a warning log if both attempts fail

Both the core path and its parent path are tried, so URLs like
``http://host:8983/solr/core0`` will also check ``/solr/admin/info/system``.


Accessing the version
---------------------

The detected version is stored as a tuple::

    import solr

    conn = solr.Solr('http://localhost:8983/solr/mycore')
    print(conn.server_version)  # e.g. (6, 6, 6)

    major, minor, patch = conn.server_version
    if major >= 9:
        print('KNN search is available')


SolrVersionError
----------------

When a feature requires a Solr version higher than what is connected,
a ``SolrVersionError`` is raised::

    import solr

    conn = solr.Solr('http://localhost:8983/solr/mycore')
    # if connected to Solr 3.x:
    # solr.core.SolrVersionError: atomic_update requires Solr 4.0+,
    #                              but connected to Solr 3.6.2

The exception has these attributes:

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Attribute
     - Description
   * - ``feature``
     - Name of the feature that was called
   * - ``required``
     - Minimum version tuple required, e.g. ``(4, 0)``
   * - ``actual``
     - Detected server version tuple, e.g. ``(3, 6, 2)``


requires_version decorator
--------------------------

The ``requires_version`` decorator is used internally to guard methods::

    from solr.core import requires_version

    class Solr:

        @requires_version(4, 0)
        def atomic_update(self, doc):
            ...

If ``self.server_version`` is lower than the specified minimum, the decorator
raises ``SolrVersionError`` before the method body executes.


Supported Solr versions
-----------------------

solrpy targets all Solr versions from 1.2 through 10.x. The version detection
mechanism ensures that features are only used when the connected Solr instance
supports them.

.. list-table::
   :widths: 30 20
   :header-rows: 1

   * - Feature
     - Minimum Solr
   * - Basic query and indexing
     - 1.2
   * - Atomic Update (``atomic_update``)
     - 4.0
   * - Soft Commit (``commit(soft_commit=True)``)
     - 4.0
   * - Real-time Get (``get()``)
     - 4.0
   * - MoreLikeThis (``mlt``)
     - 4.0
   * - Cursor Pagination (``cursor_next()``, ``iter_cursor()``)
     - 4.7
   * - JSON Facet API
     - 5.0
   * - Dense Vector Search (KNN)
     - 9.0
