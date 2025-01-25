"""
Configuration dataclasses for the spire library.
"""

import logging
from dataclasses import dataclass, field
from typing import List
from pathlib import Path

from docling_core.types.doc import ImageRefMode
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.models.easyocr_model import EasyOcrOptions
from docling.models.tesseract_ocr_cli_model import TesseractCliOcrOptions

from .enums import (
    BackendType,
    OcrEngine,
    ProcessingMode,
    AccelerationType,
)

logger = logging.getLogger(__name__)

@dataclass
class OcrConfig:
    """Configuration for OCR processing."""
    engine: OcrEngine = field(default_factory=OcrEngine.get_default)
    languages: List[str] = field(default_factory=lambda: ["en"])
    force_full_page: bool = False
    use_gpu: bool = True
    confidence_threshold: float = 0.5

@dataclass
class TableConfig:
    """Configuration for table detection and processing."""
    enabled: bool = True
    cell_matching: bool = True
    detect_headers: bool = True
    min_confidence: float = 0.7

@dataclass
class ProcessingConfig:
    """
    The unified configuration for docling usage, including advanced toggles
    like 'enable_formulas' or 'enable_picture_classification'.
    """
    # High-level docling settings
    mode: ProcessingMode = ProcessingMode.STANDARD
    backend: BackendType = BackendType.PYPDFIUM

    # Performance
    acceleration: AccelerationType = AccelerationType.AUTO
    num_threads: int = 8

    # OCR & Tables
    ocr: OcrConfig = field(default_factory=OcrConfig)
    tables: TableConfig = field(default_factory=TableConfig)

    # Image settings
    image_scale: float = 2.0
    extract_figures: bool = True
    extract_formulas: bool = False

    # Debug
    debug_mode: bool = False
    save_intermediates: bool = False

    # Export
    export_formats: List[str] = field(default_factory=lambda: ["md"])
    image_mode: ImageRefMode = ImageRefMode.REFERENCED

    # Advanced toggles
    enable_formulas: bool = False
    enable_picture_classification: bool = False

    def to_pipeline_options(self) -> PdfPipelineOptions:
        """Convert to docling's PdfPipelineOptions."""
        pipe_opts = PdfPipelineOptions()

        # Accelerator
        pipe_opts.accelerator_options.num_threads = self.num_threads
        pipe_opts.accelerator_options.device = self.acceleration.value

        # Image handling
        if self.extract_figures or self.extract_formulas:
            pipe_opts.images_scale = self.image_scale
            pipe_opts.generate_page_images = True
            pipe_opts.generate_picture_images = True

        # OCR
        pipe_opts.do_ocr = (self.ocr.engine != OcrEngine.NONE)
        if pipe_opts.do_ocr:
            try:
                if self.ocr.engine == OcrEngine.EASYOCR:
                    pipe_opts.ocr_options = EasyOcrOptions(
                        force_full_page_ocr=self.ocr.force_full_page,
                        lang=self.ocr.languages,
                        use_gpu=self.ocr.use_gpu
                    )
                elif self.ocr.engine == OcrEngine.TESSERACT_CLI:
                    pipe_opts.ocr_options = TesseractCliOcrOptions(
                        force_full_page_ocr=self.ocr.force_full_page
                    )
                else:
                    logger.warning(f"Unsupported OCR engine {self.ocr.engine}; disabling OCR.")
                    pipe_opts.do_ocr = False
            except ImportError as e:
                logger.warning(f"OCR import failed: {e}")
                pipe_opts.do_ocr = False

        # Table extraction
        pipe_opts.do_table_structure = self.tables.enabled
        if self.tables.enabled:
            pipe_opts.table_structure_options.do_cell_matching = self.tables.cell_matching

        # Debug
        if self.debug_mode:
            from docling.datamodel.settings import settings
            settings.debug.profile_pipeline_timings = True
            settings.debug.visualize_layout = self.save_intermediates
            settings.debug.visualize_ocr = self.save_intermediates
            settings.debug.visualize_tables = self.save_intermediates

        return pipe_opts

    @classmethod
    def for_mode(cls, mode: ProcessingMode) -> "ProcessingConfig":
        """Convenience to build a config preset for a given mode."""
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