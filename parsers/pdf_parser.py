"""
PDF Parser Module - Using PyMuPDF with legacy MinerU support detection.

This module provides functionality to:
1. Parse PDF documents with layout analysis
2. Extract text content with LaTeX formulas
3. Extract figures and tables as images (using smart region rendering)
4. Build image mapping for report generation
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
    
    def parse(
        self,
        pdf_path: str,
        output_dir: Optional[Path] = None
    ) -> ParsedDocument:
        """
        Parse a PDF document.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        console.print(f"[blue]📄 Parsing:[/blue] {pdf_path.name}")
        
        # Set up output directory
        if output_dir is None:
            output_dir = pdf_path.parent / f"{pdf_path.stem}_parsed"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Always use PyMuPDF with our enhanced extraction logic
        return self._parse_with_pymupdf(pdf_path, output_dir)
    
    def _parse_with_pymupdf(
        self,
        pdf_path: Path,
        output_dir: Path
    ) -> ParsedDocument:
        """Parse PDF using PyMuPDF with enhanced image extraction"""
        import fitz
        
        console.print("[blue]  → Using PyMuPDF parser (Enhanced)[/blue]")
        
        doc = fitz.open(pdf_path)
        
        # Extract text with improved formatting
        full_text = ""
        for page_num, page in enumerate(doc):
            # Get text blocks for better structure
            blocks = page.get_text("dict")["blocks"]
            page_text = ""
            
            for block in blocks:
                if block["type"] == 0:  # Text block
                    for line in block.get("lines", []):
                        line_text = ""
                        for span in line.get("spans", []):
                            text = span.get("text", "")
                            # Check for potential headers (larger font)
                            if span.get("size", 12) > 14:
                                line_text += f"**{text}**"
                            else:
                                line_text += text
                        page_text += line_text + "\n"
                    page_text += "\n"
            
            full_text += page_text + "\n---\n\n"
        
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
            raw_text=full_text,
            images=images,
            image_map={img.image_id: str(img.saved_path) for img in images}
        )
        
        console.print(f"[green]✓[/green] Parsed successfully")
        console.print(f"  - Content: {len(full_text):,} characters")
        console.print(f"  - Images: {len(images)} extracted")
        
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
            merged_rects = self._merge_rects(image_rects, tolerance_x=70, tolerance_y=30)
            
            # 3. Render each merged region
            for rect in merged_rects:
                # Filter out tiny things (icons, lines)
                if rect.width < 20 or rect.height < 20:
                    continue
                
                # Try to find figure caption below this region
                figure_id, full_caption = self._find_figure_caption(page, rect)
                
                # FILTER: Only keep figures with detected caption (Figure X, Table X, etc.)
                if not figure_id:
                    # Skip regions without proper figure labels
                    continue
                
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
        Look for figure caption text (e.g., 'Figure 1', 'Fig. 2') below the image region.
        
        Args:
            page: PyMuPDF page object
            rect: Rectangle of the image region
            
        Returns:
            Tuple of (figure_id, full_caption):
            - figure_id: e.g., 'Figure 1' or None
            - full_caption: Full caption text for description
        """
        import fitz
        
        # Define search area: below the image, same width, up to 80 pixels down
        # to capture multi-line captions
        search_height = 80
        search_rect = fitz.Rect(
            rect.x0 - 15,           # Wider to catch full caption width
            rect.y1,                # Start from bottom of image
            rect.x1 + 15,           # Wider
            min(rect.y1 + search_height, page.rect.height)
        )
        
        # Extract text from search area
        text = page.get_text("text", clip=search_rect).strip()
        
        if not text:
            return None, None
        
        # Clean up text (remove excessive whitespace)
        text = ' '.join(text.split())
        
        # Look for figure pattern: "Figure 1", "Fig. 2", "Figure 3a", etc.
        patterns = [
            r'(Figure\s*\d+[a-zA-Z]?)',    # "Figure 1", "Figure 3a"
            r'(Fig\.\s*\d+[a-zA-Z]?)',      # "Fig. 1", "Fig.2b"
            r'(Table\s*\d+[a-zA-Z]?)',      # "Table 1", "Table 2"
        ]
        
        figure_id = None
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                figure_id = match.group(1)
                break
        
        # Return figure_id and the full caption text as description
        full_caption = text[:1000] if text else None  # Increased limit for full caption
        
        return figure_id, full_caption

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

    def _extract_plain_text(self, markdown: str) -> str:
        """Extract plain text from markdown"""
        # (Same as before)
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', markdown)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
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
