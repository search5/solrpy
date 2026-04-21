from __future__ import annotations

import datetime
from typing import Any, IO
from xml.sax import make_parser
from xml.sax.handler import ContentHandler

from .exceptions import SolrException
from .response import Response, Results, GroupedResult, HighlightingResult
from .utils import utc_from_string


def parse_json_response(data: dict[str, Any], params: dict[str, Any], query: Any) -> Response:
    """Parse a JSON response dict from Solr into a Response object."""
    response = Response(query)
    response._params = params

    response.header = data.get('responseHeader', {})

    resp_data = data.get('response', {})
    response.numFound = resp_data.get('numFound', 0)
    response.start = resp_data.get('start', 0)
    if 'maxScore' in resp_data:
        response.maxScore = resp_data['maxScore']

    response.results = Results(resp_data.get('docs', []))
    response.results.numFound = response.numFound
    response.results.start = response.start

    for key, value in data.items():
        if key not in ('responseHeader', 'response'):
            setattr(response, key, value)

    if hasattr(response, 'grouped') and isinstance(response.grouped, dict):
        response.grouped = GroupedResult(response.grouped)

    if hasattr(response, 'highlighting') and isinstance(response.highlighting, dict):
        response.highlighting = HighlightingResult(response.highlighting)

    return response


def parse_query_response(data: IO[str], params: dict[str, Any], query: Any) -> Any:
    """Parse the XML results of a /select call."""
    parser = make_parser()
    handler = ResponseContentHandler()
    parser.setContentHandler(handler)
    parser.parse(data)
    if handler.stack[0].children:
        response = handler.stack[0].children[0].final
        response._params = params
        response._query = query
        return response
    else:
        return None


class ResponseContentHandler(ContentHandler):
    """ContentHandler for the XML results of a /select call.
    (Versions 2.2 (and possibly 2.1))
    """
    def __init__(self) -> None:
        self.stack: list[Node] = [Node(None, {})]
        self.in_tree: bool = False

    def startElement(self, name: str, attrs: Any) -> None:
        """Handle an opening XML tag."""
        if not self.in_tree:
            if name != 'response':
                raise SolrException(
                    "Unknown XML response from server: <%s ..." % (
                        name))
            self.in_tree = True

        element = Node(name, attrs)
        self.stack.append(element)
        self.stack[-2].children.append(element)

    def characters(self, ch: str) -> None:
        """Accumulate character data."""
        self.stack[-1].chars.append(ch)

    def endElement(self, name: str) -> None:
        """Handle a closing XML tag and build the final value."""
        node = self.stack.pop()

        tag = node.name or name
        value = "".join(node.chars)

        if tag == 'int':
            node.final = int(value.strip())

        elif tag == 'str':
            node.final = value

        elif tag == 'null':
            node.final = None

        elif tag == 'long':
            node.final = int(value.strip())

        elif tag == 'bool':
            node.final = value.strip().lower().startswith('t')

        elif tag == 'date':
            node.final = utc_from_string(value.strip())

        elif tag in ('float', 'double', 'status', 'QTime'):
            node.final = float(value.strip())

        elif tag == 'response':
            node.final = response = Response(self)
            for child in node.children:
                child_name = child.attrs.get('name', child.name)
                if child_name == 'responseHeader':
                    child_name = 'header'
                elif child.name == 'result':
                    child_name = 'results'
                    for attr_name in child.attrs.getNames():
                        if attr_name != "name":
                            setattr(response, attr_name, child.attrs.get(attr_name))

                setattr(response, child_name, child.final)

            if hasattr(response, 'grouped') and isinstance(response.grouped, dict):
                response.grouped = GroupedResult(response.grouped)

        elif tag in ('lst', 'doc'):
            node.final = dict(
                    [(cnode.attrs['name'], cnode.final)
                        for cnode in node.children])

        elif tag in ('arr',):
            node.final = [cnode.final for cnode in node.children]

        elif tag == 'result':
            node.final = Results([cnode.final for cnode in node.children])

        elif tag in ('responseHeader',):
            node.final = dict([(cnode.name, cnode.final)
                        for cnode in node.children])
        else:
            raise SolrException("Unknown tag: %s" % tag)

        for attr, val in node.attrs.items():
            if attr != 'name':
                setattr(node.final, attr, val)


class Node:
    """A temporary object used in XML processing. Not seen by end user."""

    def __init__(self, name: str | None, attrs: Any) -> None:
        """*final* will eventually be the "final" representation of
        this node, whether an int, list, dict, etc."""
        self.chars: list[str] = []
        self.name = name
        self.attrs = attrs
        self.final: Any = None
        self.children: list[Node] = []

    def __repr__(self) -> str:
        return '<%s val="%s" %s>' % (
            self.name,
            "".join(self.chars).strip(),
            ' '.join(['%s="%s"' % (attr, val)
                            for attr, val in self.attrs.items()]))
