"""Schema API client for Solr 4.2+.

Provides programmatic access to Solr's managed schema for field,
field type, dynamic field, and copy field operations.

Since 2.0.4 this class accepts both :class:`~solr.core.Solr` and
:class:`~solr.async_solr.AsyncSolr`.  With a sync connection methods
return values directly; with an async connection they return coroutines.
"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .exceptions import SolrVersionError
from .transport import DualTransport, _chain

if TYPE_CHECKING:
    from .core import Solr


class SchemaAPI:
    """Client for Solr's Schema API.

    Created explicitly by the user. All methods require Solr 4.2+.

    Works with both ``Solr`` (sync) and ``AsyncSolr`` (async) connections.

    Example::

        from solr import Solr, AsyncSolr, SchemaAPI

        # Sync
        conn = Solr('http://localhost:8983/solr/mycore')
        schema = SchemaAPI(conn)
        fields = schema.fields()

        # Async
        async with AsyncSolr('http://localhost:8983/solr/mycore') as conn:
            schema = SchemaAPI(conn)
            fields = await schema.fields()
    """

    _MIN_VERSION = (4, 2)

    def __init__(self, conn: Any) -> None:
        """Initialize a SchemaAPI client.

        :param conn: A :class:`~solr.core.Solr` or :class:`~solr.async_solr.AsyncSolr` connection.
        """
        self._transport = DualTransport(conn)
        self._is_async: bool = self._transport.is_async

    def _check_version(self) -> None:
        """Raise SolrVersionError if server is too old."""
        if self._transport.server_version < self._MIN_VERSION:
            raise SolrVersionError("schema", self._MIN_VERSION,
                                   self._transport.server_version)

    def _get_json(self, endpoint: str) -> Any:
        """GET a schema endpoint and return parsed JSON (or coroutine)."""
        self._check_version()
        return self._transport.get_json('/schema' + endpoint)

    def _modify(self, operation: str, body: dict[str, Any]) -> Any:
        """POST a schema modification command (or coroutine)."""
        self._check_version()
        return self._transport.post_json('/schema', {operation: body})

    # -- Full schema --

    def get_schema(self) -> Any:
        """Return the full schema definition."""
        raw = self._get_json('')
        return _chain(raw, lambda d: d.get('schema', d))

    # -- Fields --

    def fields(self) -> Any:
        """List all fields."""
        raw = self._get_json('/fields')
        return _chain(raw, lambda d: d.get('fields', []))

    def add_field(self, name: str, field_type: str, **opts: Any) -> Any:
        """Add a new field.

        :param name: Name of the field to add.
        :param field_type: Solr field type (e.g. ``'string'``, ``'text_general'``).
        :param opts: Additional field properties (e.g. ``stored=True``, ``indexed=True``).
        """
        body = {'name': name, 'type': field_type, **opts}
        return self._modify('add-field', body)

    def replace_field(self, name: str, field_type: str, **opts: Any) -> Any:
        """Replace an existing field definition.

        :param name: Name of the field to replace.
        :param field_type: New Solr field type.
        :param opts: Additional field properties to set on the replacement.
        """
        body = {'name': name, 'type': field_type, **opts}
        return self._modify('replace-field', body)

    def delete_field(self, name: str) -> Any:
        """Delete a field by name.

        :param name: Name of the field to delete.
        """
        return self._modify('delete-field', {'name': name})

    # -- Dynamic fields --

    def dynamic_fields(self) -> Any:
        """List all dynamic field rules."""
        raw = self._get_json('/dynamicfields')
        return _chain(raw, lambda d: d.get('dynamicFields', []))

    def add_dynamic_field(self, name: str, field_type: str, **opts: Any) -> Any:
        """Add a new dynamic field rule.

        :param name: Dynamic field pattern (e.g. ``'*_txt'``).
        :param field_type: Solr field type for matching fields.
        :param opts: Additional field properties (e.g. ``stored=True``).
        """
        body = {'name': name, 'type': field_type, **opts}
        return self._modify('add-dynamic-field', body)

    def delete_dynamic_field(self, name: str) -> Any:
        """Delete a dynamic field rule by name.

        :param name: Dynamic field pattern to delete (e.g. ``'*_txt'``).
        """
        return self._modify('delete-dynamic-field', {'name': name})

    # -- Field types --

    def field_types(self) -> Any:
        """List all field types."""
        raw = self._get_json('/fieldtypes')
        return _chain(raw, lambda d: d.get('fieldTypes', []))

    def add_field_type(self, **definition: Any) -> Any:
        """Add a new field type. Pass all attributes as keyword arguments.

        :param definition: Field type attributes (e.g. ``name='myType'``,
            ``class_='solr.TextField'``).
        """
        return self._modify('add-field-type', definition)

    def replace_field_type(self, **definition: Any) -> Any:
        """Replace an existing field type.

        :param definition: Field type attributes for the replacement definition.
        """
        return self._modify('replace-field-type', definition)

    def delete_field_type(self, name: str) -> Any:
        """Delete a field type by name.

        :param name: Name of the field type to delete.
        """
        return self._modify('delete-field-type', {'name': name})

    # -- Copy fields --

    def copy_fields(self) -> Any:
        """List all copy field rules."""
        raw = self._get_json('/copyfields')
        return _chain(raw, lambda d: d.get('copyFields', []))

    def add_copy_field(self, source: str, dest: str, max_chars: int | None = None) -> Any:
        """Add a copy field rule.

        :param source: Source field name or glob pattern.
        :param dest: Destination field name.
        :param max_chars: Maximum number of characters to copy. ``None`` means unlimited.
        """
        body: dict[str, Any] = {'source': source, 'dest': dest}
        if max_chars is not None:
            body['maxChars'] = max_chars
        return self._modify('add-copy-field', body)

    def delete_copy_field(self, source: str, dest: str) -> Any:
        """Delete a copy field rule.

        :param source: Source field name or glob pattern.
        :param dest: Destination field name.
        """
        return self._modify('delete-copy-field', {'source': source, 'dest': dest})
