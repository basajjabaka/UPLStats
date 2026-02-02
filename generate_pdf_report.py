"""
Script to convert PROJECT_REPORT.md to PDF format using reportlab
"""

import os
import re
from pathlib import Path
from datetime import datetime

def markdown_to_pdf_reportlab(md_file, pdf_file):
    """Convert markdown to PDF using reportlab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        # Read markdown content
        with open(md_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            str(pdf_file),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Container for the 'Flowable' objects
        story = []
        
        # Define styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#00008B'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        h1_style = ParagraphStyle(
            'CustomH1',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a5f7a'),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        )
        
        h2_style = ParagraphStyle(
            'CustomH2',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2e8b57'),
            spaceAfter=8,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        h3_style = ParagraphStyle(
            'CustomH3',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#555555'),
            spaceAfter=6,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
            leading=14
        )
        
        # Helper function to clean and escape text for Paragraph
        def clean_text(text):
            """Clean text and convert markdown to HTML for reportlab."""
            # First, protect code blocks from other markdown processing
            code_blocks = []
            def protect_code(match):
                code_blocks.append(match.group(1))
                return f"__CODEBLOCK_{len(code_blocks)-1}__"
            
            text = re.sub(r'`([^`]+)`', protect_code, text)
            
            # Escape HTML special characters (but not our placeholders)
            text = text.replace('&', '&amp;')
            text = text.replace('<', '&lt;')
            text = text.replace('>', '&gt;')
            
            # Convert markdown bold (but not inside code)
            text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'__(?!CODEBLOCK)([^_]+)__', r'<b>\1</b>', text)
            
            # Convert markdown italic (but not inside code or bold)
            # Only match single * that are not part of **
            text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', text)
            text = re.sub(r'(?<!_)_([^_]+?)_(?!_)', r'<i>\1</i>', text)
            
            # Restore code blocks
            for i, code in enumerate(code_blocks):
                text = text.replace(f"__CODEBLOCK_{i}__", f'<font name="Courier" size="10">{code}</font>')
            
            # Remove links but keep text
            text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
            
            # Remove special unicode characters that might cause issues
            text = text.replace('✅', '[OK]')
            text = text.replace('⚠', '[WARNING]')
            text = text.replace('✓', '[CHECK]')
            
            return text
        
        # Parse markdown and convert to PDF elements
        lines = md_content.split('\n')
        i = 0
        in_code_block = False
        code_block_lines = []
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Handle code blocks
            if stripped.startswith('```'):
                if in_code_block:
                    # End of code block - add as preformatted text
                    if code_block_lines:
                        code_text = '<br/>'.join(code_block_lines)
                        story.append(Paragraph(f'<font name="Courier" size="9">{code_text}</font>', normal_style))
                        story.append(Spacer(1, 0.1*inch))
                    code_block_lines = []
                    in_code_block = False
                else:
                    in_code_block = True
                i += 1
                continue
            
            if in_code_block:
                code_block_lines.append(line.replace('<', '&lt;').replace('>', '&gt;'))
                i += 1
                continue
            
            # Skip empty lines
            if not stripped:
                story.append(Spacer(1, 0.05*inch))
                i += 1
                continue
            
            # Title (first #)
            if stripped.startswith('# ') and i < 5:
                text = clean_text(stripped[2:])
                story.append(Paragraph(text, title_style))
                story.append(Spacer(1, 0.2*inch))
                i += 1
                continue
            
            # H1 (##)
            if stripped.startswith('## '):
                text = clean_text(stripped[3:])
                story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph(text, h1_style))
                story.append(Spacer(1, 0.05*inch))
                i += 1
                continue
            
            # H2 (###)
            if stripped.startswith('### '):
                text = clean_text(stripped[4:])
                story.append(Paragraph(text, h2_style))
                story.append(Spacer(1, 0.03*inch))
                i += 1
                continue
            
            # H3 (####)
            if stripped.startswith('#### '):
                text = clean_text(stripped[5:])
                story.append(Paragraph(text, h3_style))
                story.append(Spacer(1, 0.02*inch))
                i += 1
                continue
            
            # Horizontal rule
            if stripped.startswith('---') or stripped.startswith('==='):
                story.append(Spacer(1, 0.1*inch))
                i += 1
                continue
            
            # List items
            if stripped.startswith('- ') or stripped.startswith('* '):
                text = clean_text(stripped[2:])
                story.append(Paragraph(f"&bull; {text}", normal_style))
                i += 1
                continue
            
            # Numbered list
            if re.match(r'^\d+\.\s', stripped):
                text = re.sub(r'^\d+\.\s', '', stripped)
                text = clean_text(text)
                story.append(Paragraph(f"&bull; {text}", normal_style))
                i += 1
                continue
            
            # Table detection (simple - just format as regular text for now)
            if '|' in stripped and stripped.count('|') >= 2:
                # Skip table separator lines
                if re.match(r'^\|[\s\-\|:]+\|$', stripped):
                    i += 1
                    continue
                # Format table row
                cells = [c.strip() for c in stripped.split('|') if c.strip()]
                if cells:
                    text = ' | '.join([clean_text(c) for c in cells])
                    story.append(Paragraph(text, normal_style))
                i += 1
                continue
            
            # Regular paragraph
            text = clean_text(stripped)
            if text.strip():
                story.append(Paragraph(text, normal_style))
            
            i += 1
        
        # Build PDF
        doc.build(story)
        return True
        
    except ImportError:
        return False
    except Exception as e:
        print(f"Error with reportlab: {e}")
        import traceback
        traceback.print_exc()
        return False


def convert_markdown_to_pdf():
    """Convert markdown report to PDF using available libraries."""
    project_root = Path(__file__).resolve().parent
    md_file = project_root / "PROJECT_REPORT.md"
    pdf_file = project_root / "PROJECT_REPORT.pdf"
    
    if not md_file.exists():
        print(f"Error: {md_file} not found!")
        return False
    
    print("Converting PROJECT_REPORT.md to PDF...")
    print("=" * 60)
    
    # Try reportlab first (pure Python, no system dependencies)
    success = markdown_to_pdf_reportlab(md_file, pdf_file)
    
    if success:
        print(f"Successfully generated PDF: {pdf_file}")
        print("=" * 60)
        return True
    
    print("Failed to generate PDF with reportlab.")
    print("Please check the error messages above.")
    print("=" * 60)
    return False


if __name__ == "__main__":
    convert_markdown_to_pdf()
