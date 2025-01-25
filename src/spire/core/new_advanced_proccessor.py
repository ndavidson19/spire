"""
universal_processor.py
A single, fully implemented example of a universal docling-based processor with:

- Multiple pipeline toggles (formula, picture classification)
- A pipeline registry for custom pipelines
- A multi-enrichment pipeline that can do multiple enrichments
- Pre/post hooking
- DB storage
- Multi-format exporting with optional embedded images
"""

import json
import logging
import time
import shutil
from pathlib import Path
from typing import (
    List,
    Union,
    Optional,
    Callable,
    Any,
    Iterable,
    Dict,
)
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Literal, Annotated

import yaml
from pydantic import BaseModel, ValidationError, Field

# Docling imports
from docling_core.types.doc import (
    DoclingDocument,
    NodeItem,
    PictureItem,
    TextItem,
    DocItemLabel,
    ImageRefMode,  # For embedding or referencing images in MD/HTML
)
from docling.datamodel.base_models import (
    ConversionStatus,
    InputFormat,
    ItemAndImageEnrichmentElement,
)
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    AcceleratorDevice,
)
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
    WordFormatOption
)
from docling.models.base_model import (
    BaseEnrichmentModel,
    BaseItemAndImageEnrichmentModel,
)
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.backend.docling_parse_backend import DoclingParseDocumentBackend

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

###############################################################################
# Enums and Data Classes
###############################################################################

class BackendType(Enum):
    """Available PDF processing backends."""
    PYPDFIUM = "pypdfium"
    DOCLING_PARSE = "docling_parse"

class OcrEngine(Enum):
    """Available OCR engines."""
    NONE = "none"
    EASYOCR = "easyocr"
    TESSERACT = "tesseract"
    TESSERACT_CLI = "tesseract_cli"
    MAC = "mac"  
    RAPID = "rapid"

    @classmethod
    def get_default(cls) -> 'OcrEngine':
        """Select a default OCR engine if available."""
        try:
            import easyocr  # type: ignore
            return cls.EASYOCR
        except ImportError:
            pass
        if shutil.which("tesseract"):
            return cls.TESSERACT_CLI
        logger.warning("No OCR engines available; defaulting to NONE.")
        return cls.NONE

class ProcessingMode(Enum):
    """High-level docling modes."""
    SIMPLE = auto()
    STANDARD = auto()
    ENHANCED = auto()
    MAXIMUM = auto()

class AccelerationType(Enum):
    """Hardware acceleration options."""
    CPU = AcceleratorDevice.CPU
    CUDA = AcceleratorDevice.CUDA
    MPS = AcceleratorDevice.MPS
    AUTO = AcceleratorDevice.AUTO

@dataclass
class OcrConfig:
    engine: OcrEngine = field(default_factory=OcrEngine.get_default)
    languages: List[str] = field(default_factory=lambda: ["en"])
    force_full_page: bool = False
    use_gpu: bool = True
    confidence_threshold: float = 0.5

@dataclass
class TableConfig:
    enabled: bool = True
    cell_matching: bool = True
    detect_headers: bool = True
    min_confidence: float = 0.7

###############################################################################
# The main ProcessingConfig
###############################################################################

@dataclass
class ProcessingConfig:
    """
    The unified configuration for docling usage, including advanced toggles
    like 'enable_formulas' or 'enable_picture_classification'.
    """

    # High-level docling settings
    mode: ProcessingMode = ProcessingMode.STANDARD
    backend: BackendType = BackendType.PYPDFIUM

    # Performance
    acceleration: AccelerationType = AccelerationType.AUTO
    num_threads: int = 8

    # OCR & Tables
    ocr: OcrConfig = field(default_factory=OcrConfig)
    tables: TableConfig = field(default_factory=TableConfig)

    # Image settings
    image_scale: float = 2.0
    extract_figures: bool = True
    extract_formulas: bool = False

    # Debug
    debug_mode: bool = False
    save_intermediates: bool = False

    # Export
    export_formats: List[str] = field(default_factory=lambda: ["md"])
    image_mode: ImageRefMode = ImageRefMode.REFERENCED  # or EMBEDDED

    # Advanced toggles
    enable_formulas: bool = False
    enable_picture_classification: bool = False
    # Additional toggles can be added easily

    def to_pipeline_options(self) -> PdfPipelineOptions:
        """Convert to docling's PdfPipelineOptions."""
        pipe_opts = PdfPipelineOptions()

        # Accelerator
        pipe_opts.accelerator_options.num_threads = self.num_threads
        pipe_opts.accelerator_options.device = self.acceleration.value

        # Image handling
        if self.extract_figures or self.extract_formulas:
            pipe_opts.images_scale = self.image_scale
            pipe_opts.generate_page_images = True
            pipe_opts.generate_picture_images = True

        # OCR
        pipe_opts.do_ocr = (self.ocr.engine != OcrEngine.NONE)
        if pipe_opts.do_ocr:
            try:
                if self.ocr.engine == OcrEngine.EASYOCR:
                    from docling.models.easyocr_model import EasyOcrOptions
                    pipe_opts.ocr_options = EasyOcrOptions(
                        force_full_page_ocr=self.ocr.force_full_page,
                        lang=self.ocr.languages,
                        use_gpu=self.ocr.use_gpu
                    )
                elif self.ocr.engine == OcrEngine.TESSERACT_CLI:
                    from docling.models.tesseract_ocr_cli_model import TesseractCliOcrOptions
                    pipe_opts.ocr_options = TesseractCliOcrOptions(
                        force_full_page_ocr=self.ocr.force_full_page
                    )
                else:
                    logger.warning(f"Unsupported OCR engine {self.ocr.engine}; disabling OCR.")
                    pipe_opts.do_ocr = False
            except ImportError as e:
                logger.warning(f"OCR import failed: {e}")
                pipe_opts.do_ocr = False

        # Table extraction
        pipe_opts.do_table_structure = self.tables.enabled
        if self.tables.enabled:
            pipe_opts.table_structure_options.do_cell_matching = self.tables.cell_matching

        # Debug
        if self.debug_mode:
            from docling.datamodel.settings import settings
            settings.debug.profile_pipeline_timings = True
            settings.debug.visualize_layout = self.save_intermediates
            settings.debug.visualize_ocr = self.save_intermediates
            settings.debug.visualize_tables = self.save_intermediates

        return pipe_opts

    @classmethod
    def for_mode(cls, mode: ProcessingMode) -> "ProcessingConfig":
        """Convenience to build a config preset for a given mode."""
        if mode == ProcessingMode.SIMPLE:
            return cls(
                mode=mode,
                backend=BackendType.PYPDFIUM,
                ocr=OcrConfig(engine=OcrEngine.NONE),
                tables=TableConfig(enabled=False),
                extract_figures=False,
                export_formats=["md", "txt"]
            )
        elif mode == ProcessingMode.STANDARD:
            return cls(
                mode=mode,
                backend=BackendType.DOCLING_PARSE,
                export_formats=["md", "json"]
            )
        elif mode == ProcessingMode.ENHANCED:
            return cls(
                mode=mode,
                backend=BackendType.DOCLING_PARSE,
                tables=TableConfig(enabled=True),
                extract_figures=True,
                export_formats=["md", "json", "txt"]
            )
        elif mode == ProcessingMode.MAXIMUM:
            return cls(
                mode=mode,
                backend=BackendType.DOCLING_PARSE,
                ocr=OcrConfig(force_full_page=True),
                tables=TableConfig(enabled=True, cell_matching=True),
                extract_figures=True,
                extract_formulas=True,
                export_formats=["md", "json", "yaml", "doctags"]
            )
        return cls(mode=mode)

###############################################################################
# Define Necessary Pydantic Data Classes for Annotations
###############################################################################

class PictureDataAnnotation(BaseModel):
    type: str  # Discriminator

    class Config:
        extra = 'forbid'
        orm_mode = True
        # Pydantic v2 uses model_config instead of Config
        # model_config = ConfigDict(discriminator='type')

class Classification(BaseModel):
    class_name: str
    confidence: float

    class Config:
        extra = 'forbid'

class PictureClassificationData(PictureDataAnnotation):
    type: Literal["PictureClassificationData"] = "PictureClassificationData"  # Discriminator value
    provenance: str
    predicted_classes: List[Classification]

    class Config:
        extra = 'forbid'

class PictureDescriptionData(PictureDataAnnotation):
    type: Literal["PictureDescriptionData"] = "PictureDescriptionData"  # Discriminator value
    provenance: str
    description: str

    class Config:
        extra = 'forbid'

class PictureMoleculeData(PictureDataAnnotation):
    type: Literal["PictureMoleculeData"] = "PictureMoleculeData"  # Discriminator value
    provenance: str
    molecule_structure: str

    class Config:
        extra = 'forbid'

class PictureMiscData(PictureDataAnnotation):
    type: Literal["PictureMiscData"] = "PictureMiscData"  # Discriminator value
    provenance: str
    misc_info: str

    class Config:
        extra = 'forbid'

class PictureLineChartData(PictureDataAnnotation):
    type: Literal["PictureLineChartData"] = "PictureLineChartData"  # Discriminator value
    provenance: str
    chart_type: str  # e.g., "line_chart"
    data: dict

    class Config:
        extra = 'forbid'

class PictureBarChartData(PictureDataAnnotation):
    type: Literal["PictureBarChartData"] = "PictureBarChartData"  # Discriminator value
    provenance: str
    chart_type: str  # e.g., "bar_chart"
    data: dict

    class Config:
        extra = 'forbid'

class PictureStackedBarChartData(PictureDataAnnotation):
    type: Literal["PictureStackedBarChartData"] = "PictureStackedBarChartData"  # Discriminator value
    provenance: str
    chart_type: str  # e.g., "stacked_bar_chart"
    data: dict

    class Config:
        extra = 'forbid'

class PicturePieChartData(PictureDataAnnotation):
    type: Literal["PicturePieChartData"] = "PicturePieChartData"  # Discriminator value
    provenance: str
    chart_type: str  # e.g., "pie_chart"
    data: dict

    class Config:
        extra = 'forbid'

class PictureScatterChartData(PictureDataAnnotation):
    type: Literal["PictureScatterChartData"] = "PictureScatterChartData"  # Discriminator value
    provenance: str
    chart_type: str  # e.g., "scatter_chart"
    data: dict

    class Config:
        extra = 'forbid'

# Define a Union type for all picture data annotations with a discriminator
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

###############################################################################
# Example Advanced Enrichment Models
###############################################################################

class FormulaEnrichmentModel(BaseItemAndImageEnrichmentModel):
    """
    Example that processes doc formula items.
    """
    def __init__(self, enabled: bool = True, images_scale: float = 1.0):
        self.enabled = enabled
        self.images_scale = images_scale  # Added images_scale attribute

    def is_processable(self, doc: DoclingDocument, element: NodeItem) -> bool:
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
        if not self.enabled:
            return
        for enrich_element in element_batch:
            # Example usage of images_scale
            # Check if the image exists and has a resize method
            if hasattr(enrich_element, 'image') and enrich_element.image:
                try:
                    # Assuming enrich_element.image is a PIL Image
                    original_size = enrich_element.image.size  # Size object
                    new_width = int(original_size.width * self.images_scale)
                    new_height = int(original_size.height * self.images_scale)
                    new_size = (new_width, new_height)
                    resized_image = enrich_element.image.resize(new_size)
                    # Update the image in the document
                    enrich_element.image = resized_image
                except AttributeError as e:
                    logger.warning(f"Image scaling failed: {e}")
            # Your formula analysis logic
            # For now, do nothing special.
            yield enrich_element.item


class PictureClassifierEnrichmentModel(BaseEnrichmentModel):
    """
    Example that classifies pictures with a dummy label.
    """
    def __init__(self, enabled: bool = True, images_scale: float = 1.0):
        self.enabled = enabled
        self.images_scale = images_scale  # Added images_scale attribute

    def is_processable(self, doc: DoclingDocument, element: NodeItem) -> bool:
        return self.enabled and isinstance(element, PictureItem)

    def __call__(
        self, doc: DoclingDocument, element_batch: Iterable[NodeItem]
    ) -> Iterable[NodeItem]:
        if not self.enabled:
            return
        for element in element_batch:
            assert isinstance(element, PictureItem)
            try:
                image = element.image  # Assuming PictureItem has 'image' attribute
                if image:
                    original_size = image.size  # Size object
                    new_width = int(original_size.width * self.images_scale)
                    new_height = int(original_size.height * self.images_scale)
                    new_size = (new_width, new_height)
                    resized_image = image.resize(new_size)
                    element.image = resized_image  # Directly assign the resized image
            except AttributeError as e:
                logger.warning(f"Image resizing failed: {e}")

            # Add classification data as instances of Pydantic models
            classification_data = PictureClassificationData(
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

###############################################################################
# Example "Combined" Pipeline (if both formulas & pictures needed at once)
###############################################################################

class MultiEnrichmentPipeline(StandardPdfPipeline):
    """
    Inherits from StandardPdfPipeline but merges multiple enrichments 
    if the user wants formula understanding + picture classification simultaneously.
    """
    def __init__(
        self, 
        pipeline_options: PdfPipelineOptions, 
        do_formula: bool = False,
        do_pictures: bool = False
    ):
        super().__init__(pipeline_options)
        self.enrichment_pipe = []

        # Add formula if toggled
        if do_formula:
            self.enrichment_pipe.append(
                FormulaEnrichmentModel(
                    enabled=True, 
                    images_scale=pipeline_options.images_scale
                )
            )

        # Add pictures if toggled
        if do_pictures:
            self.enrichment_pipe.append(
                PictureClassifierEnrichmentModel(
                    enabled=True, 
                    images_scale=pipeline_options.images_scale
                )
            )

        # If either one is present, keep images in memory
        if do_formula or do_pictures:
            self.keep_backend = True

    @classmethod
    def get_default_options(cls) -> PdfPipelineOptions:
        return PdfPipelineOptions()


class MultiEnrichmentPipelineWithFormulaPictures(MultiEnrichmentPipeline):
    """
    Custom pipeline that enables both formula understanding and picture classification.
    """
    def __init__(self, pipeline_options: PdfPipelineOptions):
        super().__init__(
            pipeline_options,
            do_formula=True,
            do_pictures=True
        )


class FormulaOnlyPipeline(MultiEnrichmentPipeline):
    """
    Custom pipeline that enables only formula understanding.
    """
    def __init__(self, pipeline_options: PdfPipelineOptions):
        super().__init__(
            pipeline_options,
            do_formula=True,
            do_pictures=False
        )


class PictureOnlyPipeline(MultiEnrichmentPipeline):
    """
    Custom pipeline that enables only picture classification.
    """
    def __init__(self, pipeline_options: PdfPipelineOptions):
        super().__init__(
            pipeline_options,
            do_formula=False,
            do_pictures=True
        )

###############################################################################
# Hooks
###############################################################################

PreProcessHook = Callable[[Path, ProcessingConfig], None]
PostProcessHook = Callable[[ConversionResult, ProcessingConfig], None]

###############################################################################
# Pipeline Registry (Optional)
###############################################################################

class PipelineRegistry:
    """
    A registry to map user-chosen keys to pipeline classes, so you can 
    define or override pipeline logic more dynamically.
    """
    def __init__(self):
        # Key -> pipeline class
        self._registry = {}

    def register(self, key: str, pipeline_cls: Any):
        self._registry[key] = pipeline_cls

    def get(self, key: str, default: Any = StandardPdfPipeline) -> Any:
        return self._registry.get(key, default)

# Create a global registry
pipeline_registry = PipelineRegistry()

# Register custom pipelines
pipeline_registry.register("multi_enrichment", MultiEnrichmentPipelineWithFormulaPictures)
pipeline_registry.register("formula_only", FormulaOnlyPipeline)
pipeline_registry.register("picture_only", PictureOnlyPipeline)
# You can register additional pipelines as needed

###############################################################################
# DocumentProcessor Implementation
###############################################################################

class DocumentProcessor:
    """
    A universal docling processor that:
      - Chooses pipeline based on config toggles or registry lookups
      - Optionally merges multiple enrichments
      - Provides hooking, DB storage, multi-format export
    """

    def __init__(
        self,
        config: Optional[ProcessingConfig] = None,
        store_in_db: bool = False,
        db_client: Optional[Any] = None,
        pre_process_hooks: Optional[List[PreProcessHook]] = None,
        post_process_hooks: Optional[List[PostProcessHook]] = None,
        pipeline_key: Optional[str] = None,   # if you want to pick from registry
        pipeline_cls: Optional[Any] = None,   # if you want to pass a pipeline class directly
    ):
        """
        Args:
            config: docling config
            store_in_db: whether to store final results in DB
            db_client: object with insert_document(dict) method
            pre_process_hooks, post_process_hooks: for hooking
            pipeline_key: pick a pipeline from pipeline_registry
            pipeline_cls: pass your own pipeline class 
        """
        self.config = config if config else ProcessingConfig()
        self.store_in_db = store_in_db
        self.db_client = db_client
        self.pre_process_hooks = pre_process_hooks or []
        self.post_process_hooks = post_process_hooks or []
        self.pipeline_key = pipeline_key
        self.user_pipeline_cls = pipeline_cls

        self.converter = self._setup_converter()

    def _setup_converter(self) -> DocumentConverter:
        """
        Build a DocumentConverter. 
        Chooses the appropriate pipeline based on the configuration.
        """
        # Build base docling pipeline options from config
        base_opts = self.config.to_pipeline_options()

        # Decide pipeline class
        pipeline_cls = self._choose_pipeline_class()

        # Create the PdfFormatOption with the chosen pipeline class
        pdf_option = PdfFormatOption(
            pipeline_cls=pipeline_cls,
            pipeline_options=base_opts,
            backend=self._choose_backend()
        )

        # Add docx, etc., if needed
        format_options = {InputFormat.PDF: pdf_option}
        if self.config.mode in [ProcessingMode.ENHANCED, ProcessingMode.MAXIMUM]:
            format_options[InputFormat.DOCX] = WordFormatOption(pipeline_options=base_opts)

        # Return a converter
        return DocumentConverter(format_options=format_options)


    def _choose_pipeline_class(self) -> Any:
        """
        Logic for picking a pipeline:
        1) user_pipeline_cls
        2) pipeline_key in registry
        3) toggles => formula / picture pipeline
        4) fallback => StandardPdfPipeline
        """
        if self.user_pipeline_cls is not None:
            logger.info(f"Using user-supplied pipeline: {self.user_pipeline_cls}")
            return self.user_pipeline_cls

        if self.pipeline_key:
            # If pipeline_key is in pipeline_registry, return that
            # or fallback to StandardPdfPipeline
            cls_ = pipeline_registry.get(self.pipeline_key, StandardPdfPipeline)
            logger.info(f"Using pipeline from registry key '{self.pipeline_key}': {cls_}")
            return cls_

        # If no pipeline_key or user_pipeline_cls, check toggles:
        if self.config.enable_formulas and not self.config.enable_picture_classification:
            logger.info("Using FormulaOnlyPipeline from toggles.")
            return FormulaOnlyPipeline

        if self.config.enable_picture_classification and not self.config.enable_formulas:
            logger.info("Using PictureOnlyPipeline from toggles.")
            return PictureOnlyPipeline

        if self.config.enable_formulas and self.config.enable_picture_classification:
            logger.info("Using MultiEnrichmentPipelineWithFormulaPictures from toggles.")
            return MultiEnrichmentPipelineWithFormulaPictures

        # Default pipeline
        logger.info("No specific pipeline toggles => default to StandardPdfPipeline.")
        return StandardPdfPipeline


    def _choose_backend(self) -> Any:
        """Select docling PDF backend from config."""
        if self.config.backend == BackendType.PYPDFIUM:
            return PyPdfiumDocumentBackend
        elif self.config.backend == BackendType.DOCLING_PARSE:
            return DoclingParseDocumentBackend
        else:
            logger.warning(f"Unknown backend {self.config.backend}, returning None.")
            return None

    def add_pre_process_hook(self, hook: PreProcessHook) -> None:
        self.pre_process_hooks.append(hook)

    def add_post_process_hook(self, hook: PostProcessHook) -> None:
        self.post_process_hooks.append(hook)

    def process(
        self,
        source: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        raises_on_error: bool = False,
    ) -> Dict[str, Any]:
        """
        Process a single document with hooking, DB storing, multi-format export.
        """
        src = Path(source)
        for hook in self.pre_process_hooks:
            try:
                hook(src, self.config)
            except Exception as e:
                logger.warning(f"Pre-process hook failed on {src}: {e}")

        t0 = time.time()
        try:
            conv_result = self.converter.convert(src)
        except Exception as exc:
            logger.exception(f"Conversion error for {src}: {exc}")
            if raises_on_error:
                raise
            conv_result = ConversionResult(
                input=None,
                document=None,
                legacy_document=None,
                status=ConversionStatus.FAILURE,
                errors=[exc]
            )
        elapsed = time.time() - t0

        for hook in self.post_process_hooks:
            try:
                hook(conv_result, self.config)
            except Exception as e:
                logger.warning(f"Post-process hook failed on {src}: {e}")

        # DB store if needed
        if self.store_in_db and self.db_client and conv_result.document:
            try:
                doc_dict = conv_result.document.export_to_dict()
                self.db_client.insert_document(doc_dict)
            except Exception as ex:
                logger.warning(f"DB store failed for {src}: {ex}")

        # Prepare result
        out_data: Dict[str, Any] = {
            "document": conv_result.document,
            "result": conv_result,
            "processing_time": elapsed,
        }

        # Debugging: Check if images are present
        if conv_result.document:
            try:
                for i, page in enumerate(conv_result.document.pages):
                    logger.debug(f"Page {i} type: {type(page)}")
                    if hasattr(page, 'pictures'):
                        logger.debug(f"Page {i} has {len(page.pictures)} pictures.")
                    else:
                        logger.debug(f"Page {i} has no 'pictures' attribute.")
                num_images = sum(len(page.pictures) for page in conv_result.document.pages)
                logger.info(f"Processed document contains {num_images} images.")
            except AttributeError as e:
                logger.warning(f"Failed to count images: {e}")

        # Export if requested
        if output_dir:
            ex_paths = self._export_outputs(conv_result, Path(output_dir))
            out_data["exported_paths"] = ex_paths

        # If partial/failure + raise
        if raises_on_error and conv_result.status not in (ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS):
            raise RuntimeError(f"Docling conversion failed or partial for {src}")

        return out_data

    def batch_process(
        self,
        sources: List[Union[str, Path]],
        output_dir: Optional[Union[str, Path]] = None,
        raises_on_error: bool = False
    ) -> List[Dict[str, Any]]:
        """Process multiple docs in a loop, returning a list of result dictionaries."""
        logger.info(f"Starting batch processing of {len(sources)} docs...")
        results = []
        for s in sources:
            res = self.process(s, output_dir=output_dir, raises_on_error=raises_on_error)
            results.append(res)
        logger.info("Batch processing done.")
        return results

    def _export_outputs(self, conv_res: ConversionResult, output_dir: Path) -> Dict[str, Path]:
        """Save doc in multiple formats (md, html, json, yaml, txt, doctags)."""
        output_dir.mkdir(parents=True, exist_ok=True)
        out_map: Dict[str, Path] = {}

        if not conv_res.document:
            logger.warning("No doc to export in ConversionResult.")
            return out_map
        if not conv_res.input or not conv_res.input.file:
            logger.warning("No input file info in ConversionResult.")
            return out_map

        doc = conv_res.document
        base_name = conv_res.input.file.stem

        for fmt in self.config.export_formats:
            path = None
            if fmt == "md":
                path = output_dir / f"{base_name}.md"
                content = doc.export_to_markdown(image_mode=self.config.image_mode)
                path.write_text(content, encoding="utf-8")

            elif fmt == "html":
                path = output_dir / f"{base_name}.html"
                content = doc.export_to_html(image_mode=self.config.image_mode)
                path.write_text(content, encoding="utf-8")

            elif fmt == "json":
                path = output_dir / f"{base_name}.json"
                with path.open("w", encoding="utf-8") as fp:
                    json.dump(doc.export_to_dict(), fp, indent=2, ensure_ascii=False)

            elif fmt == "yaml":
                path = output_dir / f"{base_name}.yaml"
                with path.open("w", encoding="utf-8") as fp:
                    yaml.safe_dump(doc.export_to_dict(), fp)

            elif fmt == "txt":
                path = output_dir / f"{base_name}.txt"
                text = doc.export_to_text()
                path.write_text(text, encoding="utf-8")

            elif fmt == "doctags":
                path = output_dir / f"{base_name}.doctags"
                doc_tags = doc.export_to_document_tokens()
                path.write_text(doc_tags, encoding="utf-8")

            else:
                logger.warning(f"Unrecognized export format '{fmt}', skipping.")
                continue

            if path:
                out_map[fmt] = path

        return out_map

    @classmethod
    def for_mode(cls, mode: ProcessingMode) -> 'DocumentProcessor':
        """Convenience: build from a ProcessingMode preset."""
        cfg = ProcessingConfig.for_mode(mode)
        return cls(config=cfg)


###############################################################################
# Main (Example Usage)
###############################################################################

def main():
    logging.basicConfig(level=logging.INFO)

    # Example config: docling_parse backend, formula + pictures toggles, 
    # with images embedded in MD/HTML.
    config = ProcessingConfig(
        mode=ProcessingMode.ENHANCED,
        backend=BackendType.DOCLING_PARSE,
        enable_formulas=True,
        enable_picture_classification=True,
        export_formats=["md", "html", "json"], 
        image_mode=ImageRefMode.EMBEDDED  # Changed to EMBEDDED for testing
    )

    # Mock DB
    class MockDbClient:
        def insert_document(self, doc_dict: dict):
            logger.info(f"[DB] Inserted doc with keys: {list(doc_dict.keys())}")

    processor = DocumentProcessor(
        config=config,
        store_in_db=True,
        db_client=MockDbClient(),
        pipeline_key="multi_enrichment"  # Explicitly specify the pipeline to use
    )

    # Hooks
    def my_pre_hook(path: Path, cfg: ProcessingConfig):
        logger.info(f"Pre-hook => Checking file {path}")
        if not path.exists():
            raise FileNotFoundError(f"{path} does not exist")

    def my_post_hook(conv_res: ConversionResult, cfg: ProcessingConfig):
        logger.info(f"Post-hook => Conversion status {conv_res.status}")

    processor.add_pre_process_hook(my_pre_hook)
    processor.add_post_process_hook(my_post_hook)

    input_files = [
        "tests/data/1706.03762v7.pdf",
        "tests/data/jakes-resume.pdf"
    ]

    results = processor.batch_process(input_files, output_dir="scratch_universal")
    fails = sum(r["result"].status == ConversionStatus.FAILURE for r in results)
    partials = sum(r["result"].status == ConversionStatus.PARTIAL_SUCCESS for r in results)
    successes = sum(r["result"].status == ConversionStatus.SUCCESS for r in results)

    logger.info(f"Done => successes={successes}, partials={partials}, fails={fails}")


if __name__ == "__main__":
    main()
