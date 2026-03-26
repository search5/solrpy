"""Tests for Extract handler wrapper (Solr 1.4+)."""

import io
import json
import mimetypes
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import solr
from solr.extract import Extract
from solr.exceptions import SolrVersionError


def _make_conn(version: tuple[int, ...] = (9, 0, 0)) -> solr.Solr:
    conn = solr.Solr.__new__(solr.Solr)
    conn.server_version = version
    conn.path = '/solr/core0'
    conn.auth_headers = {}
    conn.persistent = True
    return conn  # type: ignore[return-value]


def _mock_response(payload: dict) -> MagicMock:
    rsp = MagicMock()
    rsp.status = 200
    rsp.reason = 'OK'
    rsp.getheader.return_value = ''
    rsp.read.return_value = json.dumps(payload).encode('utf-8')
    return rsp


class TestExtractVersionGuard(unittest.TestCase):

    def test_raises_on_solr_1_3(self) -> None:
        conn = _make_conn((1, 3, 0))
        ext = Extract(conn)
        with self.assertRaises(SolrVersionError):
            ext(io.BytesIO(b'data'))

    def test_passes_on_solr_1_4(self) -> None:
        conn = _make_conn((1, 4, 0))
        conn.conn = MagicMock()
        conn.conn.getresponse.return_value = _mock_response({'responseHeader': {'status': 0}})
        ext = Extract(conn)
        result = ext(io.BytesIO(b'hello'))
        self.assertIn('responseHeader', result)

    def test_passes_on_modern_solr(self) -> None:
        conn = _make_conn((9, 0, 0))
        conn.conn = MagicMock()
        conn.conn.getresponse.return_value = _mock_response({'responseHeader': {'status': 0}})
        ext = Extract(conn)
        result = ext(io.BytesIO(b'hello'))
        self.assertIn('responseHeader', result)


class TestExtractQueryParams(unittest.TestCase):

    def setUp(self) -> None:
        self.conn = _make_conn()
        self.conn.conn = MagicMock()
        self.conn.conn.getresponse.return_value = _mock_response(
            {'responseHeader': {'status': 0}}
        )
        self.ext = Extract(self.conn)

    def _called_path(self) -> str:
        args = self.conn.conn.request.call_args[0]
        return args[1]

    def _called_body(self) -> bytes:
        args = self.conn.conn.request.call_args[0]
        return args[2]

    def _called_headers(self) -> dict:
        args = self.conn.conn.request.call_args[0]
        return args[3]

    def test_wt_json_always_sent(self) -> None:
        self.ext(io.BytesIO(b'data'))
        self.assertIn('wt=json', self._called_path())

    def test_commit_false_by_default(self) -> None:
        self.ext(io.BytesIO(b'data'))
        self.assertNotIn('commit=true', self._called_path())

    def test_commit_true_when_requested(self) -> None:
        self.ext(io.BytesIO(b'data'), commit=True)
        self.assertIn('commit=true', self._called_path())

    def test_literal_param_dot_notation(self) -> None:
        self.ext(io.BytesIO(b'data'), literal_id='doc1')
        self.assertIn('literal.id=doc1', self._called_path())

    def test_literal_field_with_underscore_preserved(self) -> None:
        # literal_my_field → literal.my_field (only first underscore replaced)
        self.ext(io.BytesIO(b'data'), literal_my_field='value')
        self.assertIn('literal.my_field=value', self._called_path())

    def test_extract_path_correct(self) -> None:
        self.ext(io.BytesIO(b'data'))
        path = self._called_path()
        self.assertIn('/update/extract', path)

    def test_file_content_sent_as_body(self) -> None:
        content = b'binary file content'
        self.ext(io.BytesIO(content))
        self.assertEqual(self._called_body(), content)

    def test_content_type_header_sent(self) -> None:
        self.ext(io.BytesIO(b'data'), content_type='application/pdf')
        self.assertEqual(self._called_headers()['Content-Type'], 'application/pdf')

    def test_default_content_type_octet_stream(self) -> None:
        self.ext(io.BytesIO(b'data'))
        self.assertEqual(self._called_headers()['Content-Type'],
                         'application/octet-stream')


class TestExtractOnly(unittest.TestCase):

    def setUp(self) -> None:
        self.conn = _make_conn()
        self.conn.conn = MagicMock()
        self.ext = Extract(self.conn)

    def _set_response(self, payload: dict) -> None:
        self.conn.conn.getresponse.return_value = _mock_response(payload)

    def test_extract_only_sets_param(self) -> None:
        self._set_response({'responseHeader': {'status': 0}, '': '', '_': {}})
        self.ext.extract_only(io.BytesIO(b'data'))
        path = self.conn.conn.request.call_args[0][1]
        self.assertIn('extractOnly=true', path)

    def test_returns_text_and_metadata(self) -> None:
        self._set_response({
            'responseHeader': {'status': 0},
            '': 'extracted text',
            '_': {'Content-Type': ['application/pdf']},
        })
        text, metadata = self.ext.extract_only(io.BytesIO(b'data'))
        self.assertEqual(text, 'extracted text')
        self.assertEqual(metadata['Content-Type'], ['application/pdf'])

    def test_returns_empty_text_when_absent(self) -> None:
        self._set_response({'responseHeader': {'status': 0}})
        text, metadata = self.ext.extract_only(io.BytesIO(b'data'))
        self.assertEqual(text, '')
        self.assertEqual(metadata, {})


class TestExtractFromPath(unittest.TestCase):

    def setUp(self) -> None:
        self.conn = _make_conn()
        self.conn.conn = MagicMock()
        self.conn.conn.getresponse.return_value = _mock_response(
            {'responseHeader': {'status': 0}}
        )
        self.ext = Extract(self.conn)

    def test_from_path_reads_file(self) -> None:
        content = b'pdf binary content'
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(content)
            tmp_path = f.name
        try:
            self.ext.from_path(tmp_path)
            body = self.conn.conn.request.call_args[0][2]
            self.assertEqual(body, content)
        finally:
            os.unlink(tmp_path)

    def test_from_path_guesses_mime_type(self) -> None:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'data')
            tmp_path = f.name
        try:
            self.ext.from_path(tmp_path)
            headers = self.conn.conn.request.call_args[0][3]
            self.assertEqual(headers['Content-Type'], 'application/pdf')
        finally:
            os.unlink(tmp_path)

    def test_from_path_unknown_extension_uses_octet_stream(self) -> None:
        with tempfile.NamedTemporaryFile(suffix='.xyz123', delete=False) as f:
            f.write(b'data')
            tmp_path = f.name
        try:
            self.ext.from_path(tmp_path)
            headers = self.conn.conn.request.call_args[0][3]
            self.assertEqual(headers['Content-Type'], 'application/octet-stream')
        finally:
            os.unlink(tmp_path)

    def test_extract_from_path_sets_extract_only(self) -> None:
        self.conn.conn.getresponse.return_value = _mock_response(
            {'responseHeader': {'status': 0}, '': 'text', '_': {}}
        )
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'hello world')
            tmp_path = f.name
        try:
            text, _ = self.ext.extract_from_path(tmp_path)
            path = self.conn.conn.request.call_args[0][1]
            self.assertIn('extractOnly=true', path)
        finally:
            os.unlink(tmp_path)


class TestExtractImport(unittest.TestCase):

    def test_importable_from_top_level(self) -> None:
        from solr import Extract as TopLevel
        self.assertIs(TopLevel, Extract)


if __name__ == "__main__":
    unittest.main()
