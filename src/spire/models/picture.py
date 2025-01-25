"""
Pydantic models for picture-related data annotations.
"""

from typing import List, Dict, Literal, Union
from typing_extensions import Annotated
from pydantic import BaseModel, ConfigDict, Field, computed_field

class PictureDataAnnotation(BaseModel):
    """Base class for all picture-related annotations."""
    type: str

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        from_attributes=True,
        strict=True,
        validate_assignment=True
    )

    def model_dump(self, **kwargs):
        """Custom serialization to ensure type field is included."""
        data = super().model_dump(**kwargs)
        data["type"] = self.type
        return data

class Classification(BaseModel):
    """Classification result with confidence score."""
    class_name: str
    confidence: float

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True
    )

class PictureClassificationData(PictureDataAnnotation):
    """Picture classification results."""
    type: Literal["PictureClassificationData"] = "PictureClassificationData"
    provenance: str
    predicted_classes: List[Classification]

    @computed_field
    def predictions(self) -> List[tuple[str, float]]:
        """Get predictions as tuples for compatibility."""
        return [(c.class_name, c.confidence) for c in self.predicted_classes]

class PictureDescriptionData(PictureDataAnnotation):
    """Natural language description of a picture."""
    type: Literal["PictureDescriptionData"] = "PictureDescriptionData"
    provenance: str
    description: str

class PictureMoleculeData(PictureDataAnnotation):
    """Molecular structure data extracted from a picture."""
    type: Literal["PictureMoleculeData"] = "PictureMoleculeData"
    provenance: str
    molecule_structure: str

class PictureMiscData(PictureDataAnnotation):
    """Miscellaneous picture data."""
    type: Literal["PictureMiscData"] = "PictureMiscData"
    provenance: str
    misc_info: str

class ChartData(BaseModel):
    """Base class for chart data."""
    values: Dict[str, float]
    labels: List[str]

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True
    )

class PictureChartData(PictureDataAnnotation):
    """Base class for chart data annotations."""
    provenance: str
    data: ChartData

class PictureLineChartData(PictureChartData):
    """Data extracted from a line chart."""
    type: Literal["PictureLineChartData"] = "PictureLineChartData"

class PictureBarChartData(PictureChartData):
    """Data extracted from a bar chart."""
    type: Literal["PictureBarChartData"] = "PictureBarChartData"

class PictureStackedBarChartData(PictureChartData):
    """Data extracted from a stacked bar chart."""
    type: Literal["PictureStackedBarChartData"] = "PictureStackedBarChartData"

class PicturePieChartData(PictureChartData):
    """Data extracted from a pie chart."""
    type: Literal["PicturePieChartData"] = "PicturePieChartData"

class PictureScatterChartData(PictureChartData):
    """Data extracted from a scatter plot."""
    type: Literal["PictureScatterChartData"] = "PictureScatterChartData"

# Define a discriminated union type for all picture data annotations
PictureDataAnnotationUnion = Annotated[
    Union[
        PictureClassificationData,
        PictureDescriptionData,
        PictureMoleculeData,
        PictureMiscData,
        PictureLineChartData,
        PictureBarChartData,
        PictureStackedBarChartData,
        PicturePieChartData,
        PictureScatterChartData
    ],
    Field(discriminator='type')
]

def create_picture_annotation(
    annotation_type: str,
    **kwargs
) -> PictureDataAnnotation:
    """
    Factory function to create picture annotations.
    
    Args:
        annotation_type: Type of annotation to create
        **kwargs: Additional annotation data
        
    Returns:
        Created annotation instance
    """
    annotation_classes = {
        "PictureClassificationData": PictureClassificationData,
        "PictureDescriptionData": PictureDescriptionData,
        "PictureMoleculeData": PictureMoleculeData,
        "PictureMiscData": PictureMiscData,
        "PictureLineChartData": PictureLineChartData,
        "PictureBarChartData": PictureBarChartData,
        "PictureStackedBarChartData": PictureStackedBarChartData,
        "PicturePieChartData": PicturePieChartData,
        "PictureScatterChartData": PictureScatterChartData,
    }
    
    cls = annotation_classes.get(annotation_type)
    if not cls:
        raise ValueError(f"Unknown annotation type: {annotation_type}")
    
    return cls(type=annotation_type, **kwargs)

def create_classification_data(
    provenance: str,
    predictions: List[tuple[str, float]]
) -> PictureClassificationData:
    """
    Create a PictureClassificationData instance from predictions.
    
    Args:
        provenance: Source of the predictions
        predictions: List of (class_name, confidence) tuples
    
    Returns:
        PictureClassificationData instance
    """
    return PictureClassificationData(
        type="PictureClassificationData",
        provenance=provenance,
        predicted_classes=[
            Classification(class_name=name, confidence=conf)
            for name, conf in predictions
        ]
    )