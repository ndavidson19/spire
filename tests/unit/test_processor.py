import pytest
from pathlib import Path
import tempfile
import shutil

from docling.datamodel.base_models import InputFormat
from spire.core.processor import DocumentProcessor
from spire.core.config import (
    ProcessingConfig,
    ProcessingMode,
    BackendType,
    OcrEngine,
    AccelerationType,
    OcrConfig,
    TableConfig
)

@pytest.fixture(scope="session")
def test_files_dir():
    """Ensure test data directory exists and contains required files"""
    data_dir = Path("tests/data")
    if not data_dir.exists() or not list(data_dir.glob("*.pdf")):
        pytest.skip("Test data not found. Run scripts/create_test_data.py first")
    return data_dir

@pytest.fixture
def output_dir():
    """Temporary directory for test outputs"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_pdf(test_files_dir):
    """Get a sample PDF file"""
    pdf_path = list(test_files_dir.glob("*.pdf"))[0]
    if not pdf_path.exists():
        pytest.skip("Sample PDF not found")
    return pdf_path

def test_simple_mode_processing(sample_pdf, output_dir):
    """Test processing with simple mode (no OCR)"""
    processor = DocumentProcessor.for_mode(ProcessingMode.SIMPLE)
    result = processor.process(sample_pdf, output_dir)
    
    assert result["document"] is not None
    assert (output_dir / f"{sample_pdf.stem}.md").exists()

def test_standard_mode_processing(sample_pdf, output_dir):
    """Test processing with standard mode"""
    processor = DocumentProcessor.for_mode(ProcessingMode.STANDARD)
    result = processor.process(sample_pdf, output_dir)
    
    assert result["document"] is not None
    assert result["result"].status is not None  # Use result.status instead of status directly

def test_batch_processing(test_files_dir, output_dir):
    """Test batch processing multiple documents"""
    pdf_files = list(test_files_dir.glob("*.pdf"))[:2]
    processor = DocumentProcessor.for_mode(ProcessingMode.STANDARD)
    results = processor.batch_process(pdf_files, output_dir)
    
    assert len(results) == len(pdf_files)
    for result, pdf_path in zip(results, pdf_files):
        assert result["document"] is not None  # Remove error check since DocumentConverter raises
        assert (output_dir / f"{pdf_path.stem}.md").exists()

def test_custom_config_processing(sample_pdf, output_dir):
    """Test processing with custom configuration"""
    config = ProcessingConfig(
        mode=ProcessingMode.ENHANCED,
        backend=BackendType.PYPDFIUM,
        ocr=OcrConfig(
            engine=OcrEngine.TESSERACT,
            languages=["eng", "fra"],
            force_full_page=True
        ),
        tables=TableConfig(
            enabled=True,
            cell_matching=True,
            detect_headers=True
        ),
        export_formats=["md", "json", "txt"]
    )
    
    processor = DocumentProcessor(config)
    result = processor.process(sample_pdf, output_dir)
    
    assert result["document"] is not None
    for fmt in ["md", "json", "txt"]:
        assert (output_dir / f"{sample_pdf.stem}.{fmt}").exists()
        
def test_gpu_acceleration():
    """Test GPU acceleration configuration"""
    config = ProcessingConfig(
        mode=ProcessingMode.ENHANCED,
        acceleration=AccelerationType.CUDA,
        num_threads=4
    )
    
    processor = DocumentProcessor(config)
    converter = processor.converter
    
    pdf_format_option = converter.format_to_options[InputFormat.PDF]
    pipeline_options = pdf_format_option.pipeline_options
    
    assert pipeline_options is not None
    assert pipeline_options.accelerator_options.device == AccelerationType.CUDA.value
    assert pipeline_options.accelerator_options.num_threads == 4

def test_error_handling(test_files_dir):
    """Test error handling for non-existent file"""
    processor = DocumentProcessor.for_mode(ProcessingMode.SIMPLE)
    with pytest.raises(FileNotFoundError):
        processor.process(test_files_dir / "non_existent.pdf")