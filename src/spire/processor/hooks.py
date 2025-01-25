"""
Pre and post-processing hooks for document processing.
"""

from pathlib import Path
from typing import Callable, Protocol

from docling.datamodel.document import ConversionResult
from src.spire.types.config import ProcessingConfig

class PreProcessHook(Protocol):
    """Protocol for pre-processing hooks."""
    def __call__(self, path: Path, config: ProcessingConfig) -> None:
        """
        Execute pre-processing hook.
        
        Args:
            path: Path to the input document
            config: Current processing configuration
        """
        ...

class PostProcessHook(Protocol):
    """Protocol for post-processing hooks."""
    def __call__(self, result: ConversionResult, config: ProcessingConfig) -> None:
        """
        Execute post-processing hook.
        
        Args:
            result: Result of document conversion
            config: Current processing configuration
        """
        ...

# Common hook implementations
def file_existence_check(path: Path, config: ProcessingConfig) -> None:
    """Pre-process hook to verify file exists."""
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

def log_conversion_status(result: ConversionResult, config: ProcessingConfig) -> None:
    """Post-process hook to log conversion status."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Document conversion completed with status: {result.status}")