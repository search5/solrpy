Overview
--------

Here's the basic gist::

    import solr

    # create a connection to a solr server
    s = solr.Solr('http://example.org:8083/solr')

    # add a document to the index
    doc = dict(
        id=1,
        title='Lucene in Action',
        author=['Erik Hatcher', 'Otis Gospodnetić'],
        )
    s.add(doc, commit=True)

    # do a search
    response = s.select('title:lucene')
    for hit in response.results:
        print hit['title']

Optional parameters for query, faceting, highlighting and more like this
can be passed as parameters to the select method.  Convert dots in
parameter names to underscores.  For example, the ``facet.field``
parameter would be specified as ``facet_field``.

For example, if you want to get faceting information in your search
result::

    response = s.select(
        'title:lucene', facet='true', facet_field='subject')

and if the parameter takes multiple values you just pass them in as a list::

    response = s.select(
        'title:lucene', facet='true',
        facet_field=['subject', 'publisher'])


Community
~~~~~~~~~

Feel free to join our `discussion list`_ if you have ideas or suggestions.
Also, please add examples to the wiki_ if you have the time and interest.


.. _discussion list:  http://groups.google.com/group/solrpy
.. _wiki:  http://code.google.com/p/solrpy/w/list
