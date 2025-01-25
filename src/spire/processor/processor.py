"""
Main document processor implementation.
"""

import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from docling.datamodel.base_models import ConversionStatus
from docling.datamodel.document import ConversionResult
from docling.document_converter import DocumentConverter
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.backend.docling_parse_backend import DoclingParseDocumentBackend

from src.spire.types.config import ProcessingConfig
from src.spire.types.enums import BackendType, ProcessingMode
from src.spire.pipeline import pipeline_registry

from .hooks import PreProcessHook, PostProcessHook
from .exporter import DocumentExporter

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    Main document processor that:
    - Selects pipeline based on config or registry
    - Handles multiple enrichments
    - Provides pre/post processing hooks
    - Supports DB storage
    - Enables multi-format export
    """

    def __init__(
        self,
        config: Optional[ProcessingConfig] = None,
        store_in_db: bool = False,
        db_client: Optional[Any] = None,
        pre_process_hooks: Optional[List[PreProcessHook]] = None,
        post_process_hooks: Optional[List[PostProcessHook]] = None,
        pipeline_key: Optional[str] = None,
        pipeline_cls: Optional[Any] = None,
    ):
        """
        Initialize processor with configuration and optional components.
        
        Args:
            config: Processing configuration
            store_in_db: Whether to store results in database
            db_client: Database client for storage
            pre_process_hooks: List of pre-processing hooks
            post_process_hooks: List of post-processing hooks
            pipeline_key: Key for pipeline registry lookup
            pipeline_cls: Custom pipeline class
        """
        self.config = config if config else ProcessingConfig()
        self.store_in_db = store_in_db
        self.db_client = db_client
        self.pre_process_hooks = pre_process_hooks or []
        self.post_process_hooks = post_process_hooks or []
        self.pipeline_key = pipeline_key
        self.user_pipeline_cls = pipeline_cls

        self.converter = self._setup_converter()
        self.exporter = DocumentExporter(image_mode=self.config.image_mode)

    def _setup_converter(self) -> DocumentConverter:
            """Configure document converter with appropriate pipeline."""
            from docling.document_converter import (
                PdfFormatOption, 
                WordFormatOption,
                PowerpointFormatOption,
                ExcelFormatOption,
                MarkdownFormatOption,
                AsciiDocFormatOption,
                HTMLFormatOption,
                XMLPubMedFormatOption,
                PatentUsptoFormatOption,
                ImageFormatOption
            )
            from docling.datamodel.base_models import InputFormat
            
            # Build pipeline options from config
            base_opts = self.config.to_pipeline_options()

            # Select pipeline class
            pipeline_cls = self._choose_pipeline_class()

            # Create format options map
            format_opts = {}

            # Default configuration for PDF/Image processing
            pdf_backend = self._choose_backend()
            if pdf_backend:
                pdf_option = PdfFormatOption(
                    pipeline_cls=pipeline_cls,
                    pipeline_options=base_opts,
                    backend=pdf_backend
                )
                format_opts[InputFormat.PDF] = pdf_option
                format_opts[InputFormat.IMAGE] = ImageFormatOption(
                    pipeline_options=base_opts,
                    backend=pdf_backend
                )

            # Add support for other formats in enhanced/maximum modes
            if self.config.mode in [ProcessingMode.ENHANCED, ProcessingMode.MAXIMUM]:
                format_opts.update({
                    InputFormat.DOCX: WordFormatOption(pipeline_options=base_opts),
                    InputFormat.PPTX: PowerpointFormatOption(pipeline_options=base_opts),
                    InputFormat.XLSX: ExcelFormatOption(pipeline_options=base_opts),
                    InputFormat.MD: MarkdownFormatOption(pipeline_options=base_opts),
                    InputFormat.ASCIIDOC: AsciiDocFormatOption(pipeline_options=base_opts),
                    InputFormat.HTML: HTMLFormatOption(pipeline_options=base_opts),
                    InputFormat.XML_PUBMED: XMLPubMedFormatOption(pipeline_options=base_opts),
                    InputFormat.XML_USPTO: PatentUsptoFormatOption(pipeline_options=base_opts),
                })

            return DocumentConverter(format_options=format_opts)

    def _choose_pipeline_class(self) -> Any:
        """
        Select pipeline class based on:
        1. User-provided class
        2. Registry lookup
        3. Config toggles
        4. Default pipeline
        """
        if self.user_pipeline_cls is not None:
            logger.info(f"Using user-supplied pipeline: {self.user_pipeline_cls}")
            return self.user_pipeline_cls

        if self.pipeline_key:
            cls_ = pipeline_registry.get(self.pipeline_key)
            logger.info(f"Using pipeline from registry key '{self.pipeline_key}': {cls_}")
            return cls_

        # Choose based on config toggles
        if self.config.enable_formulas and self.config.enable_picture_classification:
            logger.info("Using multi-enrichment pipeline from toggles")
            return pipeline_registry.get("multi_enrichment")
        elif self.config.enable_formulas:
            logger.info("Using formula-only pipeline from toggles")
            return pipeline_registry.get("formula_only")
        elif self.config.enable_picture_classification:
            logger.info("Using picture-only pipeline from toggles")
            return pipeline_registry.get("picture_only")

        # Default pipeline
        from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
        logger.info("Using default StandardPdfPipeline")
        return StandardPdfPipeline

    def _choose_backend(self) -> Any:
        """Select document processing backend."""
        from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
        from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
        from docling.backend.docling_parse_v2_backend import DoclingParseV2DocumentBackend
        from docling.backend.msword_backend import MsWordDocumentBackend
        from docling.backend.mspowerpoint_backend import MsPowerpointDocumentBackend
        from docling.backend.msexcel_backend import MsExcelDocumentBackend
        from docling.backend.md_backend import MarkdownDocumentBackend
        from docling.backend.asciidoc_backend import AsciiDocBackend
        from docling.backend.html_backend import HTMLDocumentBackend
        from docling.backend.xml.pubmed_backend import PubMedDocumentBackend
        from docling.backend.xml.uspto_backend import PatentUsptoDocumentBackend
        from docling.backend.json.docling_json_backend import DoclingJSONBackend

        backend_map = {
            BackendType.PYPDFIUM: PyPdfiumDocumentBackend,
            BackendType.DOCLING_PARSE: DoclingParseDocumentBackend,
            BackendType.DOCLING_PARSE_V2: DoclingParseV2DocumentBackend,
            BackendType.WORD: MsWordDocumentBackend,
            BackendType.POWERPOINT: MsPowerpointDocumentBackend,
            BackendType.EXCEL: MsExcelDocumentBackend,
            BackendType.MARKDOWN: MarkdownDocumentBackend,
            BackendType.ASCIIDOC: AsciiDocBackend,
            BackendType.HTML: HTMLDocumentBackend,
            BackendType.PUBMED: PubMedDocumentBackend,
            BackendType.USPTO: PatentUsptoDocumentBackend,
            BackendType.JSON_DOCLING: DoclingJSONBackend,
            # BackendType.IMAGE uses DoclingParseV2DocumentBackend
            BackendType.IMAGE: DoclingParseV2DocumentBackend,
        }

        backend = backend_map.get(self.config.backend)
        if backend is None:
            logger.warning(f"Unknown backend {self.config.backend}, falling back to DoclingParseV2DocumentBackend")
            return DoclingParseV2DocumentBackend
            
        return backend

    def add_pre_process_hook(self, hook: PreProcessHook) -> None:
        """Add a pre-processing hook."""
        self.pre_process_hooks.append(hook)

    def add_post_process_hook(self, hook: PostProcessHook) -> None:
        """Add a post-processing hook."""
        self.post_process_hooks.append(hook)

    def process(
        self,
        source: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        raises_on_error: bool = False,
    ) -> Dict[str, Any]:
        """
        Process a single document.
        
        Args:
            source: Path to input document
            output_dir: Directory for output files
            raises_on_error: Whether to raise exceptions
            
        Returns:
            Dictionary containing processing results
        """
        src = Path(source)
        
        # Run pre-process hooks
        for hook in self.pre_process_hooks:
            try:
                hook(src, self.config)
            except Exception as e:
                logger.warning(f"Pre-process hook failed: {e}")

        # Process document
        t0 = time.time()
        try:
            conv_result = self.converter.convert(src)
        except Exception as exc:
            logger.exception(f"Conversion error: {exc}")
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

        # Run post-process hooks
        for hook in self.post_process_hooks:
            try:
                hook(conv_result, self.config)
            except Exception as e:
                logger.warning(f"Post-process hook failed: {e}")

        # Store in database if configured
        if self.store_in_db and self.db_client and conv_result.document:
            try:
                doc_dict = conv_result.document.export_to_dict()
                self.db_client.insert_document(doc_dict)
            except Exception as e:
                logger.warning(f"Database storage failed: {e}")

        # Prepare result dictionary
        result: Dict[str, Any] = {
            "document": conv_result.document,
            "result": conv_result,
            "processing_time": elapsed,
        }

        # Export if output directory specified
        if output_dir:
            export_paths = self.exporter.export(
                conv_result,
                Path(output_dir),
                self.config.export_formats
            )
            result["exported_paths"] = export_paths

        # Handle errors
        if (raises_on_error and 
            conv_result.status not in (ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS)):
            raise RuntimeError(f"Document conversion failed for {src}")

        return result

    def batch_process(
        self,
        sources: List[Union[str, Path]],
        output_dir: Optional[Union[str, Path]] = None,
        raises_on_error: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Process multiple documents.
        
        Args:
            sources: List of input document paths
            output_dir: Directory for output files
            raises_on_error: Whether to raise exceptions
            
        Returns:
            List of processing results
        """
        logger.info(f"Starting batch processing of {len(sources)} documents")
        results = []
        for source in sources:
            result = self.process(
                source,
                output_dir=output_dir,
                raises_on_error=raises_on_error
            )
            results.append(result)
        
        logger.info(f"Batch processing completed: {len(results)} documents processed")
        return results

    @classmethod
    def for_mode(cls, mode: ProcessingMode) -> 'DocumentProcessor':
        """
        Create a processor configured for a specific processing mode.
        
        Args:
            mode: Processing mode to configure for
            
        Returns:
            Configured DocumentProcessor instance
        """
        cfg = ProcessingConfig.for_mode(mode)
        return cls(config=cfg)

    def _debug_log_document_info(self, conv_result: ConversionResult) -> None:
        """
        Log debug information about processed document.
        
        Args:
            conv_result: Conversion result to analyze
        """
        if not conv_result.document:
            logger.debug("No document available for debug logging")
            return

        try:
            for i, page in enumerate(conv_result.document.pages):
                logger.debug(f"Page {i} type: {type(page)}")
                if hasattr(page, 'pictures'):
                    logger.debug(f"Page {i} has {len(page.pictures)} pictures")
                else:
                    logger.debug(f"Page {i} has no pictures attribute")
            
            total_images = sum(
                len(page.pictures) 
                for page in conv_result.document.pages 
                if hasattr(page, 'pictures')
            )
            logger.info(f"Document contains {total_images} total images")
        except AttributeError as e:
            logger.warning(f"Error during debug logging: {e}")

    def process_with_validation(
        self,
        source: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        validation_hooks: Optional[List[PostProcessHook]] = None
    ) -> Dict[str, Any]:
        """
        Process a document with additional validation steps.
        
        Args:
            source: Path to input document
            output_dir: Directory for output files
            validation_hooks: Additional validation hooks to run
            
        Returns:
            Processing results with validation info
        """
        # Process document
        result = self.process(source, output_dir, raises_on_error=True)
        
        # Run validation hooks if provided
        if validation_hooks and result["document"]:
            validation_results = []
            for hook in validation_hooks:
                try:
                    hook(result["result"], self.config)
                    validation_results.append({"hook": hook.__name__, "status": "passed"})
                except Exception as e:
                    validation_results.append({
                        "hook": hook.__name__,
                        "status": "failed",
                        "error": str(e)
                    })
            result["validation_results"] = validation_results
            
        return result