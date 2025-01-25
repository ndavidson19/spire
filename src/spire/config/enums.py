"""
Enums used throughout the docling package.
"""

import shutil
from enum import Enum, auto
from typing import ClassVar

from docling_core.types.doc import ImageRefMode
from docling.datamodel.pipeline_options import AcceleratorDevice

class BackendType(Enum):
    """Available PDF processing backends."""
    PYPDFIUM = "pypdfium"
    DOCLING_PARSE = "docling_parse"


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


class ImageMode(Enum):
    """Image reference modes for exports."""
    REFERENCED = ImageRefMode.REFERENCED
    EMBEDDED = ImageRefMode.EMBEDDED