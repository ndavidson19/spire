#!/usr/bin/env python3
from pathlib import Path
import time
import argparse
from typing import List, Dict, Any
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import pandas as pd
import base64
from PIL import Image
import io

from src.spire.core.config import (
    ProcessingConfig,
    ProcessingMode,
    BackendType,
    OcrEngine,
    AccelerationType,
    OcrConfig,
    TableConfig
)
from src.spire.core.processor import DocumentProcessor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_custom_config(
    mode: ProcessingMode,
    use_gpu: bool = False,
    languages: List[str] = ["eng"],
    export_formats: List[str] = None,
    extract_tables: bool = True,
    extract_images: bool = True
) -> ProcessingConfig:
    """Create a custom processing configuration"""
    if export_formats is None:
        export_formats = ["md", "txt", "json"]

    return ProcessingConfig(
        mode=mode,
        acceleration=AccelerationType.CUDA if use_gpu else AccelerationType.CPU,
        backend=BackendType.PYPDFIUM if mode == ProcessingMode.SIMPLE else BackendType.DOCLING_PARSE,
        ocr=OcrConfig(
            engine=OcrEngine.TESSERACT_CLI,
            languages=languages,
            force_full_page=mode == ProcessingMode.MAXIMUM,
            use_gpu=use_gpu,
            confidence_threshold=0.5
        ),
        tables=TableConfig(
            enabled=extract_tables and mode in [ProcessingMode.ENHANCED, ProcessingMode.MAXIMUM],
            cell_matching=mode == ProcessingMode.MAXIMUM,
            detect_headers=True,
            min_confidence=0.7
        ),
        extract_figures=extract_images and mode in [ProcessingMode.ENHANCED, ProcessingMode.MAXIMUM],
        extract_formulas=mode == ProcessingMode.MAXIMUM,
        export_formats=export_formats,
        image_scale=2.0 if extract_images else 1.0
    )

def save_extracted_tables(
    tables: List[Any],
    output_dir: Path,
    base_name: str
):
    """Save extracted tables in multiple formats"""
    tables_dir = output_dir / "tables"
    tables_dir.mkdir(exist_ok=True)
    
    for idx, table in enumerate(tables):
        logger.debug(f"Processing table {idx+1} for {base_name}")
        
        # Inspect the TableItem object
        logger.debug(f"Table {idx+1} attributes: {dir(table)}")
        
        # Check if table has data
        if not hasattr(table, 'rows') or not table.rows:
            logger.warning(f"Table {idx+1} in {base_name} is empty.")
            continue
        
        # Convert TableItem to DataFrame
        if hasattr(table, 'to_dataframe'):
            df = table.to_dataframe()
            logger.debug(f"Converted table {idx+1} using to_dataframe method.")
        else:
            # Manual conversion assuming TableItem has 'headers' and 'rows'
            headers = getattr(table, 'headers', None)
            rows = getattr(table, 'rows', [])
            if headers:
                df = pd.DataFrame(rows, columns=headers)
                logger.debug(f"Converted table {idx+1} with headers: {headers}")
            else:
                df = pd.DataFrame(rows)
                logger.debug(f"Converted table {idx+1} without headers.")
        
        # Check if DataFrame is empty
        if df.empty:
            logger.warning(f"Converted DataFrame for table {idx+1} in {base_name} is empty.")
            continue
        
        # Save as CSV
        csv_path = tables_dir / f"{base_name}_table_{idx+1}.csv"
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved table {idx+1} as CSV to {csv_path}")
        
        # Save as Excel
        xlsx_path = tables_dir / f"{base_name}_table_{idx+1}.xlsx"
        df.to_excel(xlsx_path, index=False)
        logger.info(f"Saved table {idx+1} as Excel to {xlsx_path}")
        
        # Save table metadata
        metadata = {
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': list(df.columns),
            'has_headers': bool(headers)
        }
        meta_path = tables_dir / f"{base_name}_table_{idx+1}_metadata.json"
        with meta_path.open('w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Saved metadata for table {idx+1} to {meta_path}")



def save_extracted_images(
    images: List[Dict[str, Any]],
    output_dir: Path,
    base_name: str
):
    """Save extracted images with metadata"""
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    image_metadata = []
    for idx, img_data in enumerate(images):
        logger.debug(f"Processing image {idx+1} for {base_name}")
        
        # Save image
        img_path = images_dir / f"{base_name}_image_{idx+1}.png"
        
        # Convert base64 to image and save
        if isinstance(img_data.get('data'), str):
            try:
                img_bytes = base64.b64decode(img_data['data'])
                logger.debug(f"Decoded base64 data for image {idx+1}")
            except base64.binascii.Error as e:
                logger.error(f"Base64 decoding failed for image {idx+1}: {e}")
                continue
        else:
            img_bytes = img_data.get('data')
            
        if img_bytes:
            try:
                img = Image.open(io.BytesIO(img_bytes))
                img.save(img_path)
                logger.info(f"Saved image {idx+1} to {img_path}")
                
                # Collect metadata
                metadata = {
                    'filename': img_path.name,
                    'page': img_data.get('page', 0),
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'location': img_data.get('location', {}),
                    'caption': img_data.get('caption', '')
                }
                image_metadata.append(metadata)
            except Exception as e:
                logger.error(f"Failed to save image {idx+1}: {e}")
        else:
            logger.warning(f"No image data found for image {idx+1}")
    
    if image_metadata:
        # Save metadata
        metadata_path = images_dir / f"{base_name}_image_metadata.json"
        try:
            with metadata_path.open('w') as f:
                json.dump(image_metadata, f, indent=2)
            logger.info(f"Saved image metadata to {metadata_path}")
        except Exception as e:
            logger.error(f"Failed to save image metadata: {e}")



def process_file(
    file_path: Path,
    config: ProcessingConfig,
    output_dir: Path
) -> Dict[str, Any]:
    """Process a single file with detailed metrics and content extraction"""
    logger.info(f"Processing {file_path.name} with {config.mode.name} mode")
    start_time = time.time()
    
    try:
        processor = DocumentProcessor(config)
        result = processor.process(file_path, output_dir)
        doc = result["document"]
        
        # Log the number of images found
        if hasattr(doc, 'images') and isinstance(doc.images, list):
            logger.info(f"Number of images extracted: {len(doc.images)}")
            for idx, image in enumerate(doc.images, start=1):
                logger.debug(f"Image {idx} contents: {image}")
        else:
            logger.warning(f"No images found in {file_path.name}")
        
        # Extract and save tables if available
        if hasattr(doc, 'tables') and isinstance(doc.tables, list) and doc.tables:
            save_extracted_tables(
                doc.tables,
                output_dir,
                file_path.stem
            )
        
        # Extract and save images if available
        if hasattr(doc, 'images') and isinstance(doc.images, list) and doc.images:
            save_extracted_images(
                doc.images,
                output_dir,
                file_path.stem
            )
        
        processing_time = time.time() - start_time
        
        # Collect metrics
        metrics = {
            "file_name": file_path.name,
            "processing_time": processing_time,
            "mode": config.mode.name,
            "status": "success",
            "content_stats": {
                "tables": len(doc.tables) if hasattr(doc, 'tables') and isinstance(doc.tables, list) else 0,
                "images": len(doc.images) if hasattr(doc, 'images') and isinstance(doc.images, list) else 0,
                "figures": len(doc.figures) if hasattr(doc, 'figures') and isinstance(doc.figures, list) else 0,
                "formulas": len(doc.formulas) if hasattr(doc, 'formulas') and isinstance(doc.formulas, list) else 0
            },
            "output_files": [
                str(path) for path in result.values() 
                if isinstance(path, Path)
            ]
        }
        
        logger.info(f"Successfully processed {file_path.name} in {processing_time:.2f} seconds")
        return metrics
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Error processing {file_path.name}: {str(e)}")
        return {
            "file_name": file_path.name,
            "processing_time": processing_time,
            "mode": config.mode.name,
            "status": "error",
            "error": str(e)
        }

def batch_process(
    input_files: List[Path],
    config: ProcessingConfig,
    output_dir: Path,
    max_workers: int = 4
) -> List[Dict[str, Any]]:
    """Process multiple files in parallel"""
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(
                process_file, 
                file_path, 
                config, 
                output_dir / file_path.stem
            ): file_path 
            for file_path in input_files
        }
        
        for future in as_completed(future_to_file):
            result = future.result()
            results.append(result)
    
    return results

def save_processing_report(
    results: List[Dict[str, Any]],
    output_dir: Path
):
    """Save processing results as a JSON report"""
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_files": len(results),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "error"),
        "total_processing_time": sum(r["processing_time"] for r in results),
        "content_summary": {
            "total_tables": sum(r.get("content_stats", {}).get("tables", 0) for r in results if r["status"] == "success"),
            "total_images": sum(r.get("content_stats", {}).get("images", 0) for r in results if r["status"] == "success"),
            "total_figures": sum(r.get("content_stats", {}).get("figures", 0) for r in results if r["status"] == "success"),
            "total_formulas": sum(r.get("content_stats", {}).get("formulas", 0) for r in results if r["status"] == "success")
        },
        "results": results
    }
    
    report_path = output_dir / "processing_report.json"
    with report_path.open("w") as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Processing report saved to {report_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Advanced document processing script with content extraction"
    )
    parser.add_argument(
        "input_path",
        type=str,
        help="Path to input file or directory"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directory to store output files (default: ./output)"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=[mode.name.lower() for mode in ProcessingMode],
        default="standard",
        help="Processing mode to use"
    )
    parser.add_argument(
        "--use-gpu",
        action="store_true",
        help="Enable GPU acceleration if available"
    )
    parser.add_argument(
        "--languages",
        type=str,
        nargs="+",
        default=["eng"],
        help="OCR languages (e.g., eng fra deu)"
    )
    parser.add_argument(
        "--formats",
        type=str,
        nargs="+",
        default=["md", "txt", "json"],
        help="Output formats (e.g., md txt json yaml html doctags)"
    )
    parser.add_argument(
        "--extract-tables",
        action="store_true",
        default=True,
        help="Extract tables from documents"
    )
    parser.add_argument(
        "--extract-images",
        action="store_true",
        default=True,
        help="Extract images from documents"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum number of parallel processing workers"
    )
    
    args = parser.parse_args()
    
    # Setup paths
    input_path = Path(args.input_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create processing configuration
    config = create_custom_config(
        mode=ProcessingMode[args.mode.upper()],
        use_gpu=args.use_gpu,
        languages=args.languages,
        export_formats=args.formats,
        extract_tables=args.extract_tables,
        extract_images=args.extract_images
    )
    
    # Collect input files
    if input_path.is_file():
        input_files = [input_path]
    else:
        input_files = list(input_path.glob("**/*.pdf"))
        if not input_files:
            logger.error(f"No PDF files found in {input_path}")
            return
    
    logger.info(f"Found {len(input_files)} files to process")
    
    # Process files
    results = batch_process(
        input_files,
        config,
        output_dir,
        max_workers=args.max_workers
    )
    
    # Save processing report
    save_processing_report(results, output_dir)

if __name__ == "__main__":
    main()