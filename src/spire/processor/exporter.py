"""
Document export functionality for various formats.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

import yaml
from docling.datamodel.document import ConversionResult
from docling_core.types.doc import ImageRefMode

logger = logging.getLogger(__name__)

class DocumentExporter:
    """
    Handles exporting documents to various formats.
    Supports: markdown, HTML, JSON, YAML, text, and doctags.
    """
    
    def __init__(self, image_mode: ImageRefMode = ImageRefMode.REFERENCED):
        self.image_mode = image_mode

    def export(
        self,
        conv_result: ConversionResult,
        output_dir: Path,
        formats: list[str]
    ) -> Dict[str, Path]:
        """
        Export document to multiple formats.
        
        Args:
            conv_result: Conversion result containing document
            output_dir: Directory for output files
            formats: List of formats to export to
            
        Returns:
            Dictionary mapping format to output path
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        out_map: Dict[str, Path] = {}

        if not conv_result.document:
            logger.warning("No document to export in ConversionResult")
            return out_map
            
        if not conv_result.input or not conv_result.input.file:
            logger.warning("No input file info in ConversionResult")
            return out_map

        doc = conv_result.document
        base_name = conv_result.input.file.stem

        for fmt in formats:
            path = None
            
            if fmt == "md":
                path = output_dir / f"{base_name}.md"
                content = doc.export_to_markdown(image_mode=self.image_mode)
                path.write_text(content, encoding="utf-8")

            elif fmt == "html":
                path = output_dir / f"{base_name}.html"
                content = doc.export_to_html(image_mode=self.image_mode)
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
                logger.warning(f"Unrecognized export format '{fmt}', skipping")
                continue

            if path:
                out_map[fmt] = path

        return out_map