
import sys
import shutil
from pathlib import Path
from rich.console import Console

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from parsers import PDFParser

console = Console()

def test_mineru_check():
    """Test if MinerU is detected"""
    console.print("[bold]Testing MinerU Detection...[/bold]")
    parser = PDFParser(extract_images=False)
    
    is_available = parser._check_mineru()
    if is_available:
        console.print("[green]SUCCESS: MinerU detected correctly.[/green]")
        
        # Also check if we can import the specific 2.x API we need
        try:
            from mineru.cli.common import do_parse
            console.print("[green]SUCCESS: mineru.cli.common.do_parse found.[/green]")
        except ImportError as e:
            console.print(f"[red]FAIL: mineru installed but API mismatch: {e}[/red]")
            
    else:
        console.print("[yellow]NOTE: MinerU not detected (ImportError).[/yellow]")

def test_parser_selection_logic():
    """Test logic without running full parse (mocking or checking logs)"""
    console.print("\n[bold]Testing Parser Selection Logic...[/bold]")
    
    parser = PDFParser(extract_images=False)
    
    # Check if methods exist
    if hasattr(parser, "_parse_with_mineru") and hasattr(parser, "_parse_with_pymupdf"):
        console.print("[green]SUCCESS: Methods _parse_with_mineru and _parse_with_pymupdf exist.[/green]")
    else:
        console.print("[red]FAIL: Missing required methods.[/red]")

def main():
    console.print(Panel.fit("[bold blue]MinerU 2.x Integration Verification[/bold blue]"))
    test_mineru_check()
    test_parser_selection_logic()
    
    console.print("\n[bold]Manual Verification Needed:[/bold]")
    console.print("Run: python main.py papers/your_paper.pdf --parser mineru")

if __name__ == "__main__":
    from rich.panel import Panel
    main()
