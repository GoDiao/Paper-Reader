"""
Export Utilities for Paper Reader

Handles conversion of Markdown reports to PDF and DOCX formats.
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


async def write_md_to_pdf(
    markdown_content: str,
    output_path: Path,
    title: str = "Paper Analysis"
) -> Optional[Path]:
    """
    Convert Markdown content to PDF.
    
    Uses markdown-pdf or weasyprint if available.
    Falls back to basic HTML->PDF conversion.
    """
    try:
        import markdown
        from weasyprint import HTML, CSS
        
        # Convert markdown to HTML
        html_content = markdown.markdown(
            markdown_content,
            extensions=['tables', 'fenced_code', 'codehilite', 'toc']
        )
        
        # Wrap in HTML template
        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1, h2, h3, h4 {{ color: #2c3e50; }}
        h1 {{ border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; margin-top: 30px; }}
        code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #3498db; color: white; }}
        tr:nth-child(even) {{ background: #f9f9f9; }}
        blockquote {{ border-left: 4px solid #3498db; margin: 10px 0; padding-left: 15px; color: #666; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>
"""
        
        # Generate PDF
        HTML(string=html_template).write_pdf(str(output_path))
        logger.info(f"PDF generated: {output_path}")
        return output_path
        
    except ImportError:
        logger.warning("weasyprint not installed, PDF export unavailable")
        return None
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return None


async def write_md_to_word(
    markdown_content: str,
    output_path: Path,
    title: str = "Paper Analysis"
) -> Optional[Path]:
    """
    Convert Markdown content to DOCX.
    
    Uses python-docx for Word document generation.
    """
    try:
        from docx import Document
        from docx.shared import Inches, Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        import re
        
        doc = Document()
        
        # Set document properties
        doc.core_properties.title = title
        doc.core_properties.author = "Paper Reader Agent"
        
        # Parse markdown and add to document
        lines = markdown_content.split('\n')
        current_list = None
        in_code_block = False
        code_content = []
        
        for line in lines:
            # Handle code blocks
            if line.startswith('```'):
                if in_code_block:
                    # End code block
                    code_text = '\n'.join(code_content)
                    p = doc.add_paragraph()
                    run = p.add_run(code_text)
                    run.font.name = 'Courier New'
                    run.font.size = Pt(9)
                    p.paragraph_format.left_indent = Inches(0.5)
                    code_content = []
                in_code_block = not in_code_block
                continue
            
            if in_code_block:
                code_content.append(line)
                continue
            
            # Handle headers
            if line.startswith('# '):
                doc.add_heading(line[2:].strip(), level=1)
            elif line.startswith('## '):
                doc.add_heading(line[3:].strip(), level=2)
            elif line.startswith('### '):
                doc.add_heading(line[4:].strip(), level=3)
            elif line.startswith('#### '):
                doc.add_heading(line[5:].strip(), level=4)
            # Handle bullet points
            elif line.strip().startswith('- ') or line.strip().startswith('* '):
                doc.add_paragraph(line.strip()[2:], style='List Bullet')
            # Handle numbered lists
            elif re.match(r'^\d+\.\s', line.strip()):
                text = re.sub(r'^\d+\.\s', '', line.strip())
                doc.add_paragraph(text, style='List Number')
            # Handle blockquotes
            elif line.startswith('>'):
                p = doc.add_paragraph(line[1:].strip())
                p.paragraph_format.left_indent = Inches(0.5)
                p.style = 'Quote'
            # Handle horizontal rules
            elif line.strip() in ['---', '***', '___']:
                doc.add_paragraph('_' * 50)
            # Handle regular paragraphs
            elif line.strip():
                # Clean up markdown formatting
                text = line
                # Bold
                text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
                # Italic
                text = re.sub(r'\*(.+?)\*', r'\1', text)
                # Inline code
                text = re.sub(r'`(.+?)`', r'\1', text)
                # Links
                text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
                
                doc.add_paragraph(text)
        
        # Save document
        doc.save(str(output_path))
        logger.info(f"DOCX generated: {output_path}")
        return output_path
        
    except ImportError:
        logger.warning("python-docx not installed, DOCX export unavailable")
        return None
    except Exception as e:
        logger.error(f"DOCX generation failed: {e}")
        return None


async def create_images_zip(
    images_dir: Path,
    output_path: Path
) -> Optional[Path]:
    """Create a ZIP file containing all extracted images."""
    try:
        import zipfile
        
        if not images_dir.exists():
            return None
        
        image_files = list(images_dir.glob('*.[pP][nN][gG]')) + \
                      list(images_dir.glob('*.[jJ][pP][gG]')) + \
                      list(images_dir.glob('*.[jJ][pP][eE][gG]'))
        
        if not image_files:
            return None
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for img_path in image_files:
                zipf.write(img_path, img_path.name)
        
        logger.info(f"Images ZIP created: {output_path} ({len(image_files)} files)")
        return output_path
        
    except Exception as e:
        logger.error(f"ZIP creation failed: {e}")
        return None
