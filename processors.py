from pathlib import Path
from typing import List, Dict, Optional, Union
import pandas as pd
from PIL import Image

from docling_core.types.doc import PictureItem, TableItem, ImageRefMode

class TableProcessor:
    """Specialized processor for table extraction and export"""
    
    def __init__(self, document_processor: DocumentProcessor):
        self.doc_processor = document_processor
    
    def extract_tables(
        self,
        source: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        formats: List[str] = ["csv", "html"]
    ) -> List[Dict[str, Union[pd.DataFrame, str]]]:
        """Extract tables from document and optionally export them"""
        result = self.doc_processor.process_document(source)
        document = result["document"]
        
        tables = []
        for idx, table in enumerate(document.tables):
            table_data = {
                "index": idx,
                "dataframe": table.export_to_dataframe(),
                "html": table.export_to_html()
            }
            
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                base_name = Path(source).stem
                
                if "csv" in formats:
                    csv_path = output_path / f"{base_name}-table-{idx+1}.csv"
                    table_data["dataframe"].to_csv(csv_path)
                    table_data["csv_path"] = csv_path
                
                if "html" in formats:
                    html_path = output_path / f"{base_name}-table-{idx+1}.html"
                    with html_path.open("w") as f:
                        f.write(table_data["html"])
                    table_data["html_path"] = html_path
            
            tables.append(table_data)
        
        return tables

class ImageProcessor:
    """Specialized processor for image and figure extraction"""
    
    def __init__(self, document_processor: DocumentProcessor):
        self.doc_processor = document_processor
    
    def extract_images(
        self,
        source: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        save_pages: bool = True,
        image_format: str = "png"
    ) -> Dict[str, List[Dict[str, Union[Image.Image, Path]]]]:
        """Extract images, figures, and page images from document"""
        result = self.doc_processor.process_document(source)
        document = result["document"]
        
        output: Dict[str, List[Dict[str, Union[Image.Image, Path]]]] = {
            "pages": [],
            "figures": [],
            "tables": []
        }
        
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            base_name = Path(source).stem
            
            # Save page images
            if save_pages:
                for page_no, page in document.pages.items():
                    image_data = {
                        "page_number": page_no,
                        "image": page.image.pil_image
                    }
                    
                    if output_dir:
                        image_path = output_path / f"{base_name}-page-{page_no}.{image_format}"
                        page.image.pil_image.save(image_path, format=image_format.upper())
                        image_data["path"] = image_path
                    
                    output["pages"].append(image_data)
            
            # Extract figures and tables with images
            for element, *level in document.iterate_items():
                if isinstance(element, PictureItem):
                    image_data = {
                        "reference": element.self_ref,
                        "image": element.get_image(document)
                    }
                    
                    if output_dir:
                        image_path = output_path / f"{base_name}-figure-{len(output['figures'])+1}.{image_format}"
                        element.get_image(document).save(image_path, format=image_format.upper())
                        image_data["path"] = image_path
                    
                    output["figures"].append(image_data)
                
                elif isinstance(element, TableItem):
                    image_data = {
                        "reference": element.self_ref,
                        "image": element.get_image(document)
                    }
                    
                    if output_dir:
                        image_path = output_path / f"{base_name}-table-img-{len(output['tables'])+1}.{image_format}"
                        element.get_image(document).save(image_path, format=image_format.upper())
                        image_data["path"] = image_path
                    
                    output["tables"].append(image_data)
        
        return output