"""
Core functionality for the spire library.

This module provides the main entry points and high-level interfaces
for document processing functionality.
"""

from .spire import Spire
from .processor import process_document, process_batch
from .config import SpireConfig

__all__ = [
    'Spire',
    'process_document',
    'process_batch',
    'SpireConfig',
]