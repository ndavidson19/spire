from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any
import shutil
import logging

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    PdfPipelineOptions,
)

logger = logging.getLogger(__name__)

class BackendType(Enum):
    """Available PDF processing backends"""
    PYPDFIUM = "pypdfium"
    DOCLING_PARSE = "docling_parse"

class OcrEngine(Enum):
    """Available OCR engines"""
    NONE = "none"
    EASYOCR = "easyocr"
    TESSERACT = "tesseract"
    TESSERACT_CLI = "tesseract_cli"
    MAC = "mac"  # Mac-only
    RAPID = "rapid"
    
    @classmethod
    def get_default(cls) -> 'OcrEngine':
        """Get default OCR engine based on what's available"""
        # Try easyocr first
        try:
            import easyocr
            return cls.EASYOCR
        except ImportError:
            pass
        
        # Then tesseract
        if shutil.which('tesseract'):
            return cls.TESSERACT_CLI
            
        # Fallback to no OCR
        logger.warning("No OCR engines available, defaulting to no OCR")
        return cls.NONE

class ProcessingMode(Enum):
    """High-level processing modes"""
    SIMPLE = auto()    # Basic extraction without OCR
    STANDARD = auto()  # Standard processing with basic OCR 
    ENHANCED = auto()  # Enhanced with OCR and table extraction
    MAXIMUM = auto()   # Maximum quality with all features

class AccelerationType(Enum):
    """Available acceleration options"""
    CPU = AcceleratorDevice.CPU
    CUDA = AcceleratorDevice.CUDA
    MPS = AcceleratorDevice.MPS  
    AUTO = AcceleratorDevice.AUTO

@dataclass
class OcrConfig:
    """OCR-specific configuration"""
    engine: OcrEngine = field(default_factory=OcrEngine.get_default)
    languages: List[str] = field(default_factory=lambda: ["en"])
    force_full_page: bool = False
    use_gpu: bool = True
    confidence_threshold: float = 0.5

    def get_engine_languages(self, engine: OcrEngine) -> List[str]:
        """Get language codes for specific engine"""
        if engine == OcrEngine.EASYOCR:
            return [
                OCR_LANG_MAPPING[OcrEngine.EASYOCR].get(lang, lang) 
                for lang in self.languages
            ]
        return self.languages

@dataclass
class TableConfig:
    """Table extraction configuration"""
    enabled: bool = True
    cell_matching: bool = True
    detect_headers: bool = True
    min_confidence: float = 0.7

OCR_LANG_MAPPING = {
    OcrEngine.EASYOCR: {
        "eng": "en",  # EasyOCR uses 'en' instead of 'eng'
        "fra": "fr",
        # Add more mappings as needed
    }
}

@dataclass
class ProcessingConfig:
    """Complete processing configuration"""
    # High-level settings
    mode: ProcessingMode = ProcessingMode.STANDARD
    backend: BackendType = BackendType.PYPDFIUM
    
    # Performance settings
    acceleration: AccelerationType = AccelerationType.AUTO
    num_threads: int = 8
    
    # Feature settings
    ocr: OcrConfig = field(default_factory=OcrConfig)
    tables: TableConfig = field(default_factory=TableConfig)
    
    # Image settings
    image_scale: float = 2.0
    extract_figures: bool = True
    extract_formulas: bool = False
    
    # Debug settings
    debug_mode: bool = False
    save_intermediates: bool = False
    
    # Export settings
    export_formats: List[str] = field(default_factory=lambda: ["md"])
    
    def to_pipeline_options(self) -> PdfPipelineOptions:
        """Convert to docling PdfPipelineOptions"""
        pipeline_opts = PdfPipelineOptions()
        
        # Configure acceleration
        pipeline_opts.accelerator_options.num_threads = self.num_threads
        pipeline_opts.accelerator_options.device = self.acceleration.value
        
        # Configure image handling
        if self.extract_figures or self.extract_formulas:
            pipeline_opts.images_scale = self.image_scale
            pipeline_opts.generate_page_images = True
            pipeline_opts.generate_picture_images = True
        
        # Configure OCR
        pipeline_opts.do_ocr = self.ocr.engine != OcrEngine.NONE
        if pipeline_opts.do_ocr:
            try:
                if self.ocr.engine == OcrEngine.EASYOCR:
                    from docling.models.easyocr_model import EasyOcrOptions
                    pipeline_opts.ocr_options = EasyOcrOptions(
                        force_full_page_ocr=self.ocr.force_full_page,
                        lang=self.ocr.languages,
                        use_gpu=self.ocr.use_gpu
                    )
                elif self.ocr.engine == OcrEngine.TESSERACT_CLI:
                    from docling.models.tesseract_ocr_cli_model import TesseractCliOcrOptions
                    pipeline_opts.ocr_options = TesseractCliOcrOptions(
                        force_full_page_ocr=self.ocr.force_full_page
                    )
                else:
                    logger.warning(f"Unsupported OCR engine {self.ocr.engine}, disabling OCR")
                    pipeline_opts.do_ocr = False
            except ImportError as e:
                logger.warning(f"OCR engine {self.ocr.engine} not available: {e}")
                pipeline_opts.do_ocr = False
        
        # Configure table extraction
        pipeline_opts.do_table_structure = self.tables.enabled
        if self.tables.enabled:
            pipeline_opts.table_structure_options.do_cell_matching = self.tables.cell_matching
        
        # Configure debug settings
        if self.debug_mode:
            from docling.datamodel.settings import settings
            settings.debug.profile_pipeline_timings = True
            settings.debug.visualize_layout = self.save_intermediates
            settings.debug.visualize_ocr = self.save_intermediates
            settings.debug.visualize_tables = self.save_intermediates
        
        return pipeline_opts

    @classmethod
    def for_mode(cls, mode: ProcessingMode) -> 'ProcessingConfig':
        """Create a config preset for the given mode"""
        if mode == ProcessingMode.SIMPLE:
            return cls(
                mode=mode,
                backend=BackendType.PYPDFIUM,
                ocr=OcrConfig(engine=OcrEngine.NONE),
                tables=TableConfig(enabled=False),
                extract_figures=False,
                export_formats=["md", "txt"]
            )
        elif mode == ProcessingMode.STANDARD:
            return cls(
                mode=mode,
                backend=BackendType.DOCLING_PARSE,
                export_formats=["md", "json"]
            )
        elif mode == ProcessingMode.ENHANCED:
            return cls(
                mode=mode,
                backend=BackendType.DOCLING_PARSE,
                tables=TableConfig(enabled=True),
                extract_figures=True,
                export_formats=["md", "json", "txt"]
            )
        elif mode == ProcessingMode.MAXIMUM:
            return cls(
                mode=mode,
                backend=BackendType.DOCLING_PARSE,
                ocr=OcrConfig(force_full_page=True),
                tables=TableConfig(enabled=True, cell_matching=True),
                extract_figures=True,
                extract_formulas=True,
                export_formats=["md", "json", "yaml", "doctags"]
            )
        return cls(mode=mode)