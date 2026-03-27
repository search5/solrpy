"""Solr Cell (Tika) document extraction wrapper for Solr 1.4+.

Since 2.0.4 this class accepts both :class:`~solr.core.Solr` and
:class:`~solr.async_solr.AsyncSolr`.
"""
from __future__ import annotations

import json
import mimetypes
import urllib.parse as urllib
from typing import Any, IO, TYPE_CHECKING

from .exceptions import SolrVersionError
from .transport import DualTransport, _chain

if TYPE_CHECKING:
    from .core import Solr


class Extract:
    """Index or extract rich documents via Solr's ExtractingRequestHandler (Solr 1.4+).

    Works with both ``Solr`` (sync) and ``AsyncSolr`` (async) connections.

    Example::

        from solr import Solr, Extract

        conn = Solr('http://localhost:8983/solr/mycore')
        extract = Extract(conn)

        with open('report.pdf', 'rb') as f:
            extract(f, content_type='application/pdf',
                    literal_id='report1', commit=True)

        text, metadata = extract.extract_from_path('report.pdf')
    """

    _MIN_VERSION = (1, 4)

    def __init__(self, conn: Any) -> None:
        """Initialize an Extract handler client.

        :param conn: A :class:`~solr.core.Solr` or :class:`~solr.async_solr.AsyncSolr` connection.
        """
        self._transport = DualTransport(conn)
        self._is_async: bool = self._transport.is_async

    def _check_version(self) -> None:
        """Raise SolrVersionError if server is too old."""
        if self._transport.server_version < self._MIN_VERSION:
            raise SolrVersionError("extract", self._MIN_VERSION,
                                   self._transport.server_version)

    def __call__(self, file_obj: IO[bytes],
                 content_type: str = 'application/octet-stream',
                 commit: bool = False,
                 **params: Any) -> Any:
        """Index a rich document via ``/update/extract``.

        Args:
            file_obj: Binary file-like object containing the document to
                index. Must be opened in binary mode.
            content_type: MIME type of the file (e.g. ``'application/pdf'``).
                Defaults to ``'application/octet-stream'``.
            commit: If ``True``, commit changes to the index immediately.
                Defaults to ``False``.
            **params: Additional Solr parameters. The **first** underscore in
                each key is replaced with a dot to form the Solr parameter
                name: ``literal_id='x'`` → ``literal.id=x``,
                ``stream_type='text/html'`` → ``stream.type=text/html``.
                Field names that themselves contain underscores are preserved:
                ``literal_my_field='v'`` → ``literal.my_field=v``.

        Returns:
            Parsed JSON response dict from Solr (contains ``responseHeader``).

        Raises:
            SolrVersionError: If the connected Solr server is older than 1.4.
        """
        self._check_version()

        query_parts: list[tuple[str, str]] = [('wt', 'json')]
        if commit:
            query_parts.append(('commit', 'true'))
        for key, value in params.items():
            solr_key = key.replace('_', '.', 1)
            query_parts.append((solr_key, str(value)))

        qs = urllib.urlencode(query_parts)
        body = file_obj.read()
        headers: dict[str, str] = {'Content-Type': content_type}
        raw = self._transport.post_raw('/update/extract?' + qs, body, headers)
        return _chain(raw, lambda text: json.loads(text))

    def extract_only(self, file_obj: IO[bytes],
                     content_type: str = 'application/octet-stream',
                     **params: Any) -> Any:
        """Extract text and metadata without indexing the document.

        Calls ``/update/extract`` with ``extractOnly=true``. The document is
        NOT added to the Solr index.

        Args:
            file_obj: Binary file-like object.
            content_type: MIME type of the file.
            **params: Additional Solr parameters (same key convention as
                :meth:`__call__`).

        Returns:
            A ``(text, metadata)`` tuple where *text* is the extracted plain
            text (str) and *metadata* is a dict of Tika metadata fields
            (e.g. ``Content-Type``, ``Author``, ``title``).
        """
        params['extractOnly'] = 'true'
        raw = self(file_obj, content_type, **params)

        def _parse(result: dict[str, Any]) -> tuple[str, dict[str, Any]]:
            text: str = result.get('', '') or ''
            metadata: dict[str, Any] = result.get('_', {}) or {}
            return text, metadata

        return _chain(raw, _parse)

    def from_path(self, file_path: str, **params: Any) -> Any:
        """Index a document from a filesystem path.

        The MIME type is guessed from the file extension via
        :mod:`mimetypes`. Falls back to ``'application/octet-stream'``
        when the type cannot be determined.

        Args:
            file_path: Absolute or relative path to the file.
            **params: Forwarded to :meth:`__call__` (``commit``,
                ``literal_*``, etc.).

        Returns:
            Parsed JSON response dict from Solr.
        """
        ct, _ = mimetypes.guess_type(file_path)
        content_type = ct or 'application/octet-stream'
        with open(file_path, 'rb') as f:
            return self(f, content_type, **params)

    def extract_from_path(self, file_path: str,
                          **params: Any) -> Any:
        """Extract text and metadata from a file path without indexing.

        Convenience wrapper around :meth:`extract_only` that opens the file
        by path and guesses its MIME type.

        Args:
            file_path: Absolute or relative path to the file.
            **params: Forwarded to :meth:`extract_only`.

        Returns:
            A ``(text, metadata)`` tuple.
        """
        ct, _ = mimetypes.guess_type(file_path)
        content_type = ct or 'application/octet-stream'
        with open(file_path, 'rb') as f:
            return self.extract_only(f, content_type, **params)
