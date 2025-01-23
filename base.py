from pathlib import Path
from typing import Union, List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat, ConversionStatus
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    AcceleratorOptions,
    AcceleratorDevice,
    EasyOcrOptions,
    TesseractOcrOptions
)

class OcrEngine(Enum):
    """Available OCR engines"""
    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    RAPID = "rapid"
    MAC = "mac"  # Mac-only

@dataclass
class ProcessingOptions:
    """High-level options for document processing"""
    ocr_engine: OcrEngine = OcrEngine.TESSERACT
    force_ocr: bool = False
    extract_tables: bool = True
    extract_images: bool = True
    image_resolution: float = 2.0
    accelerator: AcceleratorDevice = AcceleratorDevice.AUTO
    num_threads: int = 8

class DocumentProcessor:
    """High-level interface for document processing"""
    
    def __init__(self, options: Optional[ProcessingOptions] = None):
        self.options = options or ProcessingOptions()
        self.converter = self._setup_converter()
    
    def _setup_converter(self) -> DocumentConverter:
        """Configure the document converter based on options"""
        pipeline_options = PdfPipelineOptions()
        
        # Configure OCR
        if self.options.ocr_engine == OcrEngine.TESSERACT:
            pipeline_options.ocr_options = TesseractOcrOptions(
                force_full_page_ocr=self.options.force_ocr
            )
        elif self.options.ocr_engine == OcrEngine.EASYOCR:
            pipeline_options.ocr_options = EasyOcrOptions(
                force_full_page_ocr=self.options.force_ocr
            )
        
        # Configure acceleration
        pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=self.options.num_threads,
            device=self.options.accelerator
        )
        
        # Configure table extraction
        pipeline_options.do_table_structure = self.options.extract_tables
        if self.options.extract_tables:
            pipeline_options.table_structure_options.do_cell_matching = True
        
        # Configure image extraction
        if self.options.extract_images:
            pipeline_options.images_scale = self.options.image_resolution
            pipeline_options.generate_page_images = True
            pipeline_options.generate_picture_images = True
        
        return DocumentConverter(format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        })
    
    def process_document(
        self, 
        source: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        formats: List[str] = ["md", "json", "yaml"]
    ) -> Dict[str, Any]:
        """Process a single document and export in specified formats"""
        source_path = Path(source)
        result = self.converter.convert(source_path)
        
        if result.status != ConversionStatus.SUCCESS:
            raise ValueError(f"Document conversion failed: {result.errors}")
        
        outputs = {}
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            base_name = source_path.stem
            
            # Export in requested formats
            if "md" in formats:
                md_path = output_path / f"{base_name}.md"
                result.document.save_as_markdown(md_path)
                outputs["markdown_path"] = md_path
                
            if "json" in formats:
                json_path = output_path / f"{base_name}.json"
                with json_path.open("w") as f:
                    f.write(json.dumps(result.document.export_to_dict()))
                outputs["json_path"] = json_path
                
            if "yaml" in formats:
                yaml_path = output_path / f"{base_name}.yaml"
                with yaml_path.open("w") as f:
                    f.write(yaml.safe_dump(result.document.export_to_dict()))
                outputs["yaml_path"] = yaml_path
        
        outputs["document"] = result.document
        outputs["conversion_result"] = result
        return outputs

    def process_batch(
        self,
        sources: List[Union[str, Path]],
        output_dir: Optional[Union[str, Path]] = None,
        formats: List[str] = ["md", "json", "yaml"]
    ) -> List[Dict[str, Any]]:
        """Process multiple documents in batch"""
        return [
            self.process_document(source, output_dir, formats)
            for source in sources
        ]