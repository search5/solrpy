"""Backward-compatible aliases for async companion classes.

Since 2.0.4 the main companion classes (SchemaAPI, KNN, MoreLikeThis,
Suggest, Extract) work with both ``Solr`` and ``AsyncSolr``.  The
``Async*`` names are preserved as aliases for backward compatibility.
"""
from .schema import SchemaAPI as AsyncSchemaAPI
from .knn import KNN as AsyncKNN
from .mlt import MoreLikeThis as AsyncMoreLikeThis
from .suggest import Suggest as AsyncSuggest
from .extract import Extract as AsyncExtract

__all__ = [
    'AsyncSchemaAPI',
    'AsyncKNN',
    'AsyncMoreLikeThis',
    'AsyncSuggest',
    'AsyncExtract',
]
