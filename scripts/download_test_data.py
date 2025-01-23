import urllib.request
from pathlib import Path
import sys

def download_test_pdfs():
    """Download sample PDFs for testing"""
    test_data_dir = Path("tests/data")
    test_data_dir.mkdir(parents=True, exist_ok=True)

    # Sample PDFs from arXiv
    urls = {
        "2206.01062.pdf": "https://arxiv.org/pdf/2206.01062.pdf",
        "2203.01017v2.pdf": "https://arxiv.org/pdf/2203.01017v2.pdf",
        "2305.03393v1.pdf": "https://arxiv.org/pdf/2305.03393v1.pdf",
    }

    for filename, url in urls.items():
        output_path = test_data_dir / filename
        if not output_path.exists():
            print(f"Downloading {filename}...")
            urllib.request.urlretrieve(url, output_path)
            print(f"Downloaded {filename}")
        else:
            print(f"File {filename} already exists")

if __name__ == "__main__":
    download_test_pdfs()