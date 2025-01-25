#!/usr/bin/env python3
"""
Download sample documents for testing the document processor.

This script downloads various types of documents that showcase different
features of the document processing library.
"""

import os
import logging
from pathlib import Path
import urllib.request
import ssl
from typing import Dict, List
import hashlib
from tqdm import tqdm
import requests
import tempfile
import shutil

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Sample documents to download
DOCUMENTS = {
    "research_papers": [
        {
            "name": "attention_paper.pdf",
            "url": "https://arxiv.org/pdf/1706.03762.pdf",
            "description": "Attention Is All You Need (complex formulas, figures)",
        },
        {
            "name": "bert_paper.pdf",
            "url": "https://arxiv.org/pdf/1810.04805.pdf",
            "description": "BERT paper (tables, diagrams, formulas)",
        },
        {
            "name": "resnet_paper.pdf",
            "url": "https://arxiv.org/pdf/1512.03385.pdf",
            "description": "ResNet paper (deep learning architecture diagrams)",
        }
    ],
    "technical_docs": [
        {
            "name": "python_tutorial.pdf",
            "url": "https://docs.python.org/3/tutorial/tutorial.pdf",
            "description": "Python tutorial (code blocks, simple diagrams)",
        },
        {
            "name": "scipy_paper.pdf",
            "url": "https://arxiv.org/pdf/1907.10121.pdf",
            "description": "SciPy paper (technical diagrams, equations)",
        }
    ],
    "data_science": [
        {
            "name": "matplotlib_sample.pdf",
            "url": "https://matplotlib.org/Matplotlib.pdf",
            "description": "Matplotlib gallery (various chart types)",
        }
    ],
    "uspto_patents": [
        {
            "name": "sample_patent.xml",
            "url": "https://bulkdata.uspto.gov/data/patent/grant/redbook/2021/ipg210105.xml",
            "description": "USPTO Patent sample (XML format)",
        }
    ],
    "pubmed_articles": [
        {
            "name": "pubmed_sample.xml",
            "url": "https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_sample/sample.xml",
            "description": "PubMed Central sample article (XML format)",
        }
    ]
}

# Add GitHub-hosted samples
GITHUB_SAMPLES = {
    "excel_samples": [
        {
            "repo": "pandas-dev/pandas",
            "path": "pandas/tests/io/data/excel/test1.xlsx",
            "name": "pandas_test.xlsx",
            "description": "Sample Excel file with various data types",
        },
        {
            "repo": "python-openxml/python-docx",
            "path": "tests/test_files/sample.docx",
            "name": "sample_doc.docx",
            "description": "Sample Word document",
        }
    ]
}

class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)

def download_from_github(repo: str, path: str, output_path: Path) -> bool:
    """Download a file from GitHub."""
    try:
        url = f"https://raw.githubusercontent.com/{repo}/master/{path}"
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        
        with DownloadProgressBar(unit='B', unit_scale=True,
                               miniters=1, desc=output_path.name,
                               total=total_size) as t:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        t.update(len(chunk))
        return True
        
    except Exception as e:
        logger.error(f"Failed to download from GitHub: {e}")
        if output_path.exists():
            output_path.unlink()
        return False

def download_file(url: str, output_path: Path) -> bool:
    """Download a file with progress bar."""
    try:
        # Create SSL context
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        # First try with requests
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            
            with DownloadProgressBar(unit='B', unit_scale=True,
                                   miniters=1, desc=output_path.name,
                                   total=total_size) as t:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=block_size):
                        if chunk:
                            f.write(chunk)
                            t.update(len(chunk))
            return True
            
        except Exception:
            # Fallback to urllib
            with DownloadProgressBar(unit='B', unit_scale=True,
                                   miniters=1, desc=output_path.name) as t:
                opener = urllib.request.build_opener(
                    urllib.request.HTTPSHandler(context=ctx)
                )
                with opener.open(url) as response:
                    with open(output_path, 'wb') as f:
                        while True:
                            chunk = response.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                            t.update_to(b=1, bsize=len(chunk))
            return True
            
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        if output_path.exists():
            output_path.unlink()
        return False

def download_sample_documents(base_dir: Path) -> Dict[str, List[Path]]:
    """Download sample documents for testing."""
    downloaded_files: Dict[str, List[Path]] = {}
    
    # Create base directory
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Download regular documents
    for category, documents in DOCUMENTS.items():
        category_dir = base_dir / category
        category_dir.mkdir(exist_ok=True)
        
        downloaded_files[category] = []
        
        for doc in documents:
            output_path = category_dir / doc["name"]
            
            # Skip if file exists
            if output_path.exists():
                logger.info(f"Skipping {doc['name']} (already downloaded)")
                downloaded_files[category].append(output_path)
                continue
                
            logger.info(f"Downloading {doc['name']}...")
            logger.info(f"Description: {doc['description']}")
            
            if download_file(doc["url"], output_path):
                downloaded_files[category].append(output_path)
                logger.info(f"Successfully downloaded {doc['name']}")
            else:
                logger.error(f"Failed to download {doc['name']}")

    # Download GitHub samples
    for category, samples in GITHUB_SAMPLES.items():
        category_dir = base_dir / category
        category_dir.mkdir(exist_ok=True)
        
        downloaded_files[category] = []
        
        for sample in samples:
            output_path = category_dir / sample["name"]
            
            # Skip if file exists
            if output_path.exists():
                logger.info(f"Skipping {sample['name']} (already downloaded)")
                downloaded_files[category].append(output_path)
                continue
                
            logger.info(f"Downloading {sample['name']}...")
            logger.info(f"Description: {sample['description']}")
            
            if download_from_github(sample["repo"], sample["path"], output_path):
                downloaded_files[category].append(output_path)
                logger.info(f"Successfully downloaded {sample['name']}")
            else:
                logger.error(f"Failed to download {sample['name']}")

    return downloaded_files

def main():
    """Download sample documents."""
    # Set up download directory
    download_dir = Path("sample_documents")
    
    try:
        logger.info("Starting document download...")
        downloaded = download_sample_documents(download_dir)
        
        # Print summary
        total_files = sum(len(files) for files in downloaded.values())
        logger.info("\nDownload Summary:")
        logger.info(f"Total files downloaded: {total_files}")
        
        if total_files > 0:
            for category, files in downloaded.items():
                if files:  # Only show categories with files
                    logger.info(f"\n{category.replace('_', ' ').title()}:")
                    for file_path in files:
                        size_mb = file_path.stat().st_size / (1024 * 1024)
                        logger.info(f"  - {file_path.name} ({size_mb:.1f}MB)")
                    
            logger.info(f"\nFiles downloaded to: {download_dir.absolute()}")
        else:
            logger.warning("No files were downloaded successfully.")
        
    except Exception as e:
        logger.error(f"Download failed: {e}", exc_info=True)
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())