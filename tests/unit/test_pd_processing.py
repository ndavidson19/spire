import pytest
from pathlib import Path
import tempfile
import shutil

from docling.datamodel.base_models import InputFormat
from spire.core.config import (
    ProcessingConfig,
    ProcessingMode,
    BackendType,
    OcrEngine,
    AccelerationType,
    OcrConfig,
    TableConfig
)

def test_ocr_engine_detection():
    """Test OCR engine auto-detection"""
    engine = OcrEngine.get_default()
    assert isinstance(engine, OcrEngine)
    assert engine in [OcrEngine.EASYOCR, OcrEngine.TESSERACT_CLI, OcrEngine.NONE]

def test_processing_modes():
    """Test processing mode configurations"""
    # Simple mode
    simple_config = ProcessingConfig.for_mode(ProcessingMode.SIMPLE)
    assert simple_config.ocr.engine == OcrEngine.NONE
    assert not simple_config.tables.enabled
    assert "md" in simple_config.export_formats
    assert "txt" in simple_config.export_formats
    
    # Standard mode
    standard_config = ProcessingConfig.for_mode(ProcessingMode.STANDARD)
    assert standard_config.backend == BackendType.DOCLING_PARSE
    assert "md" in standard_config.export_formats
    assert "json" in standard_config.export_formats
    
    # Enhanced mode
    enhanced_config = ProcessingConfig.for_mode(ProcessingMode.ENHANCED)
    assert enhanced_config.tables.enabled
    assert enhanced_config.extract_figures
    assert "txt" in enhanced_config.export_formats
    
    # Maximum mode
    max_config = ProcessingConfig.for_mode(ProcessingMode.MAXIMUM)
    assert max_config.ocr.force_full_page
    assert max_config.tables.cell_matching
    assert max_config.extract_formulas
    assert "doctags" in max_config.export_formats

def test_pipeline_options_conversion():
    """Test conversion to pipeline options"""
    config = ProcessingConfig(
        mode=ProcessingMode.ENHANCED,
        acceleration=AccelerationType.CPU,
        num_threads=4,
        ocr=OcrConfig(engine=OcrEngine.NONE),
        debug_mode=True
    )
    
    pipeline_opts = config.to_pipeline_options()
    
    assert pipeline_opts.accelerator_options.device == AccelerationType.CPU.value
    assert pipeline_opts.accelerator_options.num_threads == 4
    assert not pipeline_opts.do_ocr
    assert pipeline_opts.do_table_structure

def test_gpu_acceleration_config():
    """Test GPU acceleration settings"""
    # CPU config
    cpu_config = ProcessingConfig(acceleration=AccelerationType.CPU)
    cpu_opts = cpu_config.to_pipeline_options()
    assert cpu_opts.accelerator_options.device == AccelerationType.CPU.value
    
    # CUDA config
    cuda_config = ProcessingConfig(acceleration=AccelerationType.CUDA)
    cuda_opts = cuda_config.to_pipeline_options()
    assert cuda_opts.accelerator_options.device == AccelerationType.CUDA.value
    
    # Auto config
    auto_config = ProcessingConfig(acceleration=AccelerationType.AUTO)
    auto_opts = auto_config.to_pipeline_options()
    assert auto_opts.accelerator_options.device == AccelerationType.AUTO.value

def test_ocr_configuration():
    """Test OCR configuration options"""
    # EasyOCR config
    easyocr_config = ProcessingConfig(
        ocr=OcrConfig(
            engine=OcrEngine.EASYOCR,
            languages=["eng", "fra"],
            use_gpu=True
        )
    )
    try:
        import easyocr
        opts = easyocr_config.to_pipeline_options()
        assert opts.do_ocr
        assert hasattr(opts.ocr_options, "lang")
        assert len(opts.ocr_options.lang) == 2
    except ImportError:
        # Skip if easyocr not available
        pass
    
    # Tesseract CLI config
    tesseract_config = ProcessingConfig(
        ocr=OcrConfig(
            engine=OcrEngine.TESSERACT_CLI,
            force_full_page=True
        )
    )
    if shutil.which('tesseract'):
        opts = tesseract_config.to_pipeline_options()
        assert opts.do_ocr
        assert opts.ocr_options.force_full_page_ocr

def test_table_configuration():
    """Test table extraction configuration"""
    config = ProcessingConfig(
        tables=TableConfig(
            enabled=True,
            cell_matching=True,
            detect_headers=True
        )
    )
    
    opts = config.to_pipeline_options()
    assert opts.do_table_structure
    assert opts.table_structure_options.do_cell_matching

def test_debug_configuration():
    """Test debug mode settings"""
    config = ProcessingConfig(
        debug_mode=True,
        save_intermediates=True
    )
    
    config.to_pipeline_options()
    # Debug settings should be configured in settings
    from docling.datamodel.settings import settings
    assert settings.debug.profile_pipeline_timings
    assert settings.debug.visualize_layout
    assert settings.debug.visualize_ocr
    assert settings.debug.visualize_tables