#!/usr/bin/env python
"""
Paper Reader Agent - Main Entry Point

A CLI tool for automated academic paper analysis with:
- PDF parsing with LaTeX formula extraction
- Structured analysis (Background → Problem → Method → Experiments → Conclusions)
- Detailed formula derivation
- Figure extraction and embedding
- Markdown report generation

Modes:
- simple: Basic dual-role analysis (Architect + Math Deriver)
- hierarchical: Advanced 1+3+1 agent team with parallel execution

Usage:
    python main.py paper.pdf                          # Simple mode (default)
    python main.py paper.pdf --mode hierarchical      # Hierarchical mode
    python main.py paper.pdf -o ./analysis            # Custom output dir
    python main.py paper.pdf --provider openai        # Use OpenAI

Supports:
    - DeepSeek API (default)
    - OpenAI API (gpt-4o, gpt-4-turbo, etc.)
"""

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from parsers import PDFParser, ParsedDocument
from agents import ReasoningAgent, HierarchicalOrchestrator
from generators import ReportGenerator
from utils import copy_images_to_output

console = Console()


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Paper Reader Agent - Automated academic paper analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py ConceptMoE.pdf -o ./output -v
  python main.py paper.pdf --mode hierarchical
  python main.py paper.pdf -o ./my_analysis
  python main.py paper.pdf --provider openai --model gpt-4o
        """
    )
    
    parser.add_argument(
        "pdf_path",
        type=str,
        help="Path to the PDF file to analyze"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="./output",
        help="Output directory for analysis results (default: ./output)"
    )
    
    parser.add_argument(
        "--mode",
        type=str,
        choices=["simple", "hierarchical"],
        default="hierarchical",
        help="Analysis mode: 'simple' (2 agents) or 'hierarchical' (5 agents, parallel)"
    )
    
    parser.add_argument(
        "--provider",
        type=str,
        choices=["openai", "deepseek"],
        default="deepseek",
        help="LLM API provider (default: deepseek)"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name (default: deepseek-chat for DeepSeek, gpt-4o for OpenAI)"
    )
    
    parser.add_argument(
        "--language",
        type=str,
        choices=["en", "zh"],
        default="en",
        help="Output language: 'en' (English) or 'zh' (Chinese)"
    )
    
    parser.add_argument(
        "--api-key",
        type=str,
        default="",
        help="API key (overrides environment variable)"
    )
    
    parser.add_argument(
        "--no-gpu",
        action="store_true",
        help="Disable GPU acceleration for PDF parsing"
    )
    
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Skip image extraction from PDF"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Number of parallel workers for hierarchical mode (default: 3)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--parser",
        type=str,
        choices=["auto", "pymupdf", "mineru"],
        default="auto",
        help="PDF parser backend: 'pymupdf' (fast, default) or 'mineru' (high-fidelity, requires setup)"
    )

    return parser.parse_args()


def run_simple_mode(args, parsed_doc, model, images_dir, output_dir):
    """Run simple dual-role analysis mode"""
    console.print("\n[bold cyan]Mode: Simple (Architect + Math Deriver)[/bold cyan]")
    
    agent = ReasoningAgent(
        provider=args.provider,
        model=model,
        api_key=args.api_key
    )
    
    analysis = agent.analyze_paper(
        content=parsed_doc.markdown_content,
        title=parsed_doc.title,
        images=parsed_doc.images
    )
    
    console.print(f"[green]✓[/green] Domain: {analysis.domain}")
    console.print(f"[green]✓[/green] Figures suggested: {len(analysis.figure_suggestions)}")
    
    # Save verbose outputs
    if args.verbose:
        with open(output_dir / "raw_architect.md", "w", encoding="utf-8") as f:
            f.write(analysis.raw_architect_output)
        if analysis.raw_math_output:
            with open(output_dir / "raw_math.md", "w", encoding="utf-8") as f:
                f.write(analysis.raw_math_output)
    
    return analysis.full_report, analysis.figure_suggestions


def run_hierarchical_mode(args, parsed_doc, model, images_dir, output_dir):
    """Run hierarchical 1+3+1 agent team mode"""
    console.print("\n[bold cyan]Mode: Hierarchical (1+3+1 Agent Team)[/bold cyan]")
    console.print("[dim]Architect → [Context Hunter | Math Specialist | Data Auditor] → Editor (EN/ZH)[/dim]\n")
    
    orchestrator = HierarchicalOrchestrator(
        provider=args.provider,
        model=model,
        api_key=args.api_key,
        max_workers=args.workers,
        verbose=args.verbose  # Pass verbose flag for LLM call logging
    )
    
    # Check for figure index
    figure_index_path = output_dir / "figure_index.json"
    
    analysis = orchestrator.analyze_paper(
        content=parsed_doc.markdown_content,
        title=parsed_doc.title,
        images=parsed_doc.images,
        figure_index_path=figure_index_path if figure_index_path.exists() else None,
        language=args.language
    )
    
    console.print(f"[green]✓[/green] Domain: {analysis.domain}")
    console.print(f"[green]✓[/green] Figures suggested: {len(analysis.figure_suggestions)}")
    
    # Save specialist reports (always, for later reference)
    specialists_dir = output_dir / "specialists"
    specialists_dir.mkdir(exist_ok=True)
    
    with open(specialists_dir / "01_context_hunter.md", "w", encoding="utf-8") as f:
        f.write(f"# Context Hunter Report\n\n**Domain**: {analysis.domain}\n\n")
        f.write(analysis.context_report)
    with open(specialists_dir / "02_math_specialist.md", "w", encoding="utf-8") as f:
        f.write(f"# Math Specialist Report\n\n")
        f.write(analysis.math_report)
    with open(specialists_dir / "03_data_auditor.md", "w", encoding="utf-8") as f:
        f.write(f"# Data Auditor Report\n\n")
        f.write(analysis.experiment_report)
    
    console.print("[dim]Specialist reports saved to specialists/ directory[/dim]")
    
    # Save verbose outputs (reading plan only)
    if args.verbose:
        # Save reading plan
        if analysis.reading_plan:
            with open(output_dir / "reading_plan.json", "w", encoding="utf-8") as f:
                f.write(analysis.reading_plan.raw_json)
        
        console.print("[dim]Verbose output saved (reading_plan.json)[/dim]")
    
    return analysis.final_report, analysis.final_report_chinese, analysis.figure_suggestions


def main():
    """Main entry point"""
    args = parse_args()
    
    # Display header
    mode_desc = "Hierarchical 1+3+1" if args.mode == "hierarchical" else "Simple Dual-Role"
    console.print(Panel.fit(
        f"[bold blue]📚 Paper Reader Agent[/bold blue]\n"
        f"[dim]Automated Academic Paper Analysis[/dim]\n"
        f"[cyan]Mode: {mode_desc}[/cyan]",
        border_style="blue"
    ))

    
    # Validate PDF path
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        console.print(f"[red]✗ Error:[/red] PDF file not found: {pdf_path}")
        sys.exit(1)
    
    if not pdf_path.suffix.lower() == ".pdf":
        console.print(f"[yellow]⚠ Warning:[/yellow] File may not be a PDF: {pdf_path}")
    
    # Set up output directory (include PDF name as subdirectory)
    output_dir = Path(args.output) / pdf_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    console.print(f"\n[blue]📄 Input:[/blue] {pdf_path}")
    console.print(f"[blue]📁 Output:[/blue] {output_dir}")
    console.print(f"[blue]🤖 Provider:[/blue] {args.provider}")
    
    # Determine model
    model = args.model
    if model is None:
        model = "deepseek-chat" if args.provider == "deepseek" else "gpt-4o"
    console.print(f"[blue]🧠 Model:[/blue] {model}")
    
    if args.mode == "hierarchical":
        console.print(f"[blue]👥 Workers:[/blue] {args.workers}")
    
    try:
        # Step 1: Parse PDF
        console.print("\n[bold]═══ Step 1: Parsing PDF ═══[/bold]")
        
        parser = PDFParser(
            use_gpu=not args.no_gpu,
            extract_images=not args.no_images
        )
        
        parsed_doc = parser.parse(
            pdf_path=str(pdf_path),
            output_dir=output_dir / "parsed",
            parser_backend=args.parser
        )
        
        console.print(f"[green]✓[/green] Title: {parsed_doc.title[:80]}...")
        console.print(f"[green]✓[/green] Content: {len(parsed_doc.markdown_content):,} chars")
        console.print(f"[green]✓[/green] Images: {len(parsed_doc.images)} extracted")
        
        # Copy images to output
        if parsed_doc.images:
            # For MinerU, images are already post-processed and placed in the correct 'parsed' directory
            # So we skip the generic copy logic which would flatten them into 'images' and lose the renaming
            if parsed_doc.metadata.get("parser") != "mineru":
                parser.copy_images_to_output(parsed_doc.images, images_dir)
                parsed_doc.image_map = {
                    img.image_id: str(images_dir / img.original_path.name)
                    for img in parsed_doc.images
                    if img.original_path
                }
            
            # Generate figure index for agent use
            parser.generate_figure_index(parsed_doc.images, output_dir)
        
        # Step 2: Analyze with LLM
        console.print("\n[bold]═══ Step 2: Analyzing Paper ═══[/bold]")
        
        final_report_chinese = None  # Only for hierarchical mode
        if args.mode == "hierarchical":
            final_report, final_report_chinese, figure_suggestions = run_hierarchical_mode(
                args, parsed_doc, model, images_dir, output_dir
            )
        else:
            final_report, figure_suggestions = run_simple_mode(
                args, parsed_doc, model, images_dir, output_dir
            )
        
        # Step 3: Generate Final Report
        console.print("\n[bold]═══ Step 3: Generating Report ═══[/bold]")
        
        generator = ReportGenerator()
        
        # Generate English report
        report_path = None
        if final_report:
            report_path = output_dir / "paper_analysis.md"
            final_report = generator.generate(
                analysis_report=final_report,
                image_map=parsed_doc.image_map,
                title=parsed_doc.title,
                output_path=report_path,
                images_output_dir=images_dir
            )
        
        # Generate Chinese report (if available)
        report_path_chinese = None
        if final_report_chinese:
            report_path_chinese = output_dir / "paper_analysis_zh.md"
            final_report_chinese = generator.generate(
                analysis_report=final_report_chinese,
                image_map=parsed_doc.image_map,
                title=parsed_doc.title,
                output_path=report_path_chinese,
                images_output_dir=images_dir
            )

        # Final summary
        console.print("\n" + "═" * 50)
        summary_text = f"[bold green]✓ Analysis Complete![/bold green]\n\n"
        
        if report_path:
            summary_text += f"[blue]Report (EN):[/blue] {report_path}\n"
        if report_path_chinese:
            summary_text += f"[blue]Report (ZH):[/blue] {report_path_chinese}\n"
            
        summary_text += (
            f"[blue]Images:[/blue] {images_dir}\n"
        )
        
        if final_report:
            summary_text += f"[blue]Size (EN):[/blue] {len(final_report):,} characters\n"
        if final_report_chinese:
            summary_text += f"[blue]Size (ZH):[/blue] {len(final_report_chinese):,} characters\n"
            
        summary_text += f"[blue]Mode:[/blue] {args.mode}"

        console.print(Panel.fit(
            summary_text,
            title="[bold]Summary[/bold]",
            border_style="green"
        ))
        
        # Show preview
        if final_report:
            console.print("\n[bold]Report Preview (EN):[/bold]")
            console.print("─" * 40)
            preview = final_report[:1500] + "..." if len(final_report) > 1500 else final_report
            console.print(Markdown(preview))
        elif final_report_chinese:
            console.print("\n[bold]Report Preview (ZH):[/bold]")
            console.print("─" * 40)
            preview = final_report_chinese[:1500] + "..." if len(final_report_chinese) > 1500 else final_report_chinese
            console.print(Markdown(preview))
        
    except Exception as e:
        console.print(f"\n[red]✗ Error:[/red] {e}")
        if args.verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
