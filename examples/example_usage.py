#!/usr/bin/env python3
"""
Example usage of the refactored spire library.
Demonstrates equivalent functionality to the original implementation.
"""

import logging
from pathlib import Path
from typing import Dict

from src.spire.core import Spire, SpireConfig
from src.spire.types.enums import BackendType
from docling.datamodel.document import ConversionResult
from docling.datamodel.base_models import ConversionStatus
from docling_core.types.doc import ImageRefMode

logger = logging.getLogger(__name__)

class MockDbClient:
    """Mock database client for demonstration."""
    def insert_document(self, doc_dict: dict):
        logger.info(f"[DB] Inserted doc with keys: {list(doc_dict.keys())}")

def my_pre_hook(path: Path, cfg: Dict) -> None:
    """Example pre-processing hook."""
    logger.info(f"Pre-hook => Checking file {path}")
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist")

def my_post_hook(conv_res: ConversionResult, cfg: Dict) -> None:
    """Example post-processing hook."""
    logger.info(f"Post-hook => Conversion status {conv_res.status}")

def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Create configuration
    config = SpireConfig(
        mode="enhanced",
        enable_formulas=True,
        enable_pictures=True,
        output_formats=["md", "html", "json"],
        embed_images=True,  # Equivalent to ImageRefMode.EMBEDDED
        backend="docling_parse"
    )

    # Initialize processor with configuration
    doc = Spire(config=config)
    
    # Add database client
    doc.processor.store_in_db = True
    doc.processor.db_client = MockDbClient()
    
    # Set specific pipeline
    doc.processor.pipeline_key = "multi_enrichment"
    
    # Add hooks
    doc.add_pre_hook(my_pre_hook)
    doc.add_post_hook(my_post_hook)

    # Process documents
    input_files = [
        "tests/data/1706.03762v7.pdf",
        "tests/data/jakes-resume.pdf"
    ]

    results = doc.process_batch(
        input_files,
        output_dir="scratch_universal"
    )

    # Calculate statistics
    fails = sum(r["result"].status == ConversionStatus.FAILURE for r in results)
    partials = sum(r["result"].status == ConversionStatus.PARTIAL_SUCCESS for r in results)
    successes = sum(r["result"].status == ConversionStatus.SUCCESS for r in results)

    logger.info(f"Done => successes={successes}, partials={partials}, fails={fails}")

# Alternative implementation using lower-level API for comparison
def main_alternative():
    """
    Alternative implementation using lower-level API.
    Demonstrates that we can still access all original functionality.
    """
    logging.basicConfig(level=logging.INFO)

    from docling.types.config import ProcessingConfig
    from docling.types.enums import ProcessingMode
    from docling.processor import DocumentProcessor

    # Create configuration the original way
    config = ProcessingConfig(
        mode=ProcessingMode.ENHANCED,
        backend=BackendType.DOCLING_PARSE,
        enable_formulas=True,
        enable_picture_classification=True,
        export_formats=["md", "html", "json"],
        image_mode=ImageRefMode.EMBEDDED
    )

    # Initialize processor
    processor = DocumentProcessor(
        config=config,
        store_in_db=True,
        db_client=MockDbClient(),
        pipeline_key="multi_enrichment"
    )

    # Add hooks
    processor.add_pre_process_hook(my_pre_hook)
    processor.add_post_process_hook(my_post_hook)

    # Process documents
    input_files = [
        "tests/data/1706.03762v7.pdf",
        "tests/data/jakes-resume.pdf"
    ]

    results = processor.batch_process(input_files, output_dir="scratch_universal")
    
    # Calculate statistics
    fails = sum(r["result"].status == ConversionStatus.FAILURE for r in results)
    partials = sum(r["result"].status == ConversionStatus.PARTIAL_SUCCESS for r in results)
    successes = sum(r["result"].status == ConversionStatus.SUCCESS for r in results)

    logger.info(f"Done => successes={successes}, partials={partials}, fails={fails}")

if __name__ == "__main__":
    # Use the new, simplified interface
    main()
    
    # Or use the alternative implementation that's closer to the original
    # main_alternative()