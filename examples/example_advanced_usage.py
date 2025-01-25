#!/usr/bin/env python3
"""
Advanced Usage Example: Multi-Format Document Processor

This example demonstrates processing multiple document types with advanced features:
1. Process multiple file formats (PDF, DOCX, XLSX, XML)
2. Extract and classify figures/charts/diagrams
3. Extract mathematical formulas and tables
4. Generate metadata and analytics
5. Store results in a structured database
6. Export in multiple formats
7. Validate document quality
8. Generate processing statistics
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import shutil
from collections import defaultdict

from src.spire.core import Spire, SpireConfig
from src.spire.processor.hooks import PreProcessHook, PostProcessHook
from src.spire.types.enums import ProcessingMode, BackendType
from docling.datamodel.document import ConversionResult
from docling_core.types.doc import DoclingDocument, PictureItem, TableItem

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class FigureAnalysis:
    """Analysis of figures in a document."""
    total_count: int = 0
    types: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    avg_confidence: float = 0.0
    low_quality_count: int = 0  # figures with poor resolution

@dataclass
class TableAnalysis:
    """Analysis of tables in a document."""
    total_count: int = 0
    total_cells: int = 0
    avg_rows: float = 0.0
    avg_cols: float = 0.0
    complex_tables: int = 0  # tables with merged cells or nested structure

@dataclass
class FormulaAnalysis:
    """Analysis of mathematical formulas."""
    total_count: int = 0
    categories: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    latex_extracted: int = 0

@dataclass
class DocumentMetadata:
    """Rich metadata extracted from processed documents."""
    doc_id: str
    title: str
    date_processed: datetime
    file_type: str
    language: str
    page_count: int
    word_count: int
    file_size: int
    figures: FigureAnalysis = field(default_factory=FigureAnalysis)
    tables: TableAnalysis = field(default_factory=TableAnalysis)
    formulas: FormulaAnalysis = field(default_factory=FormulaAnalysis)
    keywords: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

class AnalyticsDB:
    """Database for storing document analytics and metadata."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.documents: Dict[str, Dict] = {}
        self.metadata: Dict[str, DocumentMetadata] = {}
        self.db_path.mkdir(parents=True, exist_ok=True)

    def insert_document(self, doc_dict: Dict):
        """Store document data."""
        doc_id = doc_dict.get("name", str(len(self.documents)))
        self.documents[doc_id] = doc_dict
        
        # Save to disk
        doc_file = self.db_path / f"{doc_id}.json"
        with open(doc_file, 'w') as f:
            json.dump(doc_dict, f, indent=2)
            
        logger.info(f"Stored document {doc_id}")

    def store_metadata(self, metadata: DocumentMetadata):
        """Store document metadata."""
        self.metadata[metadata.doc_id] = metadata
        
        # Save to disk
        meta_file = self.db_path / "metadata.json"
        with open(meta_file, 'w') as f:
            json.dump(
                {k: v.__dict__ for k, v in self.metadata.items()},
                f,
                indent=2,
                default=str
            )
        
        logger.info(f"Stored metadata for {metadata.doc_id}")

    def get_analytics(self) -> Dict[str, Any]:
        """Generate analytics across all processed documents."""
        analytics = {
            "total_documents": len(self.documents),
            "document_types": defaultdict(int),
            "total_figures": 0,
            "total_tables": 0,
            "total_formulas": 0,
            "figure_types": defaultdict(int),
            "avg_processing_time": 0.0,
            "error_rate": 0.0
        }
        
        if not self.metadata:
            return analytics
            
        for meta in self.metadata.values():
            analytics["document_types"][meta.file_type] += 1
            analytics["total_figures"] += meta.figures.total_count
            analytics["total_tables"] += meta.tables.total_count
            analytics["total_formulas"] += meta.formulas.total_count
            
            for fig_type, count in meta.figures.types.items():
                analytics["figure_types"][fig_type] += count
            
            analytics["avg_processing_time"] += meta.processing_time
            
        analytics["avg_processing_time"] /= len(self.metadata)
        analytics["error_rate"] = sum(
            1 for m in self.metadata.values() if m.errors
        ) / len(self.metadata)
        
        return analytics

def analyze_document(doc: DoclingDocument, conv_result: ConversionResult) -> DocumentMetadata:
    """Extract rich metadata from processed document."""
    try:
        # Basic metadata
        metadata = DocumentMetadata(
            doc_id=str(conv_result.input.file),
            title=doc.name or "Untitled",
            date_processed=datetime.now(),
            file_type=conv_result.input.format.value,
            language="en",  # Could be detected
            page_count=len(doc.pages),
            word_count=len(doc.texts),
            file_size=conv_result.input.file.stat().st_size
        )
        
        # Analyze figures
        for picture in doc.pictures:
            metadata.figures.total_count += 1
            
            # Get classifications
            if picture.annotations:
                for annotation in picture.annotations:
                    if hasattr(annotation, 'predicted_classes'):
                        top_class = max(
                            annotation.predicted_classes,
                            key=lambda x: x.confidence
                        )
                        metadata.figures.types[top_class.class_name] += 1
                        metadata.figures.avg_confidence += top_class.confidence
            
            # Check image quality
            if hasattr(picture, 'image'):
                if picture.image.width < 300 or picture.image.height < 300:
                    metadata.figures.low_quality_count += 1
        
        if metadata.figures.total_count > 0:
            metadata.figures.avg_confidence /= metadata.figures.total_count
        
        # Analyze tables
        for table in doc.tables:
            metadata.tables.total_count += 1
            if hasattr(table, 'table_cells'):
                metadata.tables.total_cells += len(table.table_cells)
                metadata.tables.avg_rows += table.num_rows
                metadata.tables.avg_cols += table.num_cols
                
                # Check for complex tables
                if any(cell.rowspan > 1 or cell.colspan > 1 
                      for cell in table.table_cells):
                    metadata.tables.complex_tables += 1
        
        if metadata.tables.total_count > 0:
            metadata.tables.avg_rows /= metadata.tables.total_count
            metadata.tables.avg_cols /= metadata.tables.total_count
        
        # Analyze formulas
        for text in doc.texts:
            if text.label == "formula":
                metadata.formulas.total_count += 1
                if hasattr(text, 'latex'):
                    metadata.formulas.latex_extracted += 1
        
        return metadata
        
    except Exception as e:
        logger.error(f"Error analyzing document: {e}")
        return DocumentMetadata(
            doc_id=str(conv_result.input.file),
            title="Error",
            date_processed=datetime.now(),
            file_type="unknown",
            language="unknown",
            page_count=0,
            word_count=0,
            file_size=0,
            errors=[str(e)]
        )

def process_documents(
    input_dir: Path,
    output_dir: Path,
    db: AnalyticsDB,
    batch_size: int = 5
) -> bool:
    """
    Process multiple document types with advanced features.
    
    Args:
        input_dir: Directory containing input documents
        output_dir: Directory for processed outputs
        db: Analytics database
        batch_size: Number of documents to process in each batch
    
    Returns:
        bool: True if processing was successful
    """
    try:
        # Set up directories
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure processor
        config = SpireConfig(
            mode="enhanced",
            enable_formulas=True,
            enable_pictures=True,
            output_formats=["md", "html", "json"],
            embed_images=True,
            backend="docling_parse_v2",
            ocr_languages=["en"],
            debug=True
        )
        
        # Initialize processor
        processor = Spire(config=config)
        processor.processor.store_in_db = True
        processor.processor.db_client = db
        
        # Add pre-processing hook
        def validation_hook(path: Path, cfg: Dict) -> None:
            """Validate input files."""
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > 100:  # 100MB limit
                raise ValueError(f"File too large: {size_mb:.1f}MB")
            
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
                
            logger.info(f"Validating {path.name} ({size_mb:.1f}MB)")
        
        # Add post-processing hook
        def analysis_hook(conv_res: ConversionResult, cfg: Dict) -> None:
            """Analyze processed document."""
            if conv_res.document:
                metadata = analyze_document(conv_res.document, conv_res)
                metadata.processing_time = conv_res.timings.get(
                    "total_time", 0.0
                )
                db.store_metadata(metadata)
        
        # Add hooks
        processor.add_pre_hook(validation_hook)
        processor.add_post_hook(analysis_hook)
        
        # Get all documents recursively
        files = []
        extensions = ["*.pdf", "*.docx", "*.xlsx", "*.xml", "*.pptx"]
        for ext in extensions:
            # Use rglob to search recursively through subdirectories
            files.extend(input_dir.rglob(ext))
            
        if not files:
            logger.warning(f"No documents found in {input_dir} with extensions {extensions}")
            # Log the directory contents to help debug
            logger.info("Directory contents:")
            for item in input_dir.rglob("*"):
                logger.info(f"  - {item}")
            return False
        
        # Process in batches
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}")
            
            results = processor.process_batch(
                batch,
                output_dir=output_dir,
                raises_on_error=False
            )
            
            # Log batch results
            successes = sum(1 for r in results 
                          if r["result"].status == "success")
            logger.info(f"Batch completed: {successes}/{len(batch)} successful")
        
        # Generate final analytics
        analytics = db.get_analytics()
        
        # Save analytics
        analytics_file = output_dir / "processing_analytics.json"
        with open(analytics_file, 'w') as f:
            json.dump(analytics, f, indent=2, default=str)
        
        # Log summary
        logger.info("\nProcessing Summary:")
        logger.info(f"Total Documents: {analytics['total_documents']}")
        logger.info("Document Types:")
        for dtype, count in analytics["document_types"].items():
            logger.info(f"  - {dtype}: {count}")
        logger.info(f"Total Figures: {analytics['total_figures']}")
        logger.info(f"Total Tables: {analytics['total_tables']}")
        logger.info(f"Total Formulas: {analytics['total_formulas']}")
        logger.info(f"Average Processing Time: {analytics['avg_processing_time']:.2f}s")
        logger.info(f"Error Rate: {analytics['error_rate']*100:.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        return False

def main():
    """Run the advanced document processing example."""
    # Set up directories - align with download script
    base_dir = Path("sample_documents")  # Updated to match download script's base_dir
    input_dir = base_dir
    output_dir = Path("processed_output")
    db_dir = Path("analytics_db")
    
    if not input_dir.exists():
        logger.error(f"Input directory {input_dir} not found. Please run the download script first.")
        return 1
    
    # Initialize database
    db = AnalyticsDB(db_dir)
    
    try:
        logger.info("Starting document processing...")
        success = process_documents(input_dir, output_dir, db)
        
        if success:
            logger.info(f"\nResults saved to:")
            logger.info(f"- Processed files: {output_dir}")
            logger.info(f"- Analytics database: {db_dir}")
            return 0
        else:
            logger.error("Processing failed")
            return 1
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())
