from pathlib import Path
import logging
from typing import Union, List, Dict, Any, Optional
import json
import yaml
import time

from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
from docling.datamodel.base_models import (
    InputFormat,
    ConversionStatus,
)
from docling.datamodel.document import (
    InputDocument,
    ConversionResult
)
from docling_core.types.doc import DoclingDocument
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.backend.docling_parse_backend import DoclingParseDocumentBackend

from .config import ProcessingConfig, ProcessingMode, BackendType

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """High-level interface for document processing"""
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        self.config = config if config is not None else ProcessingConfig()
        self.converter = self._setup_converter()
    
    def _setup_converter(self) -> DocumentConverter:
        """Configure document converter based on settings"""
        pipeline_options = self.config.to_pipeline_options()
        
        # Select backend based on config
        backend = None
        if self.config.backend == BackendType.PYPDFIUM:
            backend = PyPdfiumDocumentBackend
        elif self.config.backend == BackendType.DOCLING_PARSE:
            backend = DoclingParseDocumentBackend

        # Configure format options
        format_options = {
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
                backend=backend
            )
        }

        # Add support for other formats in enhanced modes
        if self.config.mode in [ProcessingMode.ENHANCED, ProcessingMode.MAXIMUM]:
            format_options.update({
                InputFormat.DOCX: WordFormatOption(
                    pipeline_options=pipeline_options
                ),
                # Add other format options as needed
            })
        
        return DocumentConverter(format_options=format_options)

    def process(
        self,
        source: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """Process a single document"""
        source_path = Path(source)
        start_time = time.time()
        
        # Convert document
        result = self.converter.convert(source_path)
        
        # Prepare output
        outputs = {
            "document": result.document,
            "result": result,
            "processing_time": time.time() - start_time
        }
        
        if output_dir:
            outputs.update(
                self._save_outputs(result, Path(output_dir))
            )
        
        return outputs
    
    def _save_outputs(
        self,
        result: ConversionResult,
        output_dir: Path
    ) -> Dict[str, Path]:
        """Save outputs in requested formats"""
        output_dir.mkdir(parents=True, exist_ok=True)
        outputs = {}
        
        base_name = result.input.file.stem
        doc: DoclingDocument = result.document
        
        # Save each requested format
        for fmt in self.config.export_formats:
            if fmt == "md":
                path = output_dir / f"{base_name}.md"
                with path.open("w", encoding="utf-8") as f:
                    f.write(doc.export_to_markdown())
                outputs["markdown_path"] = path
                
            elif fmt == "html":
                path = output_dir / f"{base_name}.html"
                with path.open("w", encoding="utf-8") as f:
                    f.write(doc.export_to_html())
                outputs["html_path"] = path
                
            elif fmt == "json":
                path = output_dir / f"{base_name}.json"
                with path.open("w", encoding="utf-8") as f:
                    json.dump(doc.export_to_dict(), f, indent=2)
                outputs["json_path"] = path
                
            elif fmt == "yaml":
                path = output_dir / f"{base_name}.yaml"
                with path.open("w", encoding="utf-8") as f:
                    yaml.safe_dump(doc.export_to_dict(), f)
                outputs["yaml_path"] = path
                
            elif fmt == "txt":
                path = output_dir / f"{base_name}.txt"
                with path.open("w", encoding="utf-8") as f:
                    f.write(doc.export_to_text())
                outputs["text_path"] = path
                
            elif fmt == "doctags":
                path = output_dir / f"{base_name}.doctags"
                with path.open("w", encoding="utf-8") as f:
                    f.write(doc.export_to_document_tokens())
                outputs["doctags_path"] = path
        
        return outputs
    
    def batch_process(
        self,
        sources: List[Union[str, Path]],
        output_dir: Optional[Union[str, Path]] = None,
    ) -> List[Dict[str, Any]]:
        """Process multiple documents"""
        return [
            self.process(source, output_dir)
            for source in sources
        ]

    @classmethod
    def for_mode(cls, mode: ProcessingMode) -> 'DocumentProcessor':
        """Create a processor configured for a specific mode"""
        return cls(ProcessingConfig.for_mode(mode))