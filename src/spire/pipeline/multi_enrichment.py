"""
Multi-enrichment pipeline implementations.

These pipelines can process multiple types of enrichments (formulas, pictures)
simultaneously or separately.
"""

import logging
from typing import List

from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from src.spire.models import FormulaEnrichmentModel, PictureClassifierEnrichmentModel

logger = logging.getLogger(__name__)

class MultiEnrichmentPipeline(StandardPdfPipeline):
    """
    Base class for pipelines that can handle multiple enrichment types.
    Inherits from StandardPdfPipeline but adds support for multiple
    enrichment models.
    """
    def __init__(
        self, 
        pipeline_options: PdfPipelineOptions, 
        do_formula: bool = False,
        do_pictures: bool = False
    ):
        super().__init__(pipeline_options)
        self.enrichment_pipe: List[Any] = []

        # Add formula enrichment if enabled
        if do_formula:
            logger.info("Adding formula enrichment to pipeline")
            self.enrichment_pipe.append(
                FormulaEnrichmentModel(
                    enabled=True, 
                    images_scale=pipeline_options.images_scale
                )
            )

        # Add picture enrichment if enabled
        if do_pictures:
            logger.info("Adding picture enrichment to pipeline")
            self.enrichment_pipe.append(
                PictureClassifierEnrichmentModel(
                    enabled=True, 
                    images_scale=pipeline_options.images_scale
                )
            )

        # Keep backend in memory if any enrichments are active
        if do_formula or do_pictures:
            self.keep_backend = True

    @classmethod
    def get_default_options(cls) -> PdfPipelineOptions:
        """Get default pipeline options."""
        return PdfPipelineOptions()


class MultiEnrichmentPipelineWithFormulaPictures(MultiEnrichmentPipeline):
    """Pipeline that enables both formula and picture processing."""
    def __init__(self, pipeline_options: PdfPipelineOptions):
        super().__init__(
            pipeline_options,
            do_formula=True,
            do_pictures=True
        )
        logger.info("Initialized pipeline with both formula and picture processing")


class FormulaOnlyPipeline(MultiEnrichmentPipeline):
    """Pipeline that enables only formula processing."""
    def __init__(self, pipeline_options: PdfPipelineOptions):
        super().__init__(
            pipeline_options,
            do_formula=True,
            do_pictures=False
        )
        logger.info("Initialized pipeline with formula processing only")


class PictureOnlyPipeline(MultiEnrichmentPipeline):
    """Pipeline that enables only picture processing."""
    def __init__(self, pipeline_options: PdfPipelineOptions):
        super().__init__(
            pipeline_options,
            do_formula=False,
            do_pictures=True
        )
        logger.info("Initialized pipeline with picture processing only")


# Register all pipelines
from .registry import pipeline_registry

pipeline_registry.register("multi_enrichment", MultiEnrichmentPipelineWithFormulaPictures)
pipeline_registry.register("formula_only", FormulaOnlyPipeline)
pipeline_registry.register("picture_only", PictureOnlyPipeline)