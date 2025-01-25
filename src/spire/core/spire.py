"""
Main spire class providing high-level interface to document processing.
"""

import logging
from pathlib import Path
from typing import List, Optional, Union, Dict, Any

from src.spire.types.config import ProcessingConfig
from src.spire.types.enums import ProcessingMode
from src.spire.processor import DocumentProcessor
from src.spire.processor.hooks import PreProcessHook, PostProcessHook
from .config import SpireConfig

logger = logging.getLogger(__name__)

class Spire:
    """
    Main interface to spire document processing functionality.
    
    Example:
        >>> from docling.core import Docling
        >>> doc = Spire()
        >>> result = doc.process("document.pdf")
        >>> # With custom configuration
        >>> doc = Spire(mode="enhanced", enable_formulas=True)
        >>> result = doc.process("document.pdf", output_dir="output")
    """

    def __init__(
        self,
        config: Optional[Union[ProcessingConfig, SpireConfig]] = None,
        mode: Union[str, ProcessingMode] = ProcessingMode.STANDARD,
        enable_formulas: bool = False,
        enable_pictures: bool = False,
        **kwargs
    ):
        """
        Initialize Spire processor.
        
        Args:
            config: Full configuration object
            mode: Processing mode ("simple", "standard", "enhanced", "maximum")
            enable_formulas: Enable formula processing
            enable_pictures: Enable picture classification
            **kwargs: Additional configuration options
        """
        # Handle different config types
        if isinstance(config, SpireConfig):
            self.config = config.to_processing_config()
        elif isinstance(config, ProcessingConfig):
            self.config = config
        else:
            # Create from parameters
            if isinstance(mode, str):
                mode = ProcessingMode[mode.upper()]
            self.config = ProcessingConfig.for_mode(mode)
            self.config.enable_formulas = enable_formulas
            self.config.enable_picture_classification = enable_pictures
            # Apply any additional kwargs to config
            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)

        # Initialize processor
        self.processor = DocumentProcessor(config=self.config)

    def process(
        self,
        document: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a single document.
        
        Args:
            document: Path to document
            output_dir: Output directory for processed files
            **kwargs: Additional processing options
            
        Returns:
            Processing results
        """
        return self.processor.process(document, output_dir, **kwargs)

    def process_batch(
        self,
        documents: List[Union[str, Path]],
        output_dir: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Process multiple documents.
        
        Args:
            documents: List of document paths
            output_dir: Output directory for processed files
            **kwargs: Additional processing options
            
        Returns:
            List of processing results
        """
        return self.processor.batch_process(documents, output_dir, **kwargs)

    def add_pre_hook(self, hook: PreProcessHook) -> None:
        """Add a pre-processing hook."""
        self.processor.add_pre_process_hook(hook)

    def add_post_hook(self, hook: PostProcessHook) -> None:
        """Add a post-processing hook."""
        self.processor.add_post_process_hook(hook)

    @property
    def mode(self) -> ProcessingMode:
        """Get current processing mode."""
        return self.config.mode

    @mode.setter
    def mode(self, value: Union[str, ProcessingMode]) -> None:
        """Set processing mode."""
        if isinstance(value, str):
            value = ProcessingMode[value.upper()]
        self.config = ProcessingConfig.for_mode(value)

    def enable_feature(self, feature: str, enabled: bool = True) -> None:
        """
        Enable/disable specific features.
        
        Args:
            feature: Feature name ("formulas", "pictures", etc.)
            enabled: Whether to enable or disable
        """
        if feature == "formulas":
            self.config.enable_formulas = enabled
        elif feature in ["pictures", "picture_classification"]:
            self.config.enable_picture_classification = enabled
        else:
            logger.warning(f"Unknown feature: {feature}")