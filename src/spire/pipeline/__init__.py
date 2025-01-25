"""
Pipeline module for spire document processing.

This module contains:
- Pipeline registry for dynamic pipeline selection
- Base multi-enrichment pipeline
- Specialized pipelines for different processing needs
"""

from .registry import (
    PipelineRegistry,
    pipeline_registry,
)

from .multi_enrichment import (
    MultiEnrichmentPipeline,
    MultiEnrichmentPipelineWithFormulaPictures,
    FormulaOnlyPipeline,
    PictureOnlyPipeline,
)

__all__ = [
    # Registry
    'PipelineRegistry',
    'pipeline_registry',
    
    # Pipeline implementations
    'MultiEnrichmentPipeline',
    'MultiEnrichmentPipelineWithFormulaPictures',
    'FormulaOnlyPipeline',
    'PictureOnlyPipeline',
]