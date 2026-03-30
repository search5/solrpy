from __future__ import annotations

import math
from typing import Any

from .response import Response, Results


class EmptyPage(ValueError):
    """Raised when the requested page number is out of range."""
    pass


class PageNotAnInteger(TypeError):
    """Raised when the page number is not an integer."""
    pass


class SolrPaginator:
    """
    Paginator for a Solr response object.

    Example::

        >>> from solr import Solr, SolrPaginator
        >>>
        >>> conn = Solr('http://localhost:8083/solr')
        >>> response = conn.select('title:huckleberry')
        >>> paginator = SolrPaginator(response)
        >>> print(paginator.num_pages)
        >>> page = paginator.page(1)
    """

    def __init__(self, result: Response, default_page_size: int | str | None = None) -> None:
        """Initialize a paginator from a Solr response.

        :param result: A :class:`~solr.response.Response` object returned by a
            Solr query.
        :param default_page_size: Number of results per page. If ``None``, the
            page size is inferred from the ``rows`` query parameter or the
            number of results in *result*. Must be an integer (or integer
            string) no smaller than the current result count.
        """
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
        """Total number of matching documents."""
        return int(self.result.numFound)

    @property
    def num_pages(self) -> int:
        """Total number of pages."""
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
        q = new_params.pop('q', '')
        return self.query(q, **new_params)

    def page(self, page_num: int = 1) -> SolrPage:
        """Return the requested Page object.

        :param page_num: 1-based page number.
        :raises PageNotAnInteger: If *page_num* cannot be converted to an int.
        :raises EmptyPage: If *page_num* is outside the valid page range.
        """
        try:
            page_num = int(page_num)
        except (TypeError, ValueError):
            raise PageNotAnInteger('Page number must be an integer')

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
        """List of documents on this page."""
        return self.result

    def has_next(self) -> bool:
        """Return True if there is a next page."""
        return self.number < self.paginator.num_pages

    def has_previous(self) -> bool:
        """Return True if there is a previous page."""
        return self.number > 1

    def has_other_pages(self) -> bool:
        """Return True if there are other pages."""
        return self.paginator.num_pages > 1

    def start_index(self) -> int:
        """Return the 0-based start index of this page."""
        return (self.number - 1) * self.paginator.page_size

    def end_index(self) -> int:
        """Return the 0-based end index of this page."""
        return self.start_index() + len(self.result) - 1

    def next_page_number(self) -> int:
        """Return the next page number."""
        return self.number + 1

    def previous_page_number(self) -> int:
        """Return the previous page number."""
        return self.number - 1
