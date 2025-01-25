"""
Pipeline registry for managing and accessing different pipeline implementations.
"""

import logging
from typing import Any, Dict, Type

from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline

logger = logging.getLogger(__name__)

class PipelineRegistry:
    """
    A registry to map user-chosen keys to pipeline classes.
    Allows for dynamic pipeline selection and extension.
    """
    def __init__(self):
        self._registry: Dict[str, Type[Any]] = {}

    def register(self, key: str, pipeline_cls: Type[Any]) -> None:
        """
        Register a new pipeline class with the given key.
        
        Args:
            key: Unique identifier for the pipeline
            pipeline_cls: The pipeline class to register
        """
        logger.debug(f"Registering pipeline '{key}': {pipeline_cls}")
        self._registry[key] = pipeline_cls

    def get(self, key: str, default: Type[Any] = StandardPdfPipeline) -> Type[Any]:
        """
        Get a pipeline class by key.
        
        Args:
            key: The pipeline identifier
            default: Default pipeline class if key not found
            
        Returns:
            The pipeline class
        """
        pipeline_cls = self._registry.get(key, default)
        logger.debug(f"Retrieved pipeline for key '{key}': {pipeline_cls}")
        return pipeline_cls

    def list_pipelines(self) -> Dict[str, Type[Any]]:
        """Get a dictionary of all registered pipelines."""
        return dict(self._registry)

    def __contains__(self, key: str) -> bool:
        """Check if a pipeline key exists."""
        return key in self._registry

# Create global registry instance
pipeline_registry = PipelineRegistry()