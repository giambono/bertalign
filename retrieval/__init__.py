"""
Retrieval system for cross-lingual text alignment.

This package provides tools for building and querying a FAISS-based
retrieval system for English-Italian text alignments.
"""

from retrieval.config import IndexConfig, RetrievalConfig
from retrieval.indexer import AlignmentIndexer

__all__ = [
    'IndexConfig',
    'RetrievalConfig',
    'AlignmentIndexer',
]