from __future__ import annotations


class SolrException(Exception):
    """An exception thrown by solr connections.

    Detailed information is provided in attributes of the exception object.
    """

    httpcode: int | str | None = 400
    """HTTP response code from Solr."""

    reason: str | None = None
    """Error message from the HTTP response sent by Solr."""

    body: str | bytes | None = None
    """Response body returned by Solr.

    This can contain much more information about the error, including
    tracebacks from the Java runtime.
    """

    def __init__(self, httpcode: int | str | None = None, reason: str | None = None, body: str | bytes | None = None) -> None:
        self.httpcode = httpcode
        self.reason = reason
        self.body = body

    def __repr__(self) -> str:
        return 'HTTP code=%s, Reason=%s, body=%s' % (  # type: ignore[str-bytes-safe]
                    self.httpcode, self.reason, self.body)

    def __str__(self) -> str:
        return 'HTTP code=%s, reason=%s' % (self.httpcode, self.reason)


class SolrVersionError(Exception):
    """Raised when a feature requires a higher Solr version than connected."""

    def __init__(self, feature: str, required: tuple[int, ...], actual: tuple[int, ...]) -> None:
        self.feature = feature
        self.required = required
        self.actual = actual

    def __str__(self) -> str:
        req = ".".join(str(v) for v in self.required)
        act = ".".join(str(v) for v in self.actual)
        return "%s requires Solr %s+, but connected to Solr %s" % (
            self.feature, req, act)
