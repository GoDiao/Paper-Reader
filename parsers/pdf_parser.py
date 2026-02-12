"""
PDF Parser Module - Using PyMuPDF with enhanced extraction capabilities.

This module provides functionality to:
1. Parse PDF documents with improved layout analysis and structure preservation
2. Extract text content with better formatting (headers, paragraphs, lists)
3. Extract tables and convert to markdown format
4. Identify mathematical formula regions (by font characteristics)
5. Extract figures and tables as images (using smart region rendering)
6. Build image mapping for report generation

Optimizations (v1.2.0+):
- Uses PyMuPDF markdown mode when available for better structure
- Extracts tables using find_tables() and converts to markdown
- Identifies math regions by font characteristics (CMMI, math fonts, flags)
- Improved caption detection (searches above and below images)
- Better handling of large diagrams without captions
- Enhanced text structure preservation (headers, paragraphs)
"""

import os
import re
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from rich.console import Console

console = Console()


@dataclass
class ImageInfo:
    """Information about an extracted image"""
    image_id: str  # e.g., "figure_1", "table_2"
    original_path: Path  # Path where image was saved
    saved_path: Optional[Path] = None  # Path after copying to output
    caption: Optional[str] = None  # Caption text if available
    page_number: int = 0  # Page where the image appears


@dataclass
class ParsedDocument:
    """Parsed PDF document data"""
    title: str = ""
    markdown_content: str = ""  # Full markdown with LaTeX
    raw_text: str = ""  # Plain text without formatting
    images: List[ImageInfo] = field(default_factory=list)
    image_map: Dict[str, str] = field(default_factory=dict)  # "Figure 1" -> path
    metadata: Dict = field(default_factory=dict)


class PDFParser:
    """
    PDF Document Parser using PyMuPDF (primary).
    Implements smart image extraction by merging overlapping image layers.
    """
    
    def __init__(
        self,
        use_gpu: bool = True,
        extract_images: bool = True,
        image_format: str = "png",
        prefer_mineru: bool = False  # Deprecated but kept for compatibility
    ):
        """
        Initialize PDF Parser.
        """
        self.use_gpu = use_gpu
        self.extract_images = extract_images
        self.image_format = image_format
        
        # We now primarily use PyMuPDF because MinerU CLI requires complex config
        self.pymupdf_available = self._check_pymupdf()
        
        if not self.pymupdf_available:
            raise ImportError("PyMuPDF (fitz) is not installed. Run: pip install pymupdf")
    
    def _check_pymupdf(self) -> bool:
        """Check if PyMuPDF is installed"""
        try:
            import fitz
            console.print("[green]✓[/green] PyMuPDF available")
            return True
        except ImportError:
            console.print("[dim]PyMuPDF not installed[/dim]")
            return False
    
    def _check_mineru(self) -> bool:
        """Check if MinerU (mineru package) is installed"""
        try:
            import mineru
            console.print("[green]✓[/green] MinerU (mineru) available")
            return True
        except ImportError:
            return False

    def parse(
        self,
        pdf_path: str,
        output_dir: Optional[Path] = None,
        parser_backend: str = "auto"  # "auto", "mineru", "pymupdf"
    ) -> ParsedDocument:
        """
        Parse a PDF document with specified backend strategy.
        
        Strategies:
        - "pymupdf": Force use of PyMuPDF (fast, robust).
        - "mineru": Force use of MinerU (slow, better layout). Error if fails.
        - "auto": Try MinerU if available. If it fails or not installed, fallback to PyMuPDF.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        console.print(f"[blue]📄 Parsing:[/blue] {pdf_path.name}")
        console.print(f"[dim]Backend strategy: {parser_backend}[/dim]")
        
        # Set up output directory
        if output_dir is None:
            output_dir = pdf_path.parent / f"{pdf_path.stem}_parsed"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Strategy Logic
        if parser_backend == "pymupdf":
            return self._parse_with_pymupdf(pdf_path, output_dir)
            
        elif parser_backend == "mineru":
            # Strict mode: fail if MinerU fails
            if not self._check_mineru():
                raise ImportError("MinerU selected but not installed. Install with `pip install mineru`")
            return self._parse_with_mineru(pdf_path, output_dir)
            
        elif parser_backend == "auto":
            # Intelligent mode: Try MinerU, fallback to PyMuPDF
            if self._check_mineru():
                try:
                    return self._parse_with_mineru(pdf_path, output_dir)
                except Exception as e:
                    console.print(f"[yellow]⚠ MinerU parsing failed: {e}[/yellow]")
                    console.print("[yellow]⚠ Falling back to PyMuPDF...[/yellow]")
                    return self._parse_with_pymupdf(pdf_path, output_dir)
            else:
                # MinerU not installed, silent fallback
                return self._parse_with_pymupdf(pdf_path, output_dir)
        
        else:
            console.print(f"[yellow]Unknown backend '{parser_backend}', defaulting to PyMuPDF[/yellow]")
            return self._parse_with_pymupdf(pdf_path, output_dir)
    
    def _parse_with_pymupdf(
        self,
        pdf_path: Path,
        output_dir: Path
    ) -> ParsedDocument:
        """Parse PDF using PyMuPDF with enhanced extraction (tables, formulas, structure)"""
        import fitz
        
        console.print("[blue]  → Using PyMuPDF parser (Enhanced)[/blue]")
        
        doc = fitz.open(pdf_path)
        page_count = len(doc)  # Save page count before closing
        
        # Extract text with improved formatting and structure
        full_text_parts = []
        plain_text_parts = []
        table_count = 0
        total_math_regions = 0
        
        for page_num, page in enumerate(doc):
            page_markdown = []
            page_plain = []
            
            # Try to use markdown mode if available (PyMuPDF 1.23+)
            try:
                # Check if markdown mode is available
                markdown_text = page.get_text("markdown")
                if markdown_text and markdown_text.strip():
                    # Markdown mode provides better structure
                    page_markdown.append(markdown_text)
                    page_plain.append(page.get_text("text"))
                else:
                    # Fallback to structured extraction
                    page_markdown.append(self._extract_structured_text(page))
                    page_plain.append(page.get_text("text"))
            except (AttributeError, TypeError):
                # Fallback for older PyMuPDF versions
                page_markdown.append(self._extract_structured_text(page))
                page_plain.append(page.get_text("text"))
            
            # Extract tables and convert to markdown
            tables = self._extract_tables(page)
            if tables:
                table_count += len(tables)
                for i, table_md in enumerate(tables, 1):
                    page_markdown.append(f"\n\n### Table {table_count - len(tables) + i}\n\n{table_md}\n")
            
            # Identify and mark mathematical formula regions
            math_regions = self._identify_math_regions(page)
            if math_regions:
                total_math_regions += len(math_regions)
                # Note: We can't extract LaTeX directly, but we mark these regions
                # The LLM can still process the text representation
            
            # Combine page content
            page_content = "\n".join(page_markdown)
            if page_content.strip():
                full_text_parts.append(page_content)
                plain_text_parts.append("\n".join(page_plain))
            
            # Add page separator (except for last page)
            if page_num < len(doc) - 1:
                full_text_parts.append("\n---\n\n")
        
        full_text = "\n".join(full_text_parts)
        plain_text = "\n\n".join(plain_text_parts)
        
        # Extract images using smart region rendering
        # Note: output_dir is expected to be the images directory
        images = []
        
        if self.extract_images:
            console.print("[blue]  → Extracting images (smart region rendering)...[/blue]")
            images = self._extract_images_by_rendering(doc, output_dir)
        
        doc.close()
        
        doc_data = ParsedDocument(
            title=self._extract_title(full_text),
            markdown_content=full_text,
            raw_text=plain_text,
            images=images,
            image_map={img.image_id: str(img.saved_path) for img in images},
            metadata={
                "table_count": table_count,
                "page_count": page_count,
                "math_regions_detected": total_math_regions
            }
        )
        
        console.print(f"[green]✓[/green] Parsed successfully")
        console.print(f"  - Content: {len(full_text):,} characters")
        console.print(f"  - Images: {len(images)} extracted")
        if table_count > 0:
            console.print(f"  - Tables: {table_count} extracted")
        
        return doc_data
    
    
    def _parse_with_mineru(
        self,
        pdf_path: Path,
        output_dir: Path
    ) -> ParsedDocument:
        """
        Parse PDF using MinerU (Magic-PDF) 2.x API.
        Uses mineru.cli.common.do_parse for integration.
        """
        console.print("[blue]  → Using MinerU parser (Pipeline Mode)[/blue]")
        
        # Set HuggingFace and ModelScope cache to local ckpt directory
        import os
        ckpt_path = Path(__file__).parent.parent / "MinerU" / "ckpt"
        ckpt_path.mkdir(parents=True, exist_ok=True)
        os.environ["HF_HOME"] = str(ckpt_path.resolve())
        os.environ["MODELSCOPE_CACHE"] = str(ckpt_path.resolve())
        
        try:
            from mineru.cli.common import do_parse, read_fn
        except ImportError:
            raise ImportError("MinerU 2.x not installed. Please install with `pip install mineru`")

        # Prepare parameters
        pdf_path_obj = Path(pdf_path)
        file_name = pdf_path_obj.stem
        # Ensure output directory is ready (MinerU creates a subdir based on filename)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        console.print(f"[dim]  Reading file: {file_name}[/dim]")
        pdf_bytes = read_fn(pdf_path_obj)
        
        # Execute MinerU Pipeline
        # This will generate output_dir/{file_name}/{parse_method}/{file_name}.md
        # Defaulting to 'pipeline' backend (CPU friendly) and 'auto' method
        try:
            do_parse(
                output_dir=str(output_dir),
                pdf_file_names=[file_name],
                pdf_bytes_list=[pdf_bytes],
                p_lang_list=["en"], # Default usually English
                backend="pipeline",
                parse_method="auto",
                f_dump_md=True,
                f_dump_middle_json=False,
                f_dump_model_output=False,
                f_dump_orig_pdf=False,
                f_dump_content_list=False,
                start_page_id=0,
                end_page_id=None
            )
        except Exception as e:
            raise RuntimeError(f"MinerU internal error: {e}")

        # Locate Output
        # MinerU output structure: {output_dir}/{file_name}/auto/{file_name}.md
        # Note: 'auto' is the parse_method. If it chose 'txt' or 'ocr', folder name changes.
        # We need to find where it landed.
        mineru_sub_dir = output_dir / file_name
        md_file = None
        images_dir = None
        
        if mineru_sub_dir.exists():
            # Search for the .md file recursively in the subdir
            found_mds = list(mineru_sub_dir.rglob(f"{file_name}.md"))
            if found_mds:
                md_file = found_mds[0]
                # Usually images are in 'images' folder alongside the .md
                images_dir = md_file.parent / "images"
        
        if not md_file or not md_file.exists():
            raise FileNotFoundError("MinerU finished but output Markdown file was not found.")
            
        # Read Content
        with open(md_file, "r", encoding="utf-8") as f:
            md_content = f.read()

        # =========================================================
        # Post-Processing: Rename Images & Filter
        # =========================================================
        import re
        import shutil
        
        # Target directory for semantic images 
        # output_dir here IS the images directory from caller
        target_images_dir = output_dir 
        target_images_dir.mkdir(parents=True, exist_ok=True)
        
        # Pattern: ![](images/hash.jpg) ... Figure X: Caption
        # We look for the image link followed by a Figure caption nearby
        # MinerU usually puts caption immediately after image
        pattern = re.compile(r'!\[(.*?)\]\((.*?)\)\s*\n\s*(Figure\s*(\d+).*?)(?=\n|$)', re.IGNORECASE)
        
        console.print(f"[dim]  Searching for image captions in {len(md_content)} chars...[/dim]")
        
        final_images = []
        processed_hashes = set()
        
        def replace_match(match):
            alt_text = match.group(1)
            original_rel_path = match.group(2) # e.g. "images/hash.jpg"
            caption_line = match.group(3)      # e.g. "Figure 1: Comparison..."
            fig_num = match.group(4)           # e.g. "1"
            
            # Extract hash filename
            # MinerU output image path is relative to MD file
            original_path_obj = md_file.parent / original_rel_path
            
            if not original_path_obj.exists():
                return match.group(0) # Keep as is if file missing
            
            # Filter: If filename or caption implies it's NOT a figure (e.g. Table)
            # But the regex requires "Figure" in caption, so we are somewhat safe.
            # Just separate check if needed.
                
            # Define new name
            new_filename = f"Figure_{fig_num}.jpg"
            target_path = target_images_dir / new_filename
            
            # Copy and rename
            try:
                shutil.copy2(original_path_obj, target_path)
                processed_hashes.add(original_path_obj.name)
                
                # Add to result list
                # Add to result list
                final_images.append(ImageInfo(
                    image_id=f"fig_{fig_num}",
                    page_number=0, # MinerU doesn't easily give page num in MD, default to 0
                    caption=caption_line,
                    saved_path=str(target_path),
                    original_path=original_path_obj
                ))
                
                # Relativize for Markdown (assuming MD is in output_dir)
                # Let's use `images/Figure_1.jpg`
                return f"![{alt_text}](images/{new_filename})\n{caption_line}"
                
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to process image {original_path_obj}: {e}[/yellow]")
                return match.group(0)

        # Apply replacement to markdown content
        new_md_content = pattern.sub(replace_match, md_content)
        
        # Construct ParsedDocument
        doc_data = ParsedDocument(
            title=self._extract_title(new_md_content),
            markdown_content=new_md_content,
            raw_text=self._extract_plain_text(new_md_content),
            images=final_images,
            image_map={img.image_id: str(img.saved_path) for img in final_images},
            metadata={
                "parser": "mineru",
                "version": "2.0+",
                "backend": "pipeline"
            }
        )
        
        console.print(f"[green]✓[/green] MinerU parsing complete")
        console.print(f"  - Content: {len(md_content):,} characters")
        console.print(f"  - Images: {len(final_images)} extracted")
        
        return doc_data
    
    def _extract_images_by_rendering(
        self,
        doc,  # fitz.Document
        images_dir: Path
    ) -> List[ImageInfo]:
        """
        Extract images by finding image regions and rendering them.
        This handles layered images (SMASK) and sliced images by merging overlapping rects.
        """
        import fitz
        
        images = []
        figure_count = 0
        
        for page_num, page in enumerate(doc):
            # 1. Identify all image candidates (rects)
            image_rects = []
            
            # Get all image blocks
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_IMAGES)["blocks"]
            for block in blocks:
                if block["type"] == 1:  # Image
                    image_rects.append(fitz.Rect(block["bbox"]))
            
            # Also check raw images as backup (sometimes text dict misses them)
            if not image_rects:
                for img in page.get_images():
                    try:
                        rects = page.get_image_rects(img[0])
                        image_rects.extend(rects)
                    except:
                        pass
            
            # NEW: Detect vector drawings (charts, diagrams, plots)
            # Many academic figures are drawn with vector paths
            drawings = page.get_drawings()
            if drawings:
                # Group drawings into clusters (they're often scattered)
                drawing_rects = []
                for drawing in drawings:
                    if 'rect' in drawing:
                        r = drawing['rect']
                        # Only consider substantial drawings (not tiny decorations)
                        if r.width > 10 and r.height > 10:
                            drawing_rects.append(r)
                
                # Merge drawing rects into larger regions
                if drawing_rects:
                    # Use aggressive merging for drawings (they're often fragmented)
                    merged_drawings = self._merge_rects(drawing_rects, tolerance_x=50, tolerance_y=50)
                    # Add to image_rects for final processing
                    image_rects.extend(merged_drawings)
            
            if not image_rects:
                continue

            # 2. Merge overlapping or close rectangles
            # This is critical for "sliced" images
            # Use higher horizontal tolerance for side-by-side fragments
            merged_rects = self._merge_rects(image_rects, tolerance_x=50, tolerance_y=30)
            
            # 3. Render each merged region
            for rect in merged_rects:
                # Filter out tiny things (icons, lines)
                if rect.width < 20 or rect.height < 20:
                    continue
                
                # Try to find figure caption below or above this region
                figure_id, full_caption = self._find_figure_caption(page, rect)
                
                # If no caption found, check if this might be a table
                # Tables are often large rectangular regions without captions
                if not figure_id:
                    # Check if this looks like a table (large, rectangular, contains text)
                    table_text = page.get_text("text", clip=rect).strip()
                    if len(table_text) > 50 and rect.width > 200 and rect.height > 100:
                        # Might be a table - try to extract it
                        try:
                            # Check if find_tables can detect it
                            tables = page.find_tables(clip=rect)
                            if tables:
                                # This is a table, skip image extraction (tables are handled in text extraction)
                                continue
                        except:
                            pass
                    
                    # Skip regions without proper figure labels (unless they're very large)
                    # Allow large regions even without captions (might be important diagrams)
                    if rect.width * rect.height < 50000:  # Less than ~224x224 pixels
                        continue
                    else:
                        # Large region without caption - assign a generic ID
                        figure_id = f"Figure_{figure_count + 1}"
                        figure_count += 1
                        full_caption = f"Large diagram or figure (no caption detected)"
                
                # Extract figure number from caption (e.g., "Figure 1" -> "Figure_1")
                img_id = figure_id.replace(" ", "_").replace(".", "")
                img_id = re.sub(r'[^a-zA-Z0-9_]', '', img_id)[:30]  # Clean up
                
                img_path = images_dir / f"{img_id}.png"
                
                try:
                    # Expand clip to capture surrounding context (margins, captions, etc.)
                    margin = 15  # pixels to expand in each direction
                    clip = rect + fitz.Rect(-margin, -margin, margin, margin)
                    clip.intersect(page.rect)  # Keep within page bounds
                    
                    # Render with high quality (2x zoom)
                    mat = fitz.Matrix(2, 2)
                    pix = page.get_pixmap(matrix=mat, clip=clip)
                    
                    # Save as PNG
                    pix.save(str(img_path))
                    
                    images.append(ImageInfo(
                        image_id=img_id,
                        original_path=img_path,
                        saved_path=img_path,
                        page_number=page_num + 1,
                        caption=full_caption  # Store full description
                    ))
                except Exception as e:
                    console.print(f"[yellow]Warning: Failed to render image region {rect}: {e}[/yellow]")
                    continue
        
        return images

    def _find_figure_caption(self, page, rect) -> Tuple[Optional[str], Optional[str]]:
        """
        Look for figure caption text (e.g., 'Figure 1', 'Fig. 2') below or above the image region.
        Improved to search both below and above (some papers put captions above).
        
        Args:
            page: PyMuPDF page object
            rect: Rectangle of the image region
            
        Returns:
            Tuple of (figure_id, full_caption):
            - figure_id: e.g., 'Figure 1' or None
            - full_caption: Full caption text for description
        """
        import fitz
        
        # Search areas: below (common) and above (less common)
        search_height = 100  # Increased for multi-line captions
        search_width_expand = 30  # Wider search area
        
        search_areas = [
            # Below image (most common)
            fitz.Rect(
                rect.x0 - search_width_expand,
                rect.y1,
                rect.x1 + search_width_expand,
                min(rect.y1 + search_height, page.rect.height)
            ),
            # Above image (some papers)
            fitz.Rect(
                rect.x0 - search_width_expand,
                max(0, rect.y0 - search_height),
                rect.x1 + search_width_expand,
                rect.y0
            )
        ]
        
        best_match = None
        best_caption = None
        
        for search_rect in search_areas:
            # Extract text from search area
            text = page.get_text("text", clip=search_rect).strip()
            
            if not text:
                continue
            
            # Clean up text (remove excessive whitespace)
            text = ' '.join(text.split())
            
            # Look for figure pattern: "Figure 1", "Fig. 2", "Figure 3a", etc.
            # Also support "Fig 1" (without period) and "Figure 1:" (with colon)
            patterns = [
                r'(Figure\s*\d+[a-zA-Z]?)',           # "Figure 1", "Figure 3a"
                r'(Fig\.?\s*\d+[a-zA-Z]?)',            # "Fig. 1", "Fig 2", "Fig.2b"
                r'(Table\s*\d+[a-zA-Z]?)',             # "Table 1", "Table 2"
                r'(Algorithm\s*\d+[a-zA-Z]?)',         # "Algorithm 1"
                r'(Equation\s*\d+[a-zA-Z]?)',          # "Equation 1"
            ]
            
            figure_id = None
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    figure_id = match.group(1)
                    break
            
            if figure_id:
                # Prefer matches that are closer to the image
                if best_match is None:
                    best_match = figure_id
                    best_caption = text[:1000]  # Limit caption length
        
        return best_match, best_caption

    def _merge_rects(self, rects, tolerance_x=80.0, tolerance_y=30.0):
        """
        Merge rectangles that overlap or are very close.
        Uses iterative clustering to handle complex fragmented images.
        
        Args:
            rects: List of rectangles to merge
            tolerance_x: Horizontal tolerance (pixels) - higher for side-by-side fragments
            tolerance_y: Vertical tolerance (pixels) - lower for stacked elements
        """
        if not rects:
            return []
            
        import fitz
        
        # Convert to list and make copies
        rects = [fitz.Rect(r) for r in rects]
        
        # Iteratively merge until no more merges possible
        changed = True
        iteration = 0
        max_iterations = 10
        
        while changed and iteration < max_iterations:
            changed = False
            iteration += 1
            
            new_rects = []
            used = set()
            
            for i, rect1 in enumerate(rects):
                if i in used:
                    continue
                    
                # Start a cluster with this rect
                cluster = rect1
                used.add(i)
                
                # Find all rects that should merge with this cluster
                for j, rect2 in enumerate(rects):
                    if j in used or i == j:
                        continue
                    
                    # Check if rect2 is close to current cluster
                    # Use different tolerances for x and y directions
                    expanded = cluster + fitz.Rect(-tolerance_x, -tolerance_y, tolerance_x, tolerance_y)
                    if expanded.intersects(rect2):
                        cluster = cluster | rect2  # Union
                        used.add(j)
                        changed = True
                
                new_rects.append(cluster)
            
            rects = new_rects
        
        return rects

    def _extract_title(self, markdown: str) -> str:
        """Try to extract paper title from markdown"""
        # (Same as before)
        match = re.search(r'^#\s+(.+)$', markdown, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        match = re.search(r'^\*\*(.+?)\*\*', markdown, re.MULTILINE)
        if match:
            return match.group(1).strip()[:200]
        
        lines = markdown.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('!') and len(line) > 10:
                return line[:200]
        
        return "Untitled Paper"

    def _extract_structured_text(self, page) -> str:
        """
        Extract text with better structure preservation.
        Improved version that maintains paragraphs, lists, and formatting.
        """
        import fitz
        
        blocks = page.get_text("dict")["blocks"]
        page_text_parts = []
        current_paragraph = []
        
        for block in blocks:
            if block["type"] != 0:  # Skip non-text blocks
                continue
            
            block_text = ""
            is_header = False
            font_sizes = []
            
            for line in block.get("lines", []):
                line_text = ""
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    font_size = span.get("size", 12)
                    font_sizes.append(font_size)
                    
                    # Detect headers (larger font, often bold)
                    if font_size > 14 or (font_size > 12 and span.get("flags", 0) & 16):  # 16 = bold flag
                        is_header = True
                    
                    line_text += text
                
                if line_text.strip():
                    current_paragraph.append(line_text.strip())
            
            # Determine if this is a header based on font size
            avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 12
            
            if current_paragraph:
                para_text = " ".join(current_paragraph)
                
                # Format as header if detected
                if is_header and avg_font_size > 14 and len(para_text) < 200:
                    # Likely a section header
                    page_text_parts.append(f"\n## {para_text}\n")
                elif para_text.strip():
                    # Regular paragraph
                    page_text_parts.append(para_text)
                
                current_paragraph = []
        
        return "\n\n".join(page_text_parts)
    
    def _extract_tables(self, page) -> List[str]:
        """
        Extract tables from page and convert to markdown format.
        
        Returns:
            List of markdown-formatted table strings
        """
        import fitz
        
        tables = []
        
        try:
            # PyMuPDF's find_tables() method (available in recent versions)
            found_tables = page.find_tables()
            
            for table in found_tables:
                try:
                    # Convert table to markdown
                    table_md = table.to_markdown()
                    if table_md and table_md.strip():
                        tables.append(table_md)
                except (AttributeError, Exception) as e:
                    # Fallback: try to extract table manually
                    console.print(f"[dim]  Table extraction fallback: {e}[/dim]")
                    # Could implement manual table extraction here if needed
                    pass
        except (AttributeError, Exception):
            # find_tables() not available in this PyMuPDF version
            pass
        
        return tables
    
    def _identify_math_regions(self, page) -> List[Dict]:
        """
        Identify mathematical formula regions by font characteristics.
        
        Math formulas in PDFs often use:
        - Fonts starting with "CMMI" (Computer Modern Math Italic)
        - Special flags (value 6 vs 4 for regular text)
        - Different character spacing
        
        Returns:
            List of dicts with math region info (for future enhancement)
        """
        import fitz
        
        math_regions = []
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if block["type"] != 0:
                continue
            
            for line in block.get("lines", []):
                math_spans = []
                for span in line.get("spans", []):
                    font_name = span.get("font", "").lower()
                    flags = span.get("flags", 0)
                    
                    # Heuristic: math fonts often contain "math", "cmmi", "symbol"
                    # or have special flags
                    is_math = (
                        "math" in font_name or
                        "cmmi" in font_name or
                        "symbol" in font_name or
                        (flags == 6)  # Special flag for math
                    )
                    
                    if is_math:
                        math_spans.append({
                            "text": span.get("text", ""),
                            "bbox": span.get("bbox", []),
                            "font": font_name
                        })
                
                if math_spans:
                    # Could mark these regions for special processing
                    math_regions.append({
                        "spans": math_spans,
                        "line_bbox": line.get("bbox", [])
                    })
        
        return math_regions
    
    def _extract_plain_text(self, markdown: str) -> str:
        """Extract plain text from markdown"""
        # Remove markdown formatting
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', markdown)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'#{1,6}\s+', '', text)  # Remove headers
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Remove bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Remove italic
        text = re.sub(r'`([^`]+)`', r'\1', text)  # Remove code
        return text

    def copy_images_to_output(
        self,
        images: List[ImageInfo],
        output_images_dir: Path
    ) -> None:
        """Copy extracted images to final output directory"""
        output_images_dir.mkdir(parents=True, exist_ok=True)
        
        for img in images:
            if img.original_path and img.original_path.exists():
                dest = output_images_dir / img.original_path.name
                shutil.copy2(img.original_path, dest)
                img.saved_path = dest

    def generate_figure_index(
        self,
        images: List[ImageInfo],
        output_dir: Path
    ) -> Path:
        """
        Generate an index document describing all extracted figures.
        Creates both JSON (for programmatic access) and Markdown (for reading).
        
        Args:
            images: List of extracted ImageInfo objects
            output_dir: Directory to save the index files
            
        Returns:
            Path to the generated JSON index file
        """
        # Build index data
        index_data = {
            "figures": [],
            "total_count": len(images)
        }
        
        for img in images:
            figure_entry = {
                "id": img.image_id,
                "file": img.original_path.name if img.original_path else None,
                "path": str(img.saved_path) if img.saved_path else None,
                "page": img.page_number,
                "caption": img.caption
            }
            index_data["figures"].append(figure_entry)
        
        # Save JSON index
        json_path = output_dir / "figure_index.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        # Save Markdown index for human reading
        md_path = output_dir / "figure_index.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Figure Index\n\n")
            f.write(f"Total figures extracted: {len(images)}\n\n")
            f.write("---\n\n")
            
            for img in images:
                f.write(f"## {img.image_id}\n\n")
                f.write(f"- **File**: `{img.original_path.name if img.original_path else 'N/A'}`\n")
                f.write(f"- **Page**: {img.page_number}\n")
                if img.caption:
                    f.write(f"- **Caption**: {img.caption}\n")
                f.write("\n")
        
        console.print(f"[green]✓[/green] Generated figure index: {json_path.name}")
        
        return json_path
