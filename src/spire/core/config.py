"""
Simplified configuration interface for spire.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union

from src.spire.types.config import ProcessingConfig
from src.spire.types.enums import ProcessingMode, BackendType, OcrEngine

@dataclass
class SpireConfig:
    """
    Simplified configuration interface for spire.
    Provides a more user-friendly way to configure the library.
    
    Example:
        >>> config = SpireConfig(
        ...     mode="enhanced",
        ...     enable_formulas=True,
        ...     enable_pictures=True,
        ...     output_formats=["md", "html"]
        ... )
        >>> doc = Spire(config=config)
    """
    
    # Basic settings
    mode: Union[str, ProcessingMode] = "standard"
    enable_formulas: bool = False
    enable_pictures: bool = False
    
    # Output settings
    output_formats: List[str] = field(default_factory=lambda: ["md"])
    embed_images: bool = False
    
    # OCR settings
    enable_ocr: bool = True
    ocr_languages: List[str] = field(default_factory=lambda: ["en"])
    
    # Advanced settings
    debug: bool = False
    num_threads: int = 8
    backend: Optional[str] = None

    def to_processing_config(self) -> ProcessingConfig:
        """Convert to internal ProcessingConfig."""
        # Convert mode string to enum if needed
        if isinstance(self.mode, str):
            mode = ProcessingMode[self.mode.upper()]
        else:
            mode = self.mode

        # Start with mode-based config
        config = ProcessingConfig.for_mode(mode)
        
        # Apply our settings
        config.enable_formulas = self.enable_formulas
        config.enable_picture_classification = self.enable_pictures
        config.export_formats = self.output_formats
        config.image_mode = "embedded" if self.embed_images else "referenced"
        config.num_threads = self.num_threads
        config.debug_mode = self.debug
        
        # OCR settings
        if not self.enable_ocr:
            config.ocr.engine = OcrEngine.NONE
        else:
            config.ocr.languages = self.ocr_languages
            
        # Backend if specified
        if self.backend:
            config.backend = BackendType[self.backend.upper()]
            
        return config

    @classmethod
    def simple(cls) -> 'DoclingConfig':
        """Create simple configuration."""
        return cls(mode="simple", enable_ocr=False)

    @classmethod
    def standard(cls) -> 'DoclingConfig':
        """Create standard configuration."""
        return cls(mode="standard")

    @classmethod
    def enhanced(cls) -> 'DoclingConfig':
        """Create enhanced configuration with all features."""
        return cls(
            mode="enhanced",
            enable_formulas=True,
            enable_pictures=True,
            output_formats=["md", "html", "json"]
        )