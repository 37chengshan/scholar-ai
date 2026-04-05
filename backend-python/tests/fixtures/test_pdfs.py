"""Test PDF fixtures for performance benchmarking.

Generates simple test PDFs for validating parallel pipeline performance.
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_test_pdf(num_pages: int, output_path: str) -> None:
    """Create a simple test PDF with specified number of pages.
    
    Args:
        num_pages: Number of pages to generate
        output_path: Path to save the PDF file
    """
    c = canvas.Canvas(output_path, pagesize=letter)
    
    for page_num in range(1, num_pages + 1):
        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, f"Test Paper - Page {page_num}")
        
        # Content sections (simulates IMRaD structure)
        c.setFont("Helvetica", 12)
        c.drawString(100, 700, f"This is test content for page {page_num} of a scholarly paper.")
        
        # Abstract section
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, 650, "Abstract:")
        c.setFont("Helvetica", 11)
        c.drawString(100, 630, "This paper demonstrates PDF parsing and parallel extraction.")
        
        # Introduction
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, 590, "Introduction:")
        c.setFont("Helvetica", 11)
        c.drawString(100, 570, "Background information and context for the research presented here.")
        
        # Methods
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, 530, "Methods:")
        c.setFont("Helvetica", 11)
        c.drawString(100, 510, "Experimental procedures and data collection techniques.")
        
        # Results
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, 470, "Results:")
        c.setFont("Helvetica", 11)
        c.drawString(100, 450, "Key findings and statistical analysis of experimental data.")
        
        # Discussion
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, 410, "Discussion:")
        c.setFont("Helvetica", 11)
        c.drawString(100, 390, "Analysis and implications of the results for the field.")
        
        # Conclusion
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, 350, "Conclusion:")
        c.setFont("Helvetica", 11)
        c.drawString(100, 330, "Summary of contributions and directions for future work.")
        
        # References placeholder
        c.setFont("Helvetica-Bold", 10)
        c.drawString(100, 290, "References:")
        c.setFont("Helvetica", 10)
        c.drawString(100, 270, "[1] Author, A. (2024). Paper title. Journal Name, vol(issue), pages.")
        
        # Finish this page
        c.showPage()
    
    # Save PDF
    c.save()


def get_test_pdf_10_pages() -> str:
    """Get path to 10-page test PDF for single paper performance benchmark.
    
    Creates the PDF if it doesn't exist.
    
    Returns:
        Absolute path to test_10_pages.pdf
    """
    fixture_dir = Path(__file__).parent / "pdfs"
    fixture_dir.mkdir(exist_ok=True)
    
    pdf_path = fixture_dir / "test_10_pages.pdf"
    
    if not pdf_path.exists():
        create_test_pdf(10, str(pdf_path))
    
    return str(pdf_path.resolve())


def get_test_pdf_5_pages() -> str:
    """Get path to 5-page test PDF for quick validation tests.
    
    Creates the PDF if it doesn't exist.
    
    Returns:
        Absolute path to test_5_pages.pdf
    """
    fixture_dir = Path(__file__).parent / "pdfs"
    pdf_path = fixture_dir / "test_5_pages.pdf"
    
    if not pdf_path.exists():
        create_test_pdf(5, str(pdf_path))
    
    return str(pdf_path.resolve())


def get_test_pdf_batch(count: int = 5) -> list[str]:
    """Get paths to multiple test PDFs for batch processing tests.
    
    Args:
        count: Number of test PDFs to generate (default: 5)
    
    Returns:
        List of absolute paths to test PDF files
    """
    fixture_dir = Path(__file__).parent / "pdfs"
    fixture_dir.mkdir(exist_ok=True)
    
    pdf_paths = []
    for i in range(count):
        pdf_path = fixture_dir / f"test_batch_{i}_10_pages.pdf"
        if not pdf_path.exists():
            create_test_pdf(10, str(pdf_path))
        pdf_paths.append(str(pdf_path.resolve()))
    
    return pdf_paths


# Convenience function for cleanup
def cleanup_test_pdfs() -> None:
    """Remove generated test PDFs."""
    fixture_dir = Path(__file__).parent / "pdfs"
    if fixture_dir.exists():
        for pdf_file in fixture_dir.glob("*.pdf"):
            pdf_file.unlink()