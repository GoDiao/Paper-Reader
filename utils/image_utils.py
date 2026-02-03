"""
Image Utilities for Paper Reader.

Provides functions for:
- Copying images to output directory
- Creating image galleries
- Image format conversion
"""

import shutil
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console

console = Console()


def copy_images_to_output(
    image_map: Dict[str, str],
    output_dir: Path,
    create_subdir: bool = True
) -> Dict[str, str]:
    """
    Copy images to output directory.
    
    Args:
        image_map: Mapping of image IDs to source paths
        output_dir: Destination directory
        create_subdir: Create 'images' subdirectory
        
    Returns:
        Updated image map with new paths
    """
    if create_subdir:
        images_dir = output_dir / "images"
    else:
        images_dir = output_dir
    
    images_dir.mkdir(parents=True, exist_ok=True)
    
    new_map = {}
    copied = 0
    
    for key, src_path in image_map.items():
        src = Path(src_path)
        if src.exists():
            dest = images_dir / src.name
            
            # Handle filename conflicts
            counter = 1
            while dest.exists() and dest != src:
                dest = images_dir / f"{src.stem}_{counter}{src.suffix}"
                counter += 1
            
            if src != dest:
                shutil.copy2(src, dest)
            
            new_map[key] = str(dest)
            copied += 1
        else:
            console.print(f"[yellow]⚠[/yellow] Source image not found: {src_path}")
            new_map[key] = src_path  # Keep original path
    
    console.print(f"[green]✓[/green] Copied {copied} images to {images_dir}")
    return new_map


def create_image_gallery(
    images: List[Dict],
    columns: int = 2
) -> str:
    """
    Create a Markdown image gallery.
    
    Args:
        images: List of dicts with 'path', 'caption', and optionally 'description'
        columns: Number of columns (for HTML table layout)
        
    Returns:
        Markdown string with image gallery
    """
    if not images:
        return ""
    
    lines = ["## 📷 Figure Gallery\n"]
    
    for img in images:
        path = img.get("path", "")
        caption = img.get("caption", "Image")
        description = img.get("description", "")
        
        lines.append(f"### {caption}\n")
        lines.append(f"![{caption}]({path})\n")
        
        if description:
            lines.append(f"*{description}*\n")
        
        lines.append("")
    
    return "\n".join(lines)


def get_image_dimensions(image_path: str) -> Optional[tuple]:
    """
    Get image dimensions.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Tuple of (width, height) or None if failed
    """
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            return img.size
    except Exception:
        return None


def resize_image(
    image_path: str,
    output_path: str,
    max_width: int = 800,
    max_height: int = 600
) -> bool:
    """
    Resize an image while maintaining aspect ratio.
    
    Args:
        image_path: Source image path
        output_path: Destination path
        max_width: Maximum width
        max_height: Maximum height
        
    Returns:
        True if successful
    """
    try:
        from PIL import Image
        
        with Image.open(image_path) as img:
            # Calculate new size maintaining aspect ratio
            ratio = min(max_width / img.width, max_height / img.height)
            
            if ratio < 1:  # Only resize if larger than max
                new_size = (int(img.width * ratio), int(img.height * ratio))
                resized = img.resize(new_size, Image.Resampling.LANCZOS)
                resized.save(output_path)
            else:
                # Just copy
                shutil.copy2(image_path, output_path)
            
            return True
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to resize image: {e}")
        return False
