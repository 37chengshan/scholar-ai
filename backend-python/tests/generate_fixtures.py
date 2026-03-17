"""
Generate test PDF fixtures for testing.

This module creates minimal PDF files programmatically using reportlab
or creates placeholder files if reportlab is not available.
"""

import os
from pathlib import Path


def create_sample_digital_pdf(output_path: Path):
    """
    Create a digital PDF with text layer (no OCR needed).

    This PDF has embedded text and is searchable.
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        c = canvas.Canvas(str(output_path), pagesize=letter)
        width, height = letter

        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, height - 72, "Digital PDF Test Sample")

        # Metadata
        c.setFont("Helvetica", 12)
        c.drawString(72, height - 100, "Author: Test Author")
        c.drawString(72, height - 120, "Date: 2024-01-15")

        # Introduction section
        c.setFont("Helvetica-Bold", 14)
        c.drawString(72, height - 160, "Introduction")

        c.setFont("Helvetica", 11)
        intro_text = """This is a digital PDF test file with embedded text.
The text is directly selectable and searchable without OCR.
This simulates a typical academic paper with a clear text layer."""

        y = height - 180
        for line in intro_text.split('\n'):
            c.drawString(72, y, line)
            y -= 20

        # Methods section
        c.setFont("Helvetica-Bold", 14)
        c.drawString(72, y - 20, "Methods")

        c.setFont("Helvetica", 11)
        methods_text = """We used a standard methodology for testing.
The process involves multiple steps of validation."""

        y -= 40
        for line in methods_text.split('\n'):
            c.drawString(72, y, line)
            y -= 20

        # Results section
        c.setFont("Helvetica-Bold", 14)
        c.drawString(72, y - 20, "Results")

        c.setFont("Helvetica", 11)
        c.drawString(72, y - 40, "The test achieved 95% accuracy.")

        # Conclusion section
        c.setFont("Helvetica-Bold", 14)
        c.drawString(72, y - 80, "Conclusion")

        c.setFont("Helvetica", 11)
        c.drawString(72, y - 100, "Digital PDFs are easier to process.")

        c.save()
        print(f"Created digital PDF: {output_path}")
        return True

    except ImportError:
        print(f"reportlab not available, creating placeholder: {output_path}")
        # Create a placeholder text file
        with open(str(output_path) + '.txt', 'w') as f:
            f.write("Placeholder for digital PDF\n")
        return False


def create_sample_chinese_pdf(output_path: Path):
    """
    Create a PDF with Chinese content for testing Chinese text extraction.
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        # Try to register a Chinese font, fallback to default if not available
        try:
            pdfmetrics.registerFont(TTFont('SimSun', '/System/Library/Fonts/PingFang.ttc'))
            chinese_font = 'SimSun'
        except:
            chinese_font = 'Helvetica'

        c = canvas.Canvas(str(output_path), pagesize=A4)
        width, height = A4

        # Chinese title
        c.setFont(chinese_font, 18)
        c.drawString(72, height - 72, "中文学术论文测试")

        # Author info
        c.setFont(chinese_font, 12)
        c.drawString(72, height - 100, "作者：张三，李四")
        c.drawString(72, height - 120, "单位：中国科学院")

        # Abstract
        c.setFont(chinese_font, 14)
        c.drawString(72, height - 160, "摘要")

        c.setFont(chinese_font, 11)
        abstract = "本文研究了人工智能在医学影像分析中的应用。"
        c.drawString(72, height - 180, abstract)

        # Introduction (引言)
        c.setFont(chinese_font, 14)
        c.drawString(72, height - 220, "1. 引言")

        c.setFont(chinese_font, 11)
        intro = "随着深度学习技术的发展，医学影像诊断取得了显著进展。"
        c.drawString(72, height - 240, intro)

        # Methods (方法)
        c.setFont(chinese_font, 14)
        c.drawString(72, height - 280, "2. 方法")

        c.setFont(chinese_font, 11)
        methods = "我们使用卷积神经网络对医学影像进行分类。"
        c.drawString(72, height - 300, methods)

        # Results (结果)
        c.setFont(chinese_font, 14)
        c.drawString(72, height - 340, "3. 结果")

        c.setFont(chinese_font, 11)
        results = "实验结果显示模型准确率达到了95%。"
        c.drawString(72, height - 360, results)

        # Conclusion (结论)
        c.setFont(chinese_font, 14)
        c.drawString(72, height - 400, "4. 结论")

        c.setFont(chinese_font, 11)
        conclusion = "本研究表明人工智能可以有效辅助医学影像诊断。"
        c.drawString(72, height - 420, conclusion)

        c.save()
        print(f"Created Chinese PDF: {output_path}")
        return True

    except ImportError:
        print(f"reportlab not available, creating placeholder: {output_path}")
        with open(str(output_path) + '.txt', 'w') as f:
            f.write("Placeholder for Chinese PDF\n")
        return False


def create_sample_with_tables(output_path: Path):
    """
    Create a PDF containing tables.
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors

        c = canvas.Canvas(str(output_path), pagesize=letter)
        width, height = letter

        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, height - 72, "Paper with Tables")

        # Introduction
        c.setFont("Helvetica-Bold", 14)
        c.drawString(72, height - 100, "Results")

        c.setFont("Helvetica", 11)
        c.drawString(72, height - 120, "Table 1: Performance Metrics")

        # Simple table representation using text
        c.setFont("Helvetica-Bold", 10)
        c.drawString(72, height - 150, "Model        Accuracy    F1 Score")
        c.drawString(72, height - 165, "-------      --------    --------")

        c.setFont("Helvetica", 10)
        c.drawString(72, height - 180, "CNN          0.95        0.94")
        c.drawString(72, height - 195, "RNN          0.92        0.91")
        c.drawString(72, height - 210, "Transformer  0.97        0.96")

        c.save()
        print(f"Created tables PDF: {output_path}")
        return True

    except ImportError:
        print(f"reportlab not available, creating placeholder: {output_path}")
        with open(str(output_path) + '.txt', 'w') as f:
            f.write("Placeholder for tables PDF\n")
        return False


def create_sample_with_formulas(output_path: Path):
    """
    Create a PDF with mathematical formulas.
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        c = canvas.Canvas(str(output_path), pagesize=letter)
        width, height = letter

        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, height - 72, "Paper with Formulas")

        # Methods section with formulas
        c.setFont("Helvetica-Bold", 14)
        c.drawString(72, height - 100, "Methods")

        c.setFont("Helvetica", 11)
        c.drawString(72, height - 130, "The loss function is defined as:")

        # Formula representation
        c.setFont("Courier", 11)
        c.drawString(100, height - 160, "L = -sum(y * log(p) + (1-y) * log(1-p))")

        c.setFont("Helvetica", 11)
        c.drawString(72, height - 190, "The accuracy is calculated as:")

        c.setFont("Courier", 11)
        c.drawString(100, height - 220, "Accuracy = (TP + TN) / (TP + TN + FP + FN)")

        c.save()
        print(f"Created formulas PDF: {output_path}")
        return True

    except ImportError:
        print(f"reportlab not available, creating placeholder: {output_path}")
        with open(str(output_path) + '.txt', 'w') as f:
            f.write("Placeholder for formulas PDF\n")
        return False


def create_sample_multicolumn(output_path: Path):
    """
    Create a PDF with multi-column layout.
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        c = canvas.Canvas(str(output_path), pagesize=letter)
        width, height = letter

        # Title (spanning both columns)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(72, height - 72, "Multi-Column Academic Paper")

        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, height - 95, "Introduction")

        # Column 1
        c.setFont("Helvetica", 9)
        col1_text = """Medical image analysis has become
increasingly important in healthcare.
Deep learning approaches have shown
promising results in diagnosis tasks.
This paper presents our approach."""

        y = height - 115
        for line in col1_text.split('\n'):
            c.drawString(72, y, line)
            y -= 12

        # Column 2
        col2_text = """We evaluated our method on a dataset
of 10,000 images. The results show
95% accuracy. Our approach outperforms
existing methods significantly."""

        y = height - 115
        for line in col2_text.split('\n'):
            c.drawString(300, y, line)
            y -= 12

        c.save()
        print(f"Created multi-column PDF: {output_path}")
        return True

    except ImportError:
        print(f"reportlab not available, creating placeholder: {output_path}")
        with open(str(output_path) + '.txt', 'w') as f:
            f.write("Placeholder for multi-column PDF\n")
        return False


def create_sample_scanned_placeholder(output_path: Path):
    """
    Create a placeholder for scanned PDF.

    Note: A real scanned PDF would be an image-based PDF without text layer.
    For testing, we create a placeholder that simulates this scenario.
    """
    # For a scanned PDF test, we would ideally have an actual scanned document
    # For now, create a text file describing what it would contain
    with open(str(output_path) + '.README', 'w') as f:
        f.write("""Scanned PDF Placeholder

This represents a scanned document that would require OCR.
In production testing, use an actual scanned PDF image file.

Expected content:
- Image-based PDF without text layer
- Requires OCR to extract text
- Typically 300 DPI or higher
- Would contain:
  * Title: Scanned Research Paper
  * Author: Various authors
  * Content: Academic text requiring OCR processing
""")
    print(f"Created scanned PDF placeholder: {output_path}.README")
    return True


def generate_all_fixtures():
    """Generate all test PDF fixtures."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)

    print("Generating test PDF fixtures...")
    print(f"Output directory: {fixtures_dir}")
    print()

    fixtures = [
        ("sample_digital.pdf", create_sample_digital_pdf, "Digital PDF with text layer"),
        ("sample_scanned.pdf", create_sample_scanned_placeholder, "Scanned PDF (OCR required) - placeholder"),
        ("sample_multicolumn.pdf", create_sample_multicolumn, "Multi-column layout"),
        ("sample_chinese.pdf", create_sample_chinese_pdf, "Chinese content"),
        ("sample_with_tables.pdf", create_sample_with_tables, "PDF with tables"),
        ("sample_with_formulas.pdf", create_sample_with_formulas, "PDF with formulas"),
    ]

    created_count = 0
    for filename, creator, description in fixtures:
        output_path = fixtures_dir / filename
        print(f"Creating: {filename} - {description}")
        if creator(output_path):
            created_count += 1
        print()

    print(f"Generated {created_count}/{len(fixtures)} fixtures")
    print(f"Fixtures directory: {fixtures_dir}")

    # List created files
    print("\nCreated files:")
    for item in fixtures_dir.iterdir():
        print(f"  - {item.name}")


if __name__ == "__main__":
    generate_all_fixtures()
