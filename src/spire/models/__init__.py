"""
Models module for spire library.

This module contains:
- Pydantic models for data validation and serialization
- Enrichment models for document processing
"""

from .picture import (
    PictureDataAnnotation,
    PictureClassificationData,
    PictureDescriptionData,
    PictureMoleculeData,
    PictureMiscData,
    PictureLineChartData,
    PictureBarChartData,
    PictureStackedBarChartData,
    PicturePieChartData,
    PictureScatterChartData,
    Classification,
    PictureDataAnnotationUnion,
)

from .enrichment import (
    FormulaEnrichmentModel,
    PictureClassifierEnrichmentModel,
)

__all__ = [
    # Picture annotation models
    'PictureDataAnnotation',
    'PictureClassificationData',
    'PictureDescriptionData',
    'PictureMoleculeData',
    'PictureMiscData',
    'PictureLineChartData',
    'PictureBarChartData',
    'PictureStackedBarChartData',
    'PicturePieChartData',
    'PictureScatterChartData',
    'Classification',
    'PictureDataAnnotationUnion',
    
    # Enrichment models
    'FormulaEnrichmentModel',
    'PictureClassifierEnrichmentModel',
]