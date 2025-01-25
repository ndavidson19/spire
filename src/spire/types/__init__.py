"""
Core types and enums for the spire library.
"""

from .enums import (
    BackendType,
    OcrEngine,
    ProcessingMode,
    AccelerationType,
)
from .config import (
    OcrConfig,
    TableConfig,
    ProcessingConfig,
)

__all__ = [
    'BackendType',
    'OcrEngine',
    'ProcessingMode',
    'AccelerationType',
    'OcrConfig',
    'TableConfig',
    'ProcessingConfig',
]