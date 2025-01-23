# in spire/core/utils.py
import shutil
from enum import Enum, auto
from typing import Set
import logging

logger = logging.getLogger(__name__)

class AvailableEngines:
    """Detect available document processing engines"""
    
    @staticmethod
    def check_tesseract() -> bool:
        """Check if tesseract is available"""
        return shutil.which('tesseract') is not None
    
    @staticmethod
    def check_easyocr() -> bool:
        """Check if easyocr is available"""
        try:
            import easyocr
            return True
        except ImportError:
            return False
            
    @staticmethod
    def get_available_ocr_engines() -> Set[str]:
        """Get set of available OCR engines"""
        available = set()
        if AvailableEngines.check_tesseract():
            available.add("tesseract")
            available.add("tesseract_cli")
        if AvailableEngines.check_easyocr():
            available.add("easyocr")
        return available