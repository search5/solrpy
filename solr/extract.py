"""Solr Cell (Tika) document extraction wrapper for Solr 1.4+."""
from __future__ import annotations

import json
import mimetypes
import urllib.parse as urllib
from typing import Any, IO, TYPE_CHECKING

from .exceptions import SolrVersionError
from .utils import check_response_status, read_response

if TYPE_CHECKING:
    from .core import Solr


class Extract:
    """Index or extract rich documents via Solr's ExtractingRequestHandler (Solr 1.4+).

    Solr Cell integrates Apache Tika to extract text and metadata from rich
    documents (PDF, Word, HTML, etc.) and index them into Solr. The
    ``/update/extract`` handler must be configured in ``solrconfig.xml``.

    Example::

        from solr import Solr, Extract

        conn = Solr('http://localhost:8983/solr/mycore')
        extract = Extract(conn)

        # Index a document with literal field values
        with open('report.pdf', 'rb') as f:
            extract(f, content_type='application/pdf',
                    literal_id='report1', literal_title='Annual Report',
                    commit=True)

        # Extract text and metadata without indexing
        with open('report.pdf', 'rb') as f:
            text, metadata = extract.extract_only(f, content_type='application/pdf')
        print(text[:200])
        print(metadata.get('Content-Type'))

        # Convenience helpers that open the file by path
        extract.from_path('report.pdf', literal_id='report1', commit=True)
        text, metadata = extract.extract_from_path('report.pdf')
    """

    _MIN_VERSION = (1, 4)

    def __init__(self, conn: Solr) -> None:
        self._conn = conn

    def _check_version(self) -> None:
        if self._conn.server_version < self._MIN_VERSION:
            raise SolrVersionError("extract", self._MIN_VERSION,
                                   self._conn.server_version)

    def __call__(self, file_obj: IO[bytes],
                 content_type: str = 'application/octet-stream',
                 commit: bool = False,
                 **params: Any) -> dict[str, Any]:
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
        path = '%s/update/extract?%s' % (self._conn.path, qs)

        body = file_obj.read()
        headers: dict[str, str] = {'Content-Type': content_type}
        headers.update(self._conn.auth_headers)

        self._conn.conn.request('POST', path, body, headers)
        rsp = check_response_status(self._conn.conn.getresponse())
        result: dict[str, Any] = json.loads(read_response(rsp))
        return result

    def extract_only(self, file_obj: IO[bytes],
                     content_type: str = 'application/octet-stream',
                     **params: Any) -> tuple[str, dict[str, Any]]:
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
        result = self(file_obj, content_type, **params)
        text: str = result.get('', '') or ''
        metadata: dict[str, Any] = result.get('_', {}) or {}
        return text, metadata

    def from_path(self, file_path: str, **params: Any) -> dict[str, Any]:
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
                          **params: Any) -> tuple[str, dict[str, Any]]:
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
