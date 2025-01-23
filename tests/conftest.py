import pytest
import tempfile
import shutil
from pathlib import Path
import logging

# Configure logging for tests
@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Configure logging for all tests"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Suppress specific deprecation warnings
    import warnings
    warnings.filterwarnings(
        "ignore", 
        category=DeprecationWarning,
        module="docling.pipeline.standard_pdf_pipeline"
    )
    warnings.filterwarnings(
        "ignore",
        category=UserWarning,
        module="docling.models.easyocr_model"
    )

@pytest.fixture(scope="session")
def test_files_dir():
    """Ensure test data directory exists and contains required files"""
    data_dir = Path("tests/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    if not list(data_dir.glob("*.pdf")):
        pytest.skip("Test data not found. Run scripts/create_test_data.py first")
    return data_dir

@pytest.fixture
def output_dir():
    """Temporary directory for test outputs"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture(scope="session")
def sample_pdf(test_files_dir):
    """Get a sample PDF file"""
    pdf_files = list(test_files_dir.glob("*.pdf"))
    if not pdf_files:
        pytest.skip("No PDF files found in test directory")
    return pdf_files[0]

@pytest.fixture(scope="session")
def available_ocr_engines():
    """Check available OCR engines"""
    engines = set()
    if shutil.which('tesseract'):
        engines.add("tesseract")
    try:
        import easyocr
        engines.add("easyocr")
    except ImportError:
        pass
    return engines

# Common configuration presets
@pytest.fixture
def standard_config(available_ocr_engines):
    """Standard processing configuration"""
    from spire.core.config import ProcessingConfig, ProcessingMode, OcrEngine
    config = ProcessingConfig.for_mode(ProcessingMode.STANDARD)
    if not available_ocr_engines:
        config.ocr.engine = OcrEngine.NONE
    return config

@pytest.fixture
def enhanced_config(available_ocr_engines):
    """Enhanced processing configuration"""
    from spire.core.config import ProcessingConfig, ProcessingMode, OcrEngine
    config = ProcessingConfig.for_mode(ProcessingMode.ENHANCED)
    if not available_ocr_engines:
        config.ocr.engine = OcrEngine.NONE
    return config

@pytest.fixture
def maximum_config(available_ocr_engines):
    """Maximum quality configuration"""
    from spire.core.config import ProcessingConfig, ProcessingMode, OcrEngine
    config = ProcessingConfig.for_mode(ProcessingMode.MAXIMUM)
    if not available_ocr_engines:
        config.ocr.engine = OcrEngine.NONE
    return config

def pytest_configure(config):
    """Add custom markers"""
    config.addinivalue_line(
        "markers", "requires_ocr: mark test as requiring OCR capabilities"
    )