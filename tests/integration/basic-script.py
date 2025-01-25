#!/usr/bin/env python3
from pathlib import Path
import time
import argparse
from typing import List, Dict, Any

from src.spire.core.config import (
    ProcessingConfig,
    ProcessingMode,
    BackendType,
    OcrEngine,
    AccelerationType
)
from src.spire.core.processor import DocumentProcessor

def process_with_mode(
    file_path: Path,
    mode: ProcessingMode,
    output_dir: Path
) -> Dict[str, Any]:
    """Process a single file with the specified mode"""
    print(f"\nProcessing with {mode.name} mode...")
    processor = DocumentProcessor.for_mode(mode)
    
    start_time = time.time()
    result = processor.process(file_path, output_dir)
    processing_time = time.time() - start_time
    
    print(f"Processing completed in {processing_time:.2f} seconds")
    print("Generated files:")
    for key, path in result.items():
        if isinstance(path, Path):
            print(f"- {path.name}")
    
    return result

def main():
    # Get valid mode choices from the enum
    valid_modes = [mode.name.lower() for mode in ProcessingMode]
    
    parser = argparse.ArgumentParser(description="Test document processing capabilities")
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the PDF file to process"
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
        choices=valid_modes,
        default="standard",
        help=f"Processing mode to use (default: standard). Valid modes: {', '.join(valid_modes)}"
    )
    parser.add_argument(
        "--all-modes",
        action="store_true",
        help="Test processing with all available modes"
    )
    
    args = parser.parse_args()
    
    # Setup paths
    input_path = Path(args.input_file)
    output_dir = Path(args.output_dir)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Processing file: {input_path}")
    print(f"Output directory: {output_dir}")
    
    # Process with selected mode(s)
    if args.all_modes:
        for mode in ProcessingMode:
            mode_output_dir = output_dir / mode.name.lower()
            mode_output_dir.mkdir(parents=True, exist_ok=True)
            process_with_mode(input_path, mode, mode_output_dir)
    else:
        # Convert the lowercase input to the uppercase enum value
        mode = ProcessingMode[args.mode.upper()]
        process_with_mode(input_path, mode, output_dir)

if __name__ == "__main__":
    main()