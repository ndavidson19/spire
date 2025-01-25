"""
Enrichment models for processing documents.
"""

import logging
from typing import Iterable, Any, Optional, Union

from PIL.Image import Image

from docling_core.types.doc import (
    DoclingDocument,
    NodeItem,
    PictureItem,
    TextItem,
    DocItemLabel,
    ImageRef,
)
from docling.datamodel.base_models import (
    ConversionStatus,
    InputFormat,
    ItemAndImageEnrichmentElement,
)
from docling.models.base_model import (
    BaseEnrichmentModel,
    BaseItemAndImageEnrichmentModel,
)

from .picture import PictureClassificationData, Classification, create_picture_annotation

logger = logging.getLogger(__name__)

def scale_image(image: Union[Image, ImageRef, Any], scale_factor: float) -> Optional[Union[Image, ImageRef]]:
    """
    Scale an image while handling different image types.
    
    Args:
        image: Image object (PIL Image, ImageRef, etc.)
        scale_factor: Scale factor for resizing
        
    Returns:
        Scaled image or None if scaling fails
    """
    if image is None:
        return None
        
    try:
        if isinstance(image, ImageRef):
            # For ImageRef, we just pass it through since it's handled elsewhere
            return image
            
        elif hasattr(image, 'size') and hasattr(image, 'resize'):
            # Handle PIL Image type
            width, height = image.size
            new_size = (
                int(width * scale_factor),
                int(height * scale_factor)
            )
            return image.resize(new_size)
            
        else:
            logger.debug(f"Unsupported image type for scaling: {type(image)}")
            return image  # Return original if we can't scale it
            
    except Exception as e:
        logger.warning(f"Image scaling failed: {e}")
        return image  # Return original on error

class FormulaEnrichmentModel(BaseItemAndImageEnrichmentModel):
    """
    Model for processing formula items in documents.
    Handles image scaling and formula analysis.
    """
    def __init__(self, enabled: bool = True, images_scale: float = 1.0):
        self.enabled = enabled
        self.images_scale = images_scale

    def is_processable(self, doc: DoclingDocument, element: NodeItem) -> bool:
        """Check if an element can be processed as a formula."""
        return (
            self.enabled 
            and isinstance(element, TextItem) 
            and element.label == DocItemLabel.FORMULA
        )

    def __call__(
        self,
        doc: DoclingDocument,
        element_batch: Iterable[ItemAndImageEnrichmentElement]
    ) -> Iterable[NodeItem]:
        """Process a batch of formula elements."""
        if not self.enabled:
            return

        for enrich_element in element_batch:
            # Handle image scaling if present
            if hasattr(enrich_element, 'image') and enrich_element.image:
                enrich_element.image = scale_image(
                    enrich_element.image,
                    self.images_scale
                )
            
            yield enrich_element.item

class PictureClassifierEnrichmentModel(BaseEnrichmentModel):
    """
    Model for classifying pictures in documents.
    Handles image scaling and classification.
    """
    def __init__(self, enabled: bool = True, images_scale: float = 1.0):
        self.enabled = enabled
        self.images_scale = images_scale

    def is_processable(self, doc: DoclingDocument, element: NodeItem) -> bool:
        """Check if an element can be processed as a picture."""
        return self.enabled and isinstance(element, PictureItem)

    def __call__(
        self, 
        doc: DoclingDocument, 
        element_batch: Iterable[NodeItem]
    ) -> Iterable[NodeItem]:
        """Process a batch of picture elements."""
        if not self.enabled:
            return

        for element in element_batch:
            assert isinstance(element, PictureItem)
            
            # Handle image scaling
            if element.image:
                element.image = scale_image(element.image, self.images_scale)

            # Add classification data using create_picture_annotation
            classification_data = create_picture_annotation(
                "PictureClassificationData",
                provenance="picture_classifier",
                predicted_classes=[
                    Classification(
                        class_name="dummy",
                        confidence=0.42
                    )
                ]
            )
            element.annotations.append(classification_data)
            yield element