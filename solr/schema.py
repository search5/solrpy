"""Schema API client for Solr 4.2+.

Provides programmatic access to Solr's managed schema for field,
field type, dynamic field, and copy field operations.
"""
from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING

from .exceptions import SolrVersionError

if TYPE_CHECKING:
    from .core import Solr


class SchemaAPI:
    """Client for Solr's Schema API.

    Accessed via ``conn.schema`` on a :class:`~solr.core.Solr` instance.
    All methods require Solr 4.2+.

    Example::

        conn = Solr('http://localhost:8983/solr/mycore')
        fields = conn.schema.fields()
        conn.schema.add_field('title', 'text_general', stored=True)
    """

    _MIN_VERSION = (4, 2)

    def __init__(self, conn: Solr) -> None:
        self._conn = conn

    def _check_version(self) -> None:
        if self._conn.server_version < self._MIN_VERSION:
            raise SolrVersionError("schema", self._MIN_VERSION,
                                   self._conn.server_version)

    def _get_json(self, endpoint: str) -> Any:
        """GET a schema endpoint and return parsed JSON."""
        self._check_version()
        path = '%s/schema%s' % (self._conn.path, endpoint)
        rsp = self._conn._get(path + '?wt=json')
        return json.loads(rsp.read().decode('utf-8'))

    def _modify(self, operation: str, body: dict[str, Any]) -> dict[str, Any]:
        """POST a schema modification command."""
        self._check_version()
        payload = json.dumps({operation: body})
        path = '%s/schema' % self._conn.path
        from .utils import read_response
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
        }
        rsp = self._conn._post(path, payload, headers)
        result: dict[str, Any] = json.loads(read_response(rsp))
        return result

    # -- Full schema --

    def get_schema(self) -> dict[str, Any]:
        """Return the full schema definition."""
        data = self._get_json('')
        result: dict[str, Any] = data.get('schema', data)
        return result

    # -- Fields --

    def fields(self) -> list[dict[str, Any]]:
        """List all fields."""
        data = self._get_json('/fields')
        result: list[dict[str, Any]] = data.get('fields', [])
        return result

    def add_field(self, name: str, field_type: str, **opts: Any) -> dict[str, Any]:
        """Add a new field."""
        body = {'name': name, 'type': field_type, **opts}
        return self._modify('add-field', body)

    def replace_field(self, name: str, field_type: str, **opts: Any) -> dict[str, Any]:
        """Replace an existing field definition."""
        body = {'name': name, 'type': field_type, **opts}
        return self._modify('replace-field', body)

    def delete_field(self, name: str) -> dict[str, Any]:
        """Delete a field by name."""
        return self._modify('delete-field', {'name': name})

    # -- Dynamic fields --

    def dynamic_fields(self) -> list[dict[str, Any]]:
        """List all dynamic field rules."""
        data = self._get_json('/dynamicfields')
        result: list[dict[str, Any]] = data.get('dynamicFields', [])
        return result

    def add_dynamic_field(self, name: str, field_type: str, **opts: Any) -> dict[str, Any]:
        """Add a new dynamic field rule."""
        body = {'name': name, 'type': field_type, **opts}
        return self._modify('add-dynamic-field', body)

    def delete_dynamic_field(self, name: str) -> dict[str, Any]:
        """Delete a dynamic field rule by name."""
        return self._modify('delete-dynamic-field', {'name': name})

    # -- Field types --

    def field_types(self) -> list[dict[str, Any]]:
        """List all field types."""
        data = self._get_json('/fieldtypes')
        result: list[dict[str, Any]] = data.get('fieldTypes', [])
        return result

    def add_field_type(self, **definition: Any) -> dict[str, Any]:
        """Add a new field type. Pass all attributes as keyword arguments."""
        return self._modify('add-field-type', definition)

    def replace_field_type(self, **definition: Any) -> dict[str, Any]:
        """Replace an existing field type."""
        return self._modify('replace-field-type', definition)

    def delete_field_type(self, name: str) -> dict[str, Any]:
        """Delete a field type by name."""
        return self._modify('delete-field-type', {'name': name})

    # -- Copy fields --

    def copy_fields(self) -> list[dict[str, Any]]:
        """List all copy field rules."""
        data = self._get_json('/copyfields')
        result: list[dict[str, Any]] = data.get('copyFields', [])
        return result

    def add_copy_field(self, source: str, dest: str, max_chars: int | None = None) -> dict[str, Any]:
        """Add a copy field rule."""
        body: dict[str, Any] = {'source': source, 'dest': dest}
        if max_chars is not None:
            body['maxChars'] = max_chars
        return self._modify('add-copy-field', body)

    def delete_copy_field(self, source: str, dest: str) -> dict[str, Any]:
        """Delete a copy field rule."""
        return self._modify('delete-copy-field', {'source': source, 'dest': dest})
