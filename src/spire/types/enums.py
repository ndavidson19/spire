"""
Core enums for the spire library.
"""

import shutil
import logging
from enum import Enum, auto

from docling.datamodel.pipeline_options import AcceleratorDevice

logger = logging.getLogger(__name__)

class BackendType(Enum):
    """Available document processing backends."""
    PYPDFIUM = "pypdfium"
    DOCLING_PARSE = "docling_parse"
    DOCLING_PARSE_V2 = "docling_parse_v2"
    WORD = "word"
    POWERPOINT = "powerpoint"
    EXCEL = "excel"
    MARKDOWN = "markdown"
    ASCIIDOC = "asciidoc"
    HTML = "html"
    PUBMED = "pubmed"
    USPTO = "uspto"
    IMAGE = "image"
    JSON_DOCLING = "json_docling"

class OcrEngine(Enum):
    """Available OCR engines."""
    NONE = "none"
    EASYOCR = "easyocr"
    TESSERACT = "tesseract"
    TESSERACT_CLI = "tesseract_cli"
    MAC = "mac"  
    RAPID = "rapid"

    @classmethod
    def get_default(cls) -> 'OcrEngine':
        """Select a default OCR engine if available."""
        try:
            import easyocr  # type: ignore
            return cls.EASYOCR
        except ImportError:
            pass
        if shutil.which("tesseract"):
            return cls.TESSERACT_CLI
        logger.warning("No OCR engines available; defaulting to NONE.")
        return cls.NONE

class ProcessingMode(Enum):
    """High-level docling modes."""
    SIMPLE = auto()
    STANDARD = auto()
    ENHANCED = auto()
    MAXIMUM = auto()

class AccelerationType(Enum):
    """Hardware acceleration options."""
    CPU = AcceleratorDevice.CPU
    CUDA = AcceleratorDevice.CUDA
    MPS = AcceleratorDevice.MPS
    AUTO = AcceleratorDevice.AUTO