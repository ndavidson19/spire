"""
Simplified processing functions for common use cases.
"""

from pathlib import Path
from typing import List, Optional, Union, Dict, Any

from src.spire.types.config import ProcessingConfig
from src.spire.types.enums import ProcessingMode
from src.spire.processor import DocumentProcessor

def process_document(
    document: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
    mode: Union[str, ProcessingMode] = "standard",
    enable_formulas: bool = False,
    enable_pictures: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Process a single document with minimal configuration.
    
    Example:
        >>> result = process_document("document.pdf", output_dir="output")
        >>> result = process_document(
        ...     "document.pdf",
        ...     mode="enhanced",
        ...     enable_formulas=True
        ... )
    
    Args:
        document: Path to document
        output_dir: Output directory for processed files
        mode: Processing mode
        enable_formulas: Enable formula processing
        enable_pictures: Enable picture classification
        **kwargs: Additional configuration options
        
    Returns:
        Processing results
    """
    # Convert mode string to enum if needed
    if isinstance(mode, str):
        mode = ProcessingMode[mode.upper()]
        
    # Create config
    config = ProcessingConfig.for_mode(mode)
    config.enable_formulas = enable_formulas
    config.enable_picture_classification = enable_pictures
    
    # Apply any additional kwargs to config
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
            
    # Process document
    processor = DocumentProcessor(config=config)
    return processor.process(document, output_dir)

def process_batch(
    documents: List[Union[str, Path]],
    output_dir: Optional[Union[str, Path]] = None,
    mode: Union[str, ProcessingMode] = "standard",
    enable_formulas: bool = False,
    enable_pictures: bool = False,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Process multiple documents with minimal configuration.
    
    Example:
        >>> results = process_batch(
        ...     ["doc1.pdf", "doc2.pdf"],
        ...     output_dir="output",
        ...     mode="enhanced"
        ... )
    
    Args:
        documents: List of document paths
        output_dir: Output directory for processed files
        mode: Processing mode
        enable_formulas: Enable formula processing
        enable_pictures: Enable picture classification
        **kwargs: Additional configuration options
        
    Returns:
        List of processing results
    """
    # Convert mode string to enum if needed
    if isinstance(mode, str):
        mode = ProcessingMode[mode.upper()]
        
    # Create config
    config = ProcessingConfig.for_mode(mode)
    config.enable_formulas = enable_formulas
    config.enable_picture_classification = enable_pictures
    
    # Apply any additional kwargs to config
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
            
    # Process documents
    processor = DocumentProcessor(config=config)
    return processor.batch_process(documents, output_dir)