#!/usr/bin/env python
"""
Export an existing Markdown file as a Notion child page (under a given parent page).

Features:
- Loads config from env: CLI args override, then `./.env` and `./md2notion/.env`
- Rewrites image links: turns `![...](images/xxx.png)` into a reachable external URL
- Supports dry-run: validates inputs and rewrites links without calling Notion API

Required config (either way):
- Environment variables: NOTION_SECRET, NOTION_PARENT_PAGE_ID
- Or put them in `md2notion/.env` (recommended)

Usage examples:
1) Dry-run (no Notion page is created)
   python export_to_notion.py --md "outputs\\RR_attn_1771172518\\paper_analysis_zh.md" --dry-run

2) Export using NOTION_* from md2notion/.env
   python export_to_notion.py --md "outputs\\RR_attn_1771172518\\paper_analysis_zh.md"

3) Export with hosted images (required if you want images rendered in Notion)
   python export_to_notion.py --md "outputs\\RR_attn_1771172518\\paper_analysis_zh.md" ^
     --image-base-url "https://your-host/RR_attn_1771172518"

4) Override parent page / set a cover image
   python export_to_notion.py --md "outputs\\RR_attn_1771172518\\paper_analysis_zh.md" ^
     --parent-page-id "<your_parent_page_id>" ^
     --cover-url "https://example.com/cover.jpg"

python export_to_notion.py --md "outputs\RR_attn_1771172518\paper_analysis_zh.md" --include-specialists-dir "outputs\RR_attn_1771172518\specialists" --imgbb-expiration 0
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from ImageGo.imagego import rewrite_markdown_images_via_imgbb

console = Console()


def _load_dotenv_files(repo_root: Path) -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return

    load_dotenv(repo_root / ".env", override=False)
    load_dotenv(repo_root / "md2notion" / ".env", override=False)


def _infer_title_from_markdown(markdown: str, fallback: str) -> str:
    if not markdown:
        return fallback

    first_line = markdown.lstrip().splitlines()[0].strip()
    if first_line.startswith("#"):
        return first_line.lstrip("#").strip() or fallback

    return fallback


def _strip_first_h1(markdown: str) -> str:
    if not markdown:
        return markdown
    lines = markdown.splitlines()
    if not lines:
        return markdown
    first = lines[0].strip()
    if first.startswith("#"):
        return "\n".join(lines[1:]).lstrip("\n")
    return markdown


def _rewrite_markdown_image_urls(markdown: str, image_base_url: Optional[str]) -> str:
    import re

    if not markdown:
        return markdown

    pattern = r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)'

    def repl(match: re.Match) -> str:
        alt = match.group(1) or ""
        url = match.group(2) or ""
        if url.startswith(("http://", "https://", "data:")):
            return match.group(0)

        if image_base_url:
            normalized = url.lstrip("./").lstrip("/")
            new_url = f"{image_base_url.rstrip('/')}/{normalized}"
            return f"![{alt}]({new_url})"

        label = alt.strip() or "image"
        return f"*Image: {label} ({url})*"

    return re.sub(pattern, repl, markdown)


def _import_md2notionpage(repo_root: Path):
    try:
        from md2notionpage import md2notionpage
        return md2notionpage
    except ModuleNotFoundError:
        sys.path.insert(0, str(repo_root / "md2notion"))
        from md2notionpage import md2notionpage
        return md2notionpage


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a Markdown file to Notion as a child page.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python export_to_notion.py --md "outputs\\\\RR_attn_1771172518\\\\paper_analysis_zh.md" --dry-run\n'
            '  python export_to_notion.py --md "outputs\\\\RR_attn_1771172518\\\\paper_analysis_zh.md"\n'
            '  python export_to_notion.py --md "outputs\\\\RR_attn_1771172518\\\\paper_analysis_zh.md" '
            '--image-base-url "https://your-host/RR_attn_1771172518"\n'
        ),
    )
    parser.add_argument("--md", required=True, help="Path to the Markdown file to export")
    parser.add_argument("--parent-page-id", default="", help="Notion parent page ID (overrides NOTION_PARENT_PAGE_ID)")
    parser.add_argument("--cover-url", default="", help="Optional cover image URL for the Notion page")
    parser.add_argument(
        "--image-base-url",
        default="",
        help="Base URL to rewrite relative image links (fallback when ImgBB is not enabled)",
    )
    parser.add_argument(
        "--include-specialists-dir",
        default="",
        help="Append all *.md under this directory as sections (e.g. outputs/**/specialists)",
    )
    parser.add_argument("--imgbb-key", default="", help="ImgBB API key (overrides IMGBB_API_KEY)")
    parser.add_argument("--imgbb-expiration", type=int, default=0, help="ImgBB expiration in seconds (0 means never)")
    parser.add_argument("--imgbb-cache", default="", help="Path to JSON cache file for uploaded images")
    parser.add_argument("--dry-run", action="store_true", help="Rewrite inputs but do not call Notion API")
    args = parser.parse_args()

    repo_root = Path(__file__).parent
    _load_dotenv_files(repo_root)

    md_path = Path(args.md)
    if not md_path.exists():
        console.print(f"[red]✗ Error:[/red] Markdown file not found: {md_path}")
        raise SystemExit(1)

    markdown = md_path.read_text(encoding="utf-8")
    title = _infer_title_from_markdown(markdown, md_path.stem)

    imgbb_key = args.imgbb_key or os.environ.get("IMGBB_API_KEY", "")
    imgbb_expiration = max(0, int(args.imgbb_expiration))
    cache_path = (
        (Path(args.imgbb_cache) if args.imgbb_cache else md_path.with_suffix(md_path.suffix + ".imgbb-cache.json"))
        if imgbb_key
        else None
    )

    def maybe_upload_and_rewrite_images(md: str, md_dir: Path) -> str:
        if not imgbb_key:
            return md
        return rewrite_markdown_images_via_imgbb(
            markdown=md,
            md_dir=md_dir,
            api_key=imgbb_key,
            expiration=imgbb_expiration,
            cache_path=cache_path,
        )

    markdown = maybe_upload_and_rewrite_images(markdown, md_path.parent)

    if args.include_specialists_dir:
        specialists_dir = Path(args.include_specialists_dir)
        if not specialists_dir.exists() or not specialists_dir.is_dir():
            console.print(f"[red]✗ Error:[/red] specialists dir not found: {specialists_dir}")
            raise SystemExit(1)

        specialist_files = sorted(p for p in specialists_dir.glob("*.md") if p.is_file())
        if specialist_files:
            parts: list[str] = []
            for p in specialist_files:
                content = p.read_text(encoding="utf-8")
                content = _strip_first_h1(content)
                content = maybe_upload_and_rewrite_images(content, p.parent)
                section_title = p.stem
                parts.append(f"### {section_title}\n\n{content.strip()}")

            markdown = markdown.rstrip() + "\n\n---\n\n## Specialists\n\n" + "\n\n---\n\n".join(parts) + "\n"

    parent_page_id = args.parent_page_id or os.environ.get("NOTION_PARENT_PAGE_ID", "")
    if not parent_page_id:
        console.print("[red]✗ Error:[/red] NOTION_PARENT_PAGE_ID is not set and --parent-page-id was not provided")
        raise SystemExit(1)

    if imgbb_key:
        notion_ready_md = markdown
    else:
        image_base_url = args.image_base_url or os.environ.get("NOTION_IMAGE_BASE_URL") or None
        notion_ready_md = _rewrite_markdown_image_urls(markdown, image_base_url=image_base_url)

    if args.dry_run:
        console.print("[yellow]⚠ Notion export dry-run:[/yellow] skipped API call")
        console.print("[green]✓[/green] Notion dry-run complete")
        return

    notion_secret = os.environ.get("NOTION_SECRET", "")
    if not notion_secret:
        console.print("[red]✗ Error:[/red] NOTION_SECRET is not set")
        raise SystemExit(1)

    md2notionpage = _import_md2notionpage(repo_root)
    notion_url = md2notionpage(
        notion_ready_md,
        title=title,
        parent_page_id=parent_page_id,
        cover_url=args.cover_url,
        parent_type="page",
    )
    console.print(f"[green]✓[/green] Notion page created: {notion_url}")


if __name__ == "__main__":
    main()
