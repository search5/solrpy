from __future__ import annotations

import math
from typing import Any

from .exceptions import SolrException
from .response import Response, Results


class EmptyPage(SolrException):
    pass


class SolrPaginator:
    """
    Create a Django-like Paginator for a solr response object. Can be handy
    when you want to hand off a Paginator and/or Page to a template to
    display results, and provide links to next page, etc.

    For example:
    >>> from solr import SolrConnection, SolrPaginator
    >>>
    >>> conn = SolrConnection('http://localhost:8083/solr')
    >>> response = conn.query('title:huckleberry')
    >>> paginator = SolrPaginator(response)
    >>> print(paginator.num_pages)
    >>> page = paginator.get_page(5)

    For more details see the Django Paginator documentation and solrpy
    unittests.

      http://docs.djangoproject.com/en/dev/topics/pagination/

    """

    def __init__(self, result: Response, default_page_size: int | str | None = None) -> None:
        self.params: dict[str, Any] = result._params
        self.result = result
        self.query: Any = result._query

        if 'rows' in self.params:
            self.page_size = int(self.params['rows'])
        elif default_page_size:
            try:
                self.page_size = int(default_page_size)
            except ValueError:
                raise ValueError('default_page_size must be an integer')

            if self.page_size < len(self.result.results):
                raise ValueError('Invalid default_page_size specified, lower '
                                 'than number of results')

        else:
            self.page_size = len(self.result.results) or 10

    @property
    def count(self) -> int:
        return int(self.result.numFound)

    @property
    def num_pages(self) -> int:
        if self.count == 0:
            return 0
        return int(math.ceil(float(self.count) / float(self.page_size)))

    @property
    def page_range(self) -> range:
        """List the index numbers of the available result pages."""
        if self.count == 0:
            return range(0)
        return range(1, self.num_pages + 1)

    def _fetch_page(self, start: int = 0) -> Any:
        """Retrieve a new result response from Solr."""
        new_params: dict[str, Any] = {}
        for k, v in self.params.items():
            new_params[str(k)] = v
        new_params['start'] = start
        return self.query(**new_params)

    def page(self, page_num: int = 1) -> SolrPage:
        """Return the requested Page object"""
        try:
            int(page_num)
        except (TypeError, ValueError):
            raise SolrException('PageNotAnInteger')

        if page_num not in self.page_range:
            raise EmptyPage('That page does not exist.')

        start = (page_num - 1) * self.page_size
        new_result = self._fetch_page(start=start)
        return SolrPage(new_result.results, page_num, self)


class SolrPage:
    """A single Paginator-style page."""

    def __init__(self, result: Results | list[dict[str, Any]], page_num: int, paginator: SolrPaginator) -> None:
        self.result = result
        self.number = page_num
        self.paginator = paginator

    @property
    def object_list(self) -> Results | list[dict[str, Any]]:
        return self.result

    def has_next(self) -> bool:
        return self.number < self.paginator.num_pages

    def has_previous(self) -> bool:
        return self.number > 1

    def has_other_pages(self) -> bool:
        return self.paginator.num_pages > 1

    def start_index(self) -> int:
        return (self.number - 1) * self.paginator.page_size

    def end_index(self) -> int:
        return self.start_index() + len(self.result) - 1

    def next_page_number(self) -> int:
        return self.number + 1

    def previous_page_number(self) -> int:
        return self.number - 1
