import os
from pathlib import Path
from typing import Dict, Any
from rich.console import Console

console = Console()

class ReportGenerator:
    """Generates final reports in Markdown format."""
    
    def generate(
        self,
        analysis_report: str,
        image_map: Dict[str, str],
        title: str,
        output_path: Path,
        images_output_dir: Path
    ) -> str:
        """
        Generate structured Markdown report.
        
        Args:
            analysis_report: Content of the analysis report
            image_map: Mapping of figure IDs to image paths
            title: Paper title
            output_path: Path to save the Markdown file
            images_output_dir: Directory containing extracted images
            
        Returns:
            str: The final markdown content
        """
        # 1. Clean up constraints/artifacts from LLM
        final_md = self._clean_markdown(analysis_report)
        
        # 2. Embed images
        final_md = self._embed_images(final_md, image_map)
        
        # 3. Add title if missing
        # Only add title if content is not empty
        if final_md and title and not final_md.startswith(f"#"):
            final_md = f"# 📄 {title}\n\n{final_md}"
            
        # 4. Save Markdown file
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_md)
            console.print(f"[green]✓[/green] Saved Markdown report: {output_path}")
        except Exception as e:
            console.print(f"[red]✗ Error saving Markdown:[/red] {e}")
            
        return final_md
    
    def _embed_images(self, text: str, image_map: Dict[str, str]) -> str:
        """
        Replace <INSERT_FIGURE: ID ...> tags with actual markdown images.
        
        Args:
            text: Markdown content with tags
            image_map: Mapping of figure IDs to image paths
            
        Returns:
            str: Markdown with embedded images
        """
        import re
        
        if not image_map:
            return text
            
        def replace_tag(match):
            content = match.group(1)
            # content format: "Figure_X - reason" or just "Figure_X"
            parts = content.split(' - ', 1)
            fig_id = parts[0].strip()
            caption = parts[1].strip() if len(parts) > 1 else ""
            
            # Find image path
            img_path = image_map.get(fig_id)
            
            # Fallback lookup strategies
            if not img_path:
                # 1. Try lowercase
                img_path = image_map.get(fig_id.lower())
            
            if not img_path:
                # 2. Try replacing spaces with underscores
                img_path = image_map.get(fig_id.replace(' ', '_'))
                
            if not img_path:
                # 3. Try standardizing "Figure X" -> "fig_x"
                # Handle variations: "Figure 1", "Figure_1", "Fig. 1", "Fig-1"
                import re
                match = re.search(r'(?:Figure|Fig)[_\s.-]*(\d+)', fig_id, re.IGNORECASE)
                if match:
                    num = match.group(1)
                    img_path = image_map.get(f"fig_{num}")
            
            if not img_path:
                return f"> *[Figure {fig_id} not found]*"
                
            # Create relative path for markdown if possible
            try:
                # Assuming images are in 'images/' subdir relative to report
                # and img_path matches that structure
                img_path_obj = Path(img_path)
                rel_path = f"images/{img_path_obj.name}"
            except:
                rel_path = img_path
            
            # Construct markdown image
            # ![Caption](path)
            # *Caption*
            return f"\n![{fig_id}]({rel_path})\n\n*{caption or fig_id}*\n"
            
        # Pattern: <INSERT_FIGURE: ...>
        pattern = r'<INSERT_FIGURE:\s*([^>]+)>'
        return re.sub(pattern, replace_tag, text)
    
    def _clean_markdown(self, text: str) -> str:
        """Clean up markdown content (remove code blocks, extra newlines)."""
        if not text:
            return ""
            
        # Remove embedding code blocks if LLM wrapped whole output
        # e.g. ```markdown ... ```
        clean_text = text.strip()
        if clean_text.startswith("```markdown"):
            clean_text = clean_text.replace("```markdown", "", 1)
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
        elif clean_text.startswith("```"):
            clean_text = clean_text.replace("```", "", 1)
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
        
        return clean_text.strip()
